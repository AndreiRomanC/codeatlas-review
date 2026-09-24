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
    parser.add_argument("--summary", action="store_true", help="Return totals instead of per-revision details")
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        result = {
            "database": str(config.database),
            "module": args.module,
            "forced": args.force,
            "revisions": index_module(config, args.module, force=args.force),
        }
        if args.summary:
            revisions = result.pop("revisions")
            stats = [item["stats"] for item in revisions]
            result["summary"] = {
                "revisions": len(revisions),
                "discovered": sum(item["discovered"] for item in stats),
                "indexed": sum(item["indexed"] for item in stats),
                "unchanged": sum(item["unchanged"] for item in stats),
                "functions": sum(item["functions"] for item in stats),
                "artifacts": sum(item["artifacts"] for item in stats),
                "errors": sum(item["errors"] for item in stats),
            }
        return result

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
