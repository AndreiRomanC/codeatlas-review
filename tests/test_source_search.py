from pathlib import Path

import yaml

from codeatlas.config import load_config
from codeatlas.source_search import search_source


def test_bounded_source_search_returns_provenance_and_context(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.c").write_text(
        "int dependency(void);\nint target(void) {\n    return dependency();\n}\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "local": {
                        "module": "DEMO",
                        "local_path": str(source),
                        "revisions": [{"name": "working", "ref": "WORKTREE", "kind": "local"}],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    result = search_source(load_config(str(config_path)), "DEMO", "dependency", context=1)
    assert result["count"] == 2
    assert result["results"][0]["repository"] == "local"
    assert result["results"][0]["path"] == "sample.c"
    assert len(result["results"][0]["context"]) <= 3
