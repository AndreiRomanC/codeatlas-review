import subprocess
from pathlib import Path

import yaml

from codeatlas.config import load_config
from codeatlas.indexer import index_module
from codeatlas.repository import prepare_module
from codeatlas.search import find_references


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_git_reference_uses_mirror_and_immutable_snapshot(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "codeatlas@example.invalid")
    _git(source, "config", "user.name", "CodeAtlas Test")
    (source / "sample.c").write_text("int remote_sample(void) { return 7; }\n", encoding="utf-8")
    _git(source, "add", "sample.c")
    _git(source, "commit", "-m", "fixture")
    head_before = _git(source, "rev-parse", "HEAD")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "remote-fixture": {
                        "module": "REMOTE",
                        "url": source.as_uri(),
                        "revisions": [{"name": "main", "ref": "main", "kind": "branch"}],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    prepared = prepare_module(config, "REMOTE")
    assert prepared[0]["cloned"] is True
    result = index_module(config, "REMOTE")
    assert result[0]["resolved_commit"] == head_before
    assert _git(source, "rev-parse", "HEAD") == head_before
    assert _git(source, "status", "--porcelain") == ""
    catalog = find_references(config.database, name="remote_sample")
    assert catalog["count"] == 1

