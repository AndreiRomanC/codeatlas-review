import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import CodeAtlasConfig, RepositoryConfig, RevisionConfig
from .errors import CodeAtlasError


_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class SourceRevision:
    root: Path
    revision_name: str
    revision_kind: str
    resolved_commit: str


def _run_git(arguments: List[str], *, cwd: Optional[Path] = None, timeout: int = 300) -> str:
    command = ["git", *arguments]
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise CodeAtlasError(f"Git command failed: {detail}")
    return result.stdout.strip()


def _is_git_repository(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _mirror_path(config: CodeAtlasConfig, repository: RepositoryConfig) -> Path:
    if not _SAFE_NAME.fullmatch(repository.name):
        raise CodeAtlasError(f"Unsafe repository cache name: {repository.name}")
    return config.cache_dir / "mirrors" / f"{repository.name}.git"


def prepare_repository(
    config: CodeAtlasConfig, repository: RepositoryConfig, *, update: bool = True
) -> Dict[str, Any]:
    if repository.local_path is not None:
        path = repository.local_path
        if not path.is_dir():
            raise CodeAtlasError(f"Local repository path not found: {path}")
        dirty = None
        head = None
        if _is_git_repository(path):
            dirty = bool(_run_git(["-C", str(path), "status", "--porcelain", "--untracked-files=no"]))
            head = _run_git(["-C", str(path), "rev-parse", "HEAD"])
        return {
            "name": repository.name,
            "module": repository.module,
            "source_type": "local",
            "path": str(path),
            "dirty": dirty,
            "head": head,
            "mutated": False,
        }

    mirror = _mirror_path(config, repository)
    mirror.parent.mkdir(parents=True, exist_ok=True)
    cloned = False
    fetched = False
    if not mirror.exists():
        _run_git(["clone", "--mirror", str(repository.url), str(mirror)])
        cloned = True
    elif not mirror.is_dir():
        raise CodeAtlasError(f"Repository cache path is not a directory: {mirror}")
    elif update:
        _run_git(["--git-dir", str(mirror), "fetch", "origin"])
        fetched = True
    return {
        "name": repository.name,
        "module": repository.module,
        "source_type": "git",
        "path": str(mirror),
        "cloned": cloned,
        "fetched": fetched,
        "mutated": cloned or fetched,
    }


def prepare_module(config: CodeAtlasConfig, module: str, *, update: bool = True) -> List[Dict[str, Any]]:
    return [prepare_repository(config, repo, update=update) for repo in config.repositories_for_module(module)]


def _git_location(config: CodeAtlasConfig, repository: RepositoryConfig) -> Tuple[Path, bool]:
    if repository.local_path is not None:
        if not _is_git_repository(repository.local_path):
            raise CodeAtlasError(
                f"Revision {repository.name} requires Git, but local_path is not a Git repository"
            )
        return repository.local_path, False
    mirror = _mirror_path(config, repository)
    if not mirror.is_dir():
        prepare_repository(config, repository, update=True)
    return mirror, True


def _git_at(location: Path, bare: bool, arguments: List[str]) -> str:
    prefix = ["--git-dir", str(location)] if bare else ["-C", str(location)]
    return _run_git([*prefix, *arguments])


def _safe_extract_archive(process: subprocess.Popen, destination: Path) -> None:
    assert process.stdout is not None
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                relative = Path(member.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise CodeAtlasError(f"Unsafe path in Git archive: {member.name}")
                target = destination / relative
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise CodeAtlasError(f"Unable to read Git archive member: {member.name}")
                    with target.open("wb") as output:
                        shutil.copyfileobj(source, output)
                # Symlinks and special files are intentionally not materialized.
    finally:
        process.stdout.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait(timeout=300)
    if return_code != 0:
        raise CodeAtlasError(f"git archive failed: {stderr.strip() or 'unknown error'}")


def _snapshot(
    config: CodeAtlasConfig,
    repository: RepositoryConfig,
    revision: RevisionConfig,
) -> SourceRevision:
    location, bare = _git_location(config, repository)
    commit = _git_at(
        location,
        bare,
        ["rev-parse", "--verify", "--end-of-options", f"{revision.ref}^{{commit}}"],
    )
    destination = config.cache_dir / "snapshots" / repository.name / commit
    marker = destination / ".codeatlas-snapshot"
    if marker.is_file():
        return SourceRevision(destination, revision.name, revision.kind, commit)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f"{commit[:12]}-", dir=str(destination.parent)))
    prefix = ["--git-dir", str(location)] if bare else ["-C", str(location)]
    process = subprocess.Popen(
        ["git", *prefix, "archive", "--format=tar", commit],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _safe_extract_archive(process, temporary)
        (temporary / ".codeatlas-snapshot").write_text(commit + "\n", encoding="utf-8")
        try:
            os.replace(str(temporary), str(destination))
        except FileExistsError:
            shutil.rmtree(temporary)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if process.poll() is None:
            process.kill()
        raise
    return SourceRevision(destination, revision.name, revision.kind, commit)


def source_revision(
    config: CodeAtlasConfig,
    repository: RepositoryConfig,
    revision: RevisionConfig,
) -> SourceRevision:
    if repository.local_path is not None and revision.ref == "WORKTREE":
        if not repository.local_path.is_dir():
            raise CodeAtlasError(f"Local repository path not found: {repository.local_path}")
        return SourceRevision(repository.local_path, revision.name, revision.kind, "WORKTREE")
    return _snapshot(config, repository, revision)
