import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.indexer import index_module  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or incrementally refresh a CodeAtlas index")
    parser.add_argument("--module", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--force", action="store_true", help="Reindex unchanged files")
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        return {
            "database": str(config.database),
            "module": args.module,
            "forced": args.force,
            "revisions": index_module(config, args.module, force=args.force),
        }

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
