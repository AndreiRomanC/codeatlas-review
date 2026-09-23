import fnmatch
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Tuple

from .errors import CodeAtlasError


def portable_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    has_windows_drive = len(normalized) >= 3 and normalized[0].isalpha() and normalized[1:3] == ":/"
    if path.is_absolute() or has_windows_drive or ".." in path.parts:
        raise CodeAtlasError(f"Unsafe relative path: {value}")
    return path.as_posix()


def _matches(path: str, patterns: Iterable[str]) -> bool:
    pure = PurePosixPath(path)
    for pattern in patterns:
        candidates = (pattern, pattern[3:]) if pattern.startswith("**/") else (pattern,)
        if any(pure.match(candidate) or fnmatch.fnmatchcase(path, candidate) for candidate in candidates):
            return True
    return False


def iter_index_files(root: Path, include: Tuple[str, ...], exclude: Tuple[str, ...]) -> Iterator[Tuple[str, Path]]:
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise CodeAtlasError(f"Repository source directory not found: {resolved_root}")
    for candidate in sorted(resolved_root.rglob("*")):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        relative = portable_relative_path(candidate.relative_to(resolved_root).as_posix())
        if _matches(relative, exclude):
            continue
        if _matches(relative, include):
            yield relative, candidate
