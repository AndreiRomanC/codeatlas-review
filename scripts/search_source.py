import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.source_search import search_source  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search configured source revisions with bounded deterministic context"
    )
    parser.add_argument("--module", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--regex", action="store_true")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--refresh", action="store_true", help="Fetch remote refs first")
    args = parser.parse_args()
    return run_cli(
        lambda: search_source(
            load_config(args.config),
            args.module,
            args.query,
            regex=args.regex,
            ignore_case=args.ignore_case,
            context=args.context,
            limit=args.limit,
            refresh=args.refresh,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
