import subprocess
from pathlib import Path

import yaml

from codeatlas.config import load_config
from codeatlas.indexer import index_module
from codeatlas.repository import list_available_revisions, prepare_module
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


def test_remote_refresh_obtains_new_commit_and_lists_actual_refs(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "codeatlas@example.invalid")
    _git(source, "config", "user.name", "CodeAtlas Test")
    (source / "sample.c").write_text("int first(void) { return 1; }\n", encoding="utf-8")
    _git(source, "add", "sample.c")
    _git(source, "commit", "-m", "first")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "remote": {
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
    prepare_module(config, "REMOTE")
    first_commit = index_module(config, "REMOTE")[0]["resolved_commit"]

    (source / "sample.c").write_text("int second(void) { return 2; }\n", encoding="utf-8")
    _git(source, "add", "sample.c")
    _git(source, "commit", "-m", "second")
    second_commit = _git(source, "rev-parse", "HEAD")
    assert second_commit != first_commit

    prepare_module(config, "REMOTE", update=True)
    refreshed = index_module(config, "REMOTE")
    assert refreshed[0]["resolved_commit"] == second_commit
    refs = list_available_revisions(config, "REMOTE")
    assert any(item["name"] == "main" for item in refs["repositories"][0]["refs"])


def test_local_git_revision_snapshot_does_not_touch_dirty_worktree(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.email", "codeatlas@example.invalid")
    _git(source, "config", "user.name", "CodeAtlas Test")
    tracked = source / "sample.c"
    tracked.write_text("int main_version(void) { return 1; }\n", encoding="utf-8")
    _git(source, "add", "sample.c")
    _git(source, "commit", "-m", "main")
    main_commit = _git(source, "rev-parse", "HEAD")
    _git(source, "switch", "-c", "variant")
    tracked.write_text("int variant_version(void) { return 2; }\n", encoding="utf-8")
    _git(source, "commit", "-am", "variant")
    _git(source, "switch", "main")
    tracked.write_text("int dirty_worktree(void) { return 3; }\n", encoding="utf-8")
    status_before = _git(source, "status", "--porcelain")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "local-git": {
                        "module": "LOCAL",
                        "local_path": str(source),
                        "revisions": [
                            {"name": "variant", "ref": "variant", "kind": "branch"}
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    indexed = index_module(config, "LOCAL")
    assert indexed[0]["resolved_commit"] != main_commit
    assert _git(source, "rev-parse", "HEAD") == main_commit
    assert tracked.read_text(encoding="utf-8").startswith("int dirty_worktree")
    assert _git(source, "status", "--porcelain") == status_before
    assert find_references(config.database, name="variant_version")["count"] == 1
