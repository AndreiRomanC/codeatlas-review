import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.database import initialize  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a CodeAtlas SQLite database")
    parser.add_argument("--db", required=True)
    parser.add_argument("--schema")
    args = parser.parse_args()

    def action():
        database = Path(args.db).expanduser().resolve()
        schema = Path(args.schema).expanduser().resolve() if args.schema else None
        connection = initialize(database, schema)
        connection.close()
        return {"database": str(database), "initialized": True}

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
