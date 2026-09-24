from pathlib import Path
import subprocess

import pytest
import yaml

from codeatlas.config import load_config
from codeatlas.errors import ConfigurationError
from codeatlas.specification import SpecificationRequest, provider_from_config


def test_unconfigured_specification_is_reported_explicitly():
    provider = provider_from_config({"provider": "unconfigured"})
    result = provider.get(SpecificationRequest(module="ERRM", feature="example"))
    assert result.available is False
    assert result.content is None
    assert "not configured" in result.message


def _provider(root: Path):
    return provider_from_config(
        {
            "provider": "folder_txt",
            "roots": [str(root)],
            "directory_pattern": "agf/{module}/d",
            "recursive": False,
            "max_file_bytes": 10000,
        }
    )


def test_folder_txt_loads_latin1_and_preserves_provenance(tmp_path: Path):
    directory = tmp_path / "agf" / "module_a" / "d"
    directory.mkdir(parents=True)
    content = "Specification café\r\nRequirement 1\r\n"
    (directory / "SPEC_A.txt").write_bytes(content.encode("latin-1"))
    result = _provider(tmp_path).get(SpecificationRequest("module_a", revision="R1"))
    assert result.available is True
    assert result.content == "Specification café\nRequirement 1"
    assert result.provenance["revision_verified"] is False
    assert result.provenance["sources"][0]["path"].endswith("SPEC_A.txt")


def test_identical_txt_files_are_deduplicated_with_all_sources(tmp_path: Path):
    directory = tmp_path / "agf" / "module_a" / "d"
    directory.mkdir(parents=True)
    for name in ("SPEC_A.txt", "SPEC_A_copy.txt"):
        (directory / name).write_text("same specification\n", encoding="utf-8")
    result = _provider(tmp_path).get(SpecificationRequest("module_a"))
    assert result.available is True
    assert len(result.provenance["sources"]) == 2
    assert "identical files" in result.message


def test_distinct_documents_require_explicit_selection(tmp_path: Path):
    directory = tmp_path / "agf" / "module_a" / "d"
    directory.mkdir(parents=True)
    (directory / "SPEC_A.txt").write_text("first\n", encoding="utf-8")
    (directory / "SPEC_B.txt").write_text("second\n", encoding="utf-8")
    provider = _provider(tmp_path)
    ambiguous = provider.get(SpecificationRequest("module_a"))
    assert ambiguous.available is False
    assert "Multiple different" in ambiguous.message
    selected = provider.get(SpecificationRequest("module_a", document="SPEC_B"))
    assert selected.available is True
    assert selected.content == "second"


def test_specification_path_traversal_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="module"):
        _provider(tmp_path).get(SpecificationRequest("../module"))
    with pytest.raises(ConfigurationError, match="selector"):
        _provider(tmp_path).get(SpecificationRequest("module", document="../secret.txt"))


def test_unknown_directory_pattern_placeholder_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="placeholder"):
        provider_from_config(
            {
                "provider": "folder_txt",
                "roots": [str(tmp_path)],
                "directory_pattern": "{unknown}/{module}/d",
            }
        )


def test_repository_backed_specification_tracks_configured_revision(tmp_path: Path):
    source = tmp_path / "source"
    directory = source / "agf" / "module_a" / "d"
    directory.mkdir(parents=True)
    (directory / "SPEC.txt").write_text("versioned requirement\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main", str(source)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-m", "spec"], check=True, capture_output=True)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "database": "atlas.db",
                "cache_dir": "cache",
                "repositories": {
                    "remote": {
                        "module": "module_a",
                        "url": source.as_uri(),
                        "revisions": [{"name": "main", "ref": "main", "kind": "branch"}],
                    }
                },
                "specification": {
                    "provider": "folder_txt",
                    "repository": "remote",
                    "revision": "main",
                    "directory_pattern": "agf/{module}/d",
                },
            }
        ),
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    provider = provider_from_config(
        config.specification, base_dir=config.path.parent, codeatlas_config=config
    )
    result = provider.get(SpecificationRequest("module_a"))
    assert result.available is True
    assert result.content == "versioned requirement"
    assert result.provenance["revision_verified"] is True
    assert result.provenance["revision"] == "main"
