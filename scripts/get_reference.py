import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.search import get_reference  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve one exact CodeAtlas reference")
    parser.add_argument("--db", required=True)
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--max-bytes", type=int, default=200_000)
    args = parser.parse_args()

    def action():
        return get_reference(
            Path(args.db).expanduser().resolve(), args.id, max_bytes=args.max_bytes
        )

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
