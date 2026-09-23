import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.search import find_references  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Return a compact CodeAtlas reference catalog")
    parser.add_argument("--db", required=True)
    parser.add_argument("--kind")
    parser.add_argument("--name")
    parser.add_argument("--name-mode", choices=("exact", "contains"), default="exact")
    parser.add_argument("--hash", dest="hash_prefix")
    parser.add_argument("--module")
    parser.add_argument("--repository")
    parser.add_argument("--revision")
    parser.add_argument("--identifier")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    def action():
        return find_references(
            Path(args.db).expanduser().resolve(),
            kind=args.kind,
            name=args.name,
            name_mode=args.name_mode,
            hash_prefix=args.hash_prefix,
            module=args.module,
            repository=args.repository,
            revision=args.revision,
            identifier=args.identifier,
            limit=args.limit,
        )

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
