import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.config import load_config  # noqa: E402
from codeatlas.jsonio import run_cli  # noqa: E402
from codeatlas.specification import SpecificationRequest, provider_from_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve a specification through the configured adapter")
    parser.add_argument("--config", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--feature")
    parser.add_argument("--revision")
    parser.add_argument("--document", help="Exact .txt filename or stem when a module has distinct documents")
    args = parser.parse_args()

    def action():
        config = load_config(args.config)
        provider = provider_from_config(
            config.specification, base_dir=config.path.parent, codeatlas_config=config
        )
        result = provider.get(
            SpecificationRequest(args.module, args.feature, args.revision, args.document)
        )
        return {
            "request": {
                "module": args.module,
                "feature": args.feature,
                "revision": args.revision,
                "document": args.document,
            },
            "result": result.to_dict(),
        }

    return run_cli(action)


if __name__ == "__main__":
    raise SystemExit(main())
