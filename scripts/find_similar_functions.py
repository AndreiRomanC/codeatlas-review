import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.c_parser import extract_functions  # noqa: E402
from codeatlas.errors import CodeAtlasError  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.search import find_similar_functions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Find functions with similar token fingerprints")
    parser.add_argument("--db", required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--id", type=int, help="Indexed function entity ID")
    target.add_argument("--source", help="C source file containing the target function")
    parser.add_argument("--function", help="Function name within --source")
    parser.add_argument("--candidate-name", help="Restrict candidates to this exact name")
    parser.add_argument("--module", help="Restrict candidates to this module")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()

    def resolve_target():
        if args.source is None:
            if args.function:
                raise CodeAtlasError("--function requires --source")
            return None
        if not args.function:
            raise CodeAtlasError("--source requires --function")
        source_path = Path(args.source).expanduser().resolve()
        if not source_path.is_file():
            raise CodeAtlasError(f"Source file not found: {source_path}")
        matches = [item for item in extract_functions(source_path.read_bytes()) if item.name == args.function]
        if len(matches) != 1:
            raise CodeAtlasError(
                f"Expected one function named {args.function!r} in {source_path}; found {len(matches)}"
            )
        return matches[0]

    return run_cli(
        lambda: find_similar_functions(
            Path(args.db).expanduser().resolve(),
            args.id,
            target_function=resolve_target(),
            candidate_name=args.candidate_name,
            module=args.module,
            limit=args.limit,
            min_score=args.min_score,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
