from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit

import yaml

from .errors import ConfigurationError


DEFAULT_INCLUDE = ("**/*.c", "**/*.h", "**/*.grl", "**/*.grl2")
DEFAULT_EXCLUDE = ("**/.git/**", "**/.codeatlas/**", "**/build/**", "**/target/**")
DEFAULT_ARTIFACT_KINDS = {"grr": (".grl", ".grl2")}


@dataclass(frozen=True)
class RevisionConfig:
    name: str
    ref: str
    kind: str


@dataclass(frozen=True)
class RepositoryConfig:
    name: str
    module: str
    local_path: Optional[Path]
    url: Optional[str]
    revisions: Tuple[RevisionConfig, ...]

    @property
    def source_type(self) -> str:
        return "local" if self.local_path is not None else "git"

    @property
    def origin(self) -> str:
        return str(self.local_path) if self.local_path is not None else str(self.url)


@dataclass(frozen=True)
class IndexConfig:
    include: Tuple[str, ...]
    exclude: Tuple[str, ...]
    artifact_kinds: Mapping[str, Tuple[str, ...]]
    max_file_bytes: int

    def artifact_kind_for(self, suffix: str) -> Optional[str]:
        lowered = suffix.lower()
        for kind, suffixes in self.artifact_kinds.items():
            if lowered in suffixes:
                return kind
        return None


@dataclass(frozen=True)
class CodeAtlasConfig:
    path: Path
    database: Path
    cache_dir: Path
    repositories: Tuple[RepositoryConfig, ...]
    index: IndexConfig
    specification: Mapping[str, Any]

    def repositories_for_module(self, module: str) -> Tuple[RepositoryConfig, ...]:
        matches = tuple(repo for repo in self.repositories if repo.module.casefold() == module.casefold())
        if not matches:
            raise ConfigurationError(f"No repositories configured for module: {module}")
        return matches


def _resolve_path(base: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field} must be a non-empty path string")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _strings(value: Any, field: str, default: Iterable[str]) -> Tuple[str, ...]:
    if value is None:
        return tuple(default)
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) and item for item in value):
        raise ConfigurationError(f"{field} must be a list of non-empty strings")
    return tuple(value)


def _revision(item: Any) -> RevisionConfig:
    if isinstance(item, str):
        return RevisionConfig(name=item, ref=item, kind="git")
    if not isinstance(item, dict):
        raise ConfigurationError("Each revision must be a string or mapping")
    name = item.get("name") or item.get("ref")
    ref = item.get("ref") or name
    kind = item.get("kind") or ("local" if ref == "WORKTREE" else "git")
    if not all(isinstance(value, str) and value for value in (name, ref, kind)):
        raise ConfigurationError("Revision name, ref, and kind must be non-empty strings")
    return RevisionConfig(name=name, ref=ref, kind=kind)


def _reject_embedded_http_credentials(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and (parsed.username or parsed.password):
        raise ConfigurationError("Do not embed HTTP credentials in repository URLs")


def load_config(path: str) -> CodeAtlasConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML configuration: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigurationError("Configuration root must be a mapping")
    if loaded.get("version", 1) != 1:
        raise ConfigurationError("Unsupported configuration version")

    base = config_path.parent
    database = _resolve_path(base, loaded.get("database", ".codeatlas/codeatlas.db"), "database")
    cache_dir = _resolve_path(base, loaded.get("cache_dir", ".codeatlas/repos"), "cache_dir")

    index_raw = loaded.get("index") or {}
    if not isinstance(index_raw, dict):
        raise ConfigurationError("index must be a mapping")
    artifact_raw = index_raw.get("artifact_kinds", DEFAULT_ARTIFACT_KINDS)
    if not isinstance(artifact_raw, dict):
        raise ConfigurationError("index.artifact_kinds must be a mapping")
    artifact_kinds: Dict[str, Tuple[str, ...]] = {}
    for kind, suffixes in artifact_raw.items():
        if not isinstance(kind, str) or not kind:
            raise ConfigurationError("Artifact kind names must be non-empty strings")
        parsed = _strings(suffixes, f"index.artifact_kinds.{kind}", ())
        artifact_kinds[kind] = tuple(s.lower() if s.startswith(".") else f".{s.lower()}" for s in parsed)
    max_file_bytes = index_raw.get("max_file_bytes", 5_000_000)
    if not isinstance(max_file_bytes, int) or not 1 <= max_file_bytes <= 100_000_000:
        raise ConfigurationError("index.max_file_bytes must be between 1 and 100000000")
    index = IndexConfig(
        include=_strings(index_raw.get("include"), "index.include", DEFAULT_INCLUDE),
        exclude=_strings(index_raw.get("exclude"), "index.exclude", DEFAULT_EXCLUDE),
        artifact_kinds=artifact_kinds,
        max_file_bytes=max_file_bytes,
    )

    repositories_raw = loaded.get("repositories")
    if not isinstance(repositories_raw, dict) or not repositories_raw:
        raise ConfigurationError("repositories must be a non-empty mapping")
    repositories: List[RepositoryConfig] = []
    for name, raw in repositories_raw.items():
        if not isinstance(name, str) or not name or not isinstance(raw, dict):
            raise ConfigurationError("Repository entries must be named mappings")
        module = raw.get("module")
        if not isinstance(module, str) or not module:
            raise ConfigurationError(f"Repository {name} requires module")
        has_local = "local_path" in raw
        has_url = "url" in raw
        if has_local == has_url:
            raise ConfigurationError(f"Repository {name} must define exactly one of local_path or url")
        local_path = _resolve_path(base, raw["local_path"], f"repositories.{name}.local_path") if has_local else None
        url = raw.get("url") if has_url else None
        if url is not None:
            if not isinstance(url, str) or not url.strip():
                raise ConfigurationError(f"Repository {name} URL must be a non-empty string")
            if url.startswith("-"):
                raise ConfigurationError(f"Repository {name} URL must not begin with '-'")
            _reject_embedded_http_credentials(url)
        revisions_raw = raw.get("revisions") or ([{"name": "working-tree", "ref": "WORKTREE", "kind": "local"}] if has_local else [])
        if not isinstance(revisions_raw, list) or not revisions_raw:
            raise ConfigurationError(f"Repository {name} requires at least one revision")
        revisions = tuple(_revision(item) for item in revisions_raw)
        repositories.append(RepositoryConfig(name, module, local_path, url, revisions))

    specification = loaded.get("specification") or {"provider": "unconfigured"}
    if not isinstance(specification, dict):
        raise ConfigurationError("specification must be a mapping")
    return CodeAtlasConfig(config_path, database, cache_dir, tuple(repositories), index, specification)
