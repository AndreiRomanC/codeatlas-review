import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.search import extract_grl_definitions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a GRL definition across indexed revisions")
    parser.add_argument("--db", required=True)
    parser.add_argument("--identifier", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--all-revisions", action="store_true", help="Include missing/no-GRL revisions")
    args = parser.parse_args()
    result = extract_grl_definitions(
        Path(args.db).expanduser().resolve(),
        args.identifier,
        limit=args.limit,
        revision=args.revision,
        all_revisions=args.all_revisions,
    )
    if args.format == "text":
        print(f"identifier: {result['identifier']}")
        print(f"definitions: {result['count']}")
        for item in result["results"]:
            print(
                f"\n--- {item['revision']} | {item['path']}:{item['start_line']}-{item['end_line']} ---"
            )
            print(item["definition"])
        if args.all_revisions:
            print("\n--- revision coverage ---")
            for item in result["revisions"]:
                print(f"{item['revision']} | {item['status']} | {'GRL' if item['has_grl'] else 'no-GRL'}")
        return 0
    from codeatlas.jsonio import emit  # noqa: E402

    emit({"ok": True, **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())