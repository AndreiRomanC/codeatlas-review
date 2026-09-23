from pathlib import Path

import pytest
import yaml

from codeatlas.config import load_config
from codeatlas.database import open_existing
from codeatlas.errors import CodeAtlasError
from codeatlas.indexer import index_module, index_status
from codeatlas.search import find_references, get_reference


FUNCTION_V1 = """static int Sample_Function(void)
{
    return 1;
}
"""

FUNCTION_V2 = """static int Sample_Function(void)
{
    return 2;
}
"""

GRL = """cFile 'sample_data.c' {
}
parameter c_sample_limit {
    value = 10;
}
"""


def _configured_project(tmp_path: Path):
    first = tmp_path / "repo-a"
    second = tmp_path / "repo-b"
    for root in (first, second):
        (root / "src").mkdir(parents=True)
        (root / "src" / "sample.c").write_text(FUNCTION_V1, encoding="utf-8")
        (root / "src" / "sample.grl").write_text(GRL, encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "repo-a": {
                        "module": "ERRM",
                        "local_path": str(first),
                        "revisions": [{"name": "main", "ref": "WORKTREE", "kind": "local"}],
                    },
                    "repo-b": {
                        "module": "ERRM",
                        "local_path": str(second),
                        "revisions": [{"name": "main", "ref": "WORKTREE", "kind": "local"}],
                    },
                },
                "specification": {"provider": "unconfigured"},
            }
        ),
        encoding="utf-8",
    )
    return load_config(str(config_path)), first, second


def test_dedup_occurrences_incremental_refresh_and_retrieval(tmp_path: Path):
    config, _first, second = _configured_project(tmp_path)
    initial = index_module(config, "ERRM")
    assert sum(item["stats"]["functions"] for item in initial) == 2

    connection = open_existing(config.database)
    assert connection.execute("SELECT COUNT(*) FROM entities WHERE kind = 'function'").fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM occurrences o JOIN entities e ON e.id = o.entity_id WHERE e.kind = 'function'"
    ).fetchone()[0] == 2
    assert connection.execute("SELECT COUNT(*) FROM entities WHERE kind = 'grr'").fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM occurrences o JOIN entities e ON e.id = o.entity_id WHERE e.kind = 'grr'"
    ).fetchone()[0] == 2
    connection.close()

    catalog = find_references(config.database, kind="function", name="Sample_Function", limit=10)
    assert catalog["count"] == 2
    assert catalog["results"][0]["id"] == catalog["results"][1]["id"]
    reference = get_reference(config.database, catalog["results"][0]["id"])
    assert len(reference["reference"]["occurrences"]) == 2
    assert "return 1" in reference["reference"]["content"]

    by_identifier = find_references(config.database, identifier="c_sample_limit", limit=10)
    assert by_identifier["count"] == 2
    assert index_status(config, "ERRM")["stale"] is False

    (second / "src" / "sample.c").write_text(FUNCTION_V2, encoding="utf-8")
    assert index_status(config, "ERRM")["stale"] is True
    refreshed = index_module(config, "ERRM")
    assert sum(item["stats"]["indexed"] for item in refreshed) == 1

    connection = open_existing(config.database)
    assert connection.execute("SELECT COUNT(*) FROM entities WHERE kind = 'function'").fetchone()[0] == 2
    assert connection.execute(
        "SELECT COUNT(*) FROM occurrences o JOIN entities e ON e.id = o.entity_id WHERE e.kind = 'function'"
    ).fetchone()[0] == 2
    connection.close()


@pytest.mark.parametrize("limit", [-1, 0, 51])
def test_candidate_limit_is_strict(tmp_path: Path, limit: int):
    config, _first, _second = _configured_project(tmp_path)
    index_module(config, "ERRM")
    with pytest.raises(CodeAtlasError, match="limit"):
        find_references(config.database, limit=limit)


def test_missing_reference_is_explicit(tmp_path: Path):
    config, _first, _second = _configured_project(tmp_path)
    index_module(config, "ERRM")
    with pytest.raises(CodeAtlasError, match="not found"):
        get_reference(config.database, 999999)

