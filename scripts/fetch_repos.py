import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.repository import prepare_module  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare configured reference repositories safely")
    parser.add_argument("--module", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--no-update", action="store_true", help="Do not fetch existing Git mirrors")
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        return {
            "module": args.module,
            "repositories": prepare_module(config, args.module, update=not args.no_update),
        }

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
