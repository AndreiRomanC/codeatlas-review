import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.search import list_implementations  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List unique exact implementations and all indexed occurrences"
    )
    parser.add_argument("--db", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--kind", default="function")
    parser.add_argument("--module")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    return run_cli(
        lambda: list_implementations(
            Path(args.db).expanduser().resolve(),
            args.name,
            kind=args.kind,
            module=args.module,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
