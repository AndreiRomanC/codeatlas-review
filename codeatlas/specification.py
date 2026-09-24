from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import re
from typing import Any, Dict, List, Mapping, Optional, Protocol, Tuple

from .errors import ConfigurationError
from .hashing import decode_text, normalize_text, sha256_bytes


_SAFE_MODULE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class SpecificationRequest:
    module: str
    feature: Optional[str] = None
    revision: Optional[str] = None
    document: Optional[str] = None


@dataclass(frozen=True)
class SpecificationResult:
    available: bool
    provider: str
    message: str
    content: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpecificationProvider(Protocol):
    def get(self, request: SpecificationRequest) -> SpecificationResult:
        ...


class UnconfiguredSpecificationProvider:
    def get(self, request: SpecificationRequest) -> SpecificationResult:
        return SpecificationResult(
            available=False,
            provider="unconfigured",
            message=(
                "Specification retrieval is not configured. Provide the approved provider, "
                "access mechanism, document format, and revision rules."
            ),
        )


class FolderTxtSpecificationProvider:
    def __init__(
        self,
        roots: Tuple[Path, ...],
        *,
        directory_pattern: str,
        recursive: bool,
        max_file_bytes: int,
    ) -> None:
        self.roots = roots
        self.directory_pattern = directory_pattern
        self.recursive = recursive
        self.max_file_bytes = max_file_bytes

    def _module_directories(self, module: str) -> List[Path]:
        pattern = self.directory_pattern.format(module=module)
        directories: List[Path] = []
        for root in self.roots:
            if not root.is_dir():
                continue
            resolved_root = root.resolve()
            for candidate in root.glob(pattern):
                if not candidate.is_dir() or candidate.is_symlink():
                    continue
                resolved = candidate.resolve()
                try:
                    resolved.relative_to(resolved_root)
                except ValueError:
                    continue
                directories.append(resolved)
        return sorted(set(directories))

    def _candidates(self, request: SpecificationRequest) -> List[Path]:
        candidates: List[Path] = []
        for directory in self._module_directories(request.module):
            iterator = directory.rglob("*") if self.recursive else directory.iterdir()
            candidates.extend(
                path.resolve()
                for path in iterator
                if path.is_file() and not path.is_symlink() and path.suffix.casefold() == ".txt"
            )
        candidates = sorted(set(candidates))
        if request.document:
            selector = request.document.casefold()
            candidates = [
                path
                for path in candidates
                if path.name.casefold() == selector or path.stem.casefold() == selector
            ]
        return candidates

    def get(self, request: SpecificationRequest) -> SpecificationResult:
        if not _SAFE_MODULE.fullmatch(request.module):
            raise ConfigurationError("Specification module must contain only letters, digits, '.', '_' or '-'")
        if request.document:
            document = PurePosixPath(request.document.replace("\\", "/"))
            if document.is_absolute() or ".." in document.parts or len(document.parts) != 1:
                raise ConfigurationError("Specification document selector must be a filename or stem")

        candidates = self._candidates(request)
        if not candidates:
            detail = f" matching document '{request.document}'" if request.document else ""
            return SpecificationResult(
                available=False,
                provider="folder_txt",
                message=f"No .txt specification{detail} found in the configured d folder for module {request.module}",
                provenance={"module": request.module, "searched_roots": [str(root) for root in self.roots]},
            )

        documents: List[Dict[str, Any]] = []
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for path in candidates:
            size = path.stat().st_size
            item: Dict[str, Any] = {"path": str(path), "size_bytes": size}
            if size > self.max_file_bytes:
                item["error"] = f"exceeds max_file_bytes={self.max_file_bytes}"
                documents.append(item)
                continue
            data = path.read_bytes()
            digest = sha256_bytes(data)
            text, encoding = decode_text(data)
            item.update({"sha256": digest, "encoding": encoding})
            documents.append(item)
            groups.setdefault(digest, []).append({**item, "content": normalize_text(text)})

        if not groups:
            return SpecificationResult(
                available=False,
                provider="folder_txt",
                message="All matching specification files exceed the configured size limit",
                provenance={"module": request.module, "documents": documents},
            )
        if len(groups) > 1:
            return SpecificationResult(
                available=False,
                provider="folder_txt",
                message=(
                    "Multiple different .txt specifications were found. Select one explicitly "
                    "with the document filename; CodeAtlas will not guess which is authoritative."
                ),
                provenance={
                    "module": request.module,
                    "requested_feature": request.feature,
                    "requested_revision": request.revision,
                    "documents": documents,
                },
            )

        digest, matches = next(iter(groups.items()))
        selected = matches[0]
        return SpecificationResult(
            available=True,
            provider="folder_txt",
            message=(
                "Loaded one specification document"
                if len(matches) == 1
                else f"Loaded one specification content shared by {len(matches)} identical files"
            ),
            content=selected["content"],
            provenance={
                "module": request.module,
                "requested_feature": request.feature,
                "requested_revision": request.revision,
                "revision_verified": False,
                "sha256": digest,
                "sources": [
                    {
                        "path": item["path"],
                        "size_bytes": item["size_bytes"],
                        "encoding": item["encoding"],
                    }
                    for item in matches
                ],
            },
        )


class RepositoryFolderTxtSpecificationProvider:
    def __init__(
        self,
        codeatlas_config: Any,
        repository_name: str,
        revision_name: Optional[str],
        *,
        directory_pattern: str,
        recursive: bool,
        max_file_bytes: int,
    ) -> None:
        self.config = codeatlas_config
        self.repository_name = repository_name
        self.revision_name = revision_name
        self.directory_pattern = directory_pattern
        self.recursive = recursive
        self.max_file_bytes = max_file_bytes

    def get(self, request: SpecificationRequest) -> SpecificationResult:
        from .repository import source_revision

        repositories = [item for item in self.config.repositories if item.name == self.repository_name]
        if len(repositories) != 1:
            raise ConfigurationError(
                f"Specification repository not found or ambiguous: {self.repository_name}"
            )
        repository = repositories[0]
        requested_revision = request.revision or self.revision_name
        if requested_revision:
            revisions = [
                item
                for item in repository.revisions
                if item.name == requested_revision or item.ref == requested_revision
            ]
        else:
            revisions = list(repository.revisions)
        if len(revisions) != 1:
            raise ConfigurationError(
                "Specification revision must identify exactly one configured repository revision"
            )
        source = source_revision(self.config, repository, revisions[0])
        delegate = FolderTxtSpecificationProvider(
            (source.root,),
            directory_pattern=self.directory_pattern,
            recursive=self.recursive,
            max_file_bytes=self.max_file_bytes,
        )
        result = delegate.get(request)
        provenance = dict(result.provenance or {})
        provenance.update(
            {
                "repository": repository.name,
                "revision": source.revision_name,
                "resolved_commit": source.resolved_commit,
                "revision_verified": source.resolved_commit != "WORKTREE",
            }
        )
        return SpecificationResult(
            available=result.available,
            provider=result.provider,
            message=result.message,
            content=result.content,
            provenance=provenance,
        )


def _folder_options(settings: Mapping[str, Any]) -> Tuple[str, bool, int]:
    pattern = settings.get("directory_pattern", "**/{module}/d")
    if not isinstance(pattern, str) or "{module}" not in pattern:
        raise ConfigurationError("specification.directory_pattern must contain {module}")
    normalized_pattern = pattern.replace("\\", "/")
    try:
        rendered_pattern = normalized_pattern.format(module="module")
    except (KeyError, ValueError) as exc:
        raise ConfigurationError(
            "specification.directory_pattern may use only the {module} placeholder"
        ) from exc
    pure_pattern = PurePosixPath(rendered_pattern)
    if pure_pattern.is_absolute() or ".." in pure_pattern.parts:
        raise ConfigurationError("specification.directory_pattern must stay within each configured root")
    recursive = settings.get("recursive", False)
    if not isinstance(recursive, bool):
        raise ConfigurationError("specification.recursive must be true or false")
    max_file_bytes = settings.get("max_file_bytes", 250_000)
    if not isinstance(max_file_bytes, int) or not 1 <= max_file_bytes <= 1_000_000:
        raise ConfigurationError("specification.max_file_bytes must be between 1 and 1000000")
    return normalized_pattern, recursive, max_file_bytes


def _folder_txt_provider(
    settings: Mapping[str, Any], base_dir: Optional[Path], codeatlas_config: Optional[Any]
) -> SpecificationProvider:
    pattern, recursive, max_file_bytes = _folder_options(settings)
    repository_name = settings.get("repository")
    if repository_name is not None:
        if not isinstance(repository_name, str) or not repository_name:
            raise ConfigurationError("specification.repository must be a non-empty string")
        if codeatlas_config is None:
            raise ConfigurationError("Repository-backed specification requires CodeAtlas configuration")
        revision_name = settings.get("revision")
        if revision_name is not None and (not isinstance(revision_name, str) or not revision_name):
            raise ConfigurationError("specification.revision must be a non-empty string")
        return RepositoryFolderTxtSpecificationProvider(
            codeatlas_config,
            repository_name,
            revision_name,
            directory_pattern=pattern,
            recursive=recursive,
            max_file_bytes=max_file_bytes,
        )
    roots_raw = settings.get("roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise ConfigurationError(
            "folder_txt specification provider requires either repository or a non-empty roots list"
        )
    root_base = (base_dir or Path.cwd()).resolve()
    roots: List[Path] = []
    for value in roots_raw:
        if not isinstance(value, str) or not value:
            raise ConfigurationError("Specification roots must be non-empty path strings")
        path = Path(value).expanduser()
        roots.append((root_base / path).resolve() if not path.is_absolute() else path.resolve())
    return FolderTxtSpecificationProvider(
        tuple(roots),
        directory_pattern=pattern,
        recursive=recursive,
        max_file_bytes=max_file_bytes,
    )


def provider_from_config(
    settings: Mapping[str, Any], *, base_dir: Optional[Path] = None, codeatlas_config: Optional[Any] = None
) -> SpecificationProvider:
    name = settings.get("provider", "unconfigured")
    if name in {None, "", "unconfigured"}:
        return UnconfiguredSpecificationProvider()
    if name == "folder_txt":
        return _folder_txt_provider(settings, base_dir, codeatlas_config)
    raise ConfigurationError(
        f"Specification provider '{name}' is not implemented; add an approved adapter instead of guessing"
    )
