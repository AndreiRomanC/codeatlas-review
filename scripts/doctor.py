import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.runtime import resolve_python  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve and check the local CodeAtlas runtime")
    parser.add_argument("--json", action="store_true", help="Emit compact machine-readable JSON")
    parser.add_argument(
        "--resolve", action="store_true", help="Print only the recommended Python executable"
    )
    args = parser.parse_args()

    result = resolve_python(Path(__file__).resolve().parents[1])
    result["git"] = {"available": shutil.which("git") is not None}
    result["ok"] = bool(result["selected"] and result["dependencies_ready"] and result["git"]["available"])
    if args.resolve:
        if result["selected"]:
            print(result["selected"]["executable"])
        return 0 if result["ok"] else 2
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
