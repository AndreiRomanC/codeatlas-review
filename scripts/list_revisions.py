import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.repository import list_available_revisions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="List actual Git branches and tags for a module")
    parser.add_argument("--module", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--refresh", action="store_true", help="Fetch remote refs first")
    args = parser.parse_args()
    return run_cli(
        lambda: list_available_revisions(
            load_config(args.config), args.module, update=args.refresh
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
