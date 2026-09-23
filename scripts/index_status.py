import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.indexer import index_status  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Report whether a CodeAtlas index is stale")
    parser.add_argument("--module", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        return {"module": args.module, "database": str(config.database), **index_status(config, args.module)}

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
