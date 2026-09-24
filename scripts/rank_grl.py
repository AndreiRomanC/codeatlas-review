import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.search import rank_grl_identifiers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank GRL identifiers by revision coverage")
    parser.add_argument("--db", required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    return run_cli(
        lambda: rank_grl_identifiers(
            Path(args.db).expanduser().resolve(), limit=args.limit
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())