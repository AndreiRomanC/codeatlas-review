import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MINIMUM_PYTHON = (3, 9)
REQUIRED_MODULES = ("yaml", "tree_sitter", "tree_sitter_c")


def _unique_candidates(items: Iterable[Tuple[int, str, Path]]) -> List[Tuple[int, str, Path]]:
    seen = set()
    result = []
    for priority, source, path in items:
        absolute = Path(os.path.abspath(str(path)))
        normalized = os.path.normcase(str(absolute))
        if normalized not in seen and path.is_file():
            seen.add(normalized)
            # Preserve venv launcher paths. Resolving the symlink would bypass the venv.
            result.append((priority, source, absolute))
    return result


def interpreter_candidates(project_root: Path) -> List[Tuple[int, str, Path]]:
    items: List[Tuple[int, str, Path]] = []
    explicit = os.environ.get("CODEATLAS_PYTHON")
    if explicit:
        items.append((0, "CODEATLAS_PYTHON", Path(explicit).expanduser()))

    aura = os.environ.get("AURA_FRAMEWORK_PATH")
    if aura:
        aura_root = Path(aura).expanduser()
        items.extend(
            (
                (1, "AURA venv", aura_root / ".venv" / "Scripts" / "python.exe"),
                (1, "AURA venv", aura_root / ".venv" / "bin" / "python"),
            )
        )

    items.extend(
        (
            (2, "project venv", project_root / ".venv" / "Scripts" / "python.exe"),
            (2, "project venv", project_root / ".venv" / "bin" / "python"),
        )
    )

    if os.name == "nt":
        legacy = Path("C:/LegacyApp")
        if legacy.is_dir():
            for path in sorted(legacy.glob("Python*/python.exe")):
                items.append((3, "C:/LegacyApp", path))
        launcher = shutil.which("py")
        if launcher:
            result = subprocess.run(
                [launcher, "-0p"], check=False, capture_output=True, text=True, timeout=15
            )
            for line in result.stdout.splitlines():
                value = line.strip().split()[-1] if line.strip() else ""
                if value:
                    items.append((3, "py launcher", Path(value)))

    items.append((4, "current interpreter", Path(sys.executable)))
    for command in (
        "python3.14",
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3.9",
        "python3",
        "python",
    ):
        executable = shutil.which(command)
        if executable:
            items.append((5, "PATH", Path(executable)))
    return _unique_candidates(items)


def inspect_interpreter(path: Path, source: str, priority: int) -> Dict[str, Any]:
    probe = (
        "import importlib.util,json,sys;"
        f"mods={REQUIRED_MODULES!r};"
        "print(json.dumps({'version':list(sys.version_info[:3]),"
        "'modules':{m:importlib.util.find_spec(m) is not None for m in mods}}))"
    )
    try:
        result = subprocess.run(
            [str(path), "-c", probe], check=False, capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "probe failed")
        payload = json.loads(result.stdout)
        version = tuple(int(part) for part in payload["version"])
        modules = payload["modules"]
        return {
            "executable": str(path),
            "source": source,
            "priority": priority,
            "version": ".".join(str(part) for part in version),
            "supported": version[:2] >= MINIMUM_PYTHON,
            "modules": modules,
            "dependencies_ready": all(modules.values()),
        }
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "executable": str(path),
            "source": source,
            "priority": priority,
            "supported": False,
            "dependencies_ready": False,
            "error": str(exc),
        }


def resolve_python(project_root: Path) -> Dict[str, Any]:
    inspected = [
        inspect_interpreter(path, source, priority)
        for priority, source, path in interpreter_candidates(project_root.resolve())
    ]
    compatible = [item for item in inspected if item.get("supported")]
    ready = [item for item in compatible if item.get("dependencies_ready")]
    pool = ready or compatible
    selected: Optional[Dict[str, Any]] = None
    if pool:
        selected = sorted(
            pool,
            key=lambda item: (
                int(item["priority"]),
                tuple(-int(part) for part in str(item["version"]).split(".")),
            ),
        )[0]
    return {
        "minimum_python": ".".join(str(part) for part in MINIMUM_PYTHON),
        "selected": selected,
        "dependencies_ready": bool(selected and selected["dependencies_ready"]),
        "candidates": inspected,
    }
