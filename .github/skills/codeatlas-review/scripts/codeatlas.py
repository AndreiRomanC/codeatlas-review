import os
import subprocess
import sys
from pathlib import Path


COMMANDS = {
    "doctor": "doctor.py",
    "fetch": "fetch_repos.py",
    "find": "find_references.py",
    "get": "get_reference.py",
    "grl": "extract_grl.py",
    "implementations": "list_implementations.py",
    "index": "build_index.py",
    "list-revisions": "list_revisions.py",
    "rank-grl": "rank_grl.py",
    "similar": "find_similar_functions.py",
    "source-search": "search_source.py",
    "spec": "get_specification.py",
    "status": "index_status.py",
}


def locate_home() -> Path:
    configured = os.environ.get("CODEATLAS_HOME")
    candidates = [Path(configured).expanduser()] if configured else []
    candidates.extend(Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (candidate / "codeatlas").is_dir():
            return candidate.resolve()
    raise SystemExit(
        "CodeAtlas core not found. Set CODEATLAS_HOME to the standalone codeatlas-review repository."
    )


def preferred_python(home: Path) -> Path:
    configured = os.environ.get("CODEATLAS_PYTHON")
    if configured:
        return Path(configured).expanduser()
    for relative in (Path(".venv/Scripts/python.exe"), Path(".venv/bin/python")):
        candidate = home / relative
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        available = ", ".join(sorted(COMMANDS))
        print(f"usage: codeatlas.py COMMAND [arguments]\ncommands: {available}", file=sys.stderr)
        return 2
    home = locate_home()
    command = home / "scripts" / COMMANDS[sys.argv[1]]
    result = subprocess.run(
        [str(preferred_python(home)), str(command), *sys.argv[2:]],
        cwd=str(home),
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
