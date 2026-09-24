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
    parser.add_argument("--summary", action="store_true", help="Return totals instead of per-revision details")
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        result = {"module": args.module, "database": str(config.database), **index_status(config, args.module)}
        if args.summary:
            repositories = result.pop("repositories")
            result["summary"] = {
                "revisions": len(repositories),
                "stale_revisions": sum(item["stale"] for item in repositories),
                "indexed": bool(result["initialized"] and repositories)
                and all(item["indexed"] for item in repositories),
            }
        return result

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
