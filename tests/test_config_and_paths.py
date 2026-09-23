from pathlib import Path

import pytest

from codeatlas.config import load_config
from codeatlas.errors import CodeAtlasError, ConfigurationError
from codeatlas.paths import _matches, portable_relative_path


def test_windows_separator_is_normalized():
    assert portable_relative_path(r"agf\module\file.c") == "agf/module/file.c"


def test_recursive_glob_includes_root_and_nested_files():
    assert _matches("sample.c", ("**/*.c",))
    assert _matches("src/sample.c", ("**/*.c",))


@pytest.mark.parametrize("value", ["../secret", "/absolute/file.c", r"..\secret", r"C:\absolute\file.c"])
def test_unsafe_relative_path_is_rejected(value):
    with pytest.raises(CodeAtlasError):
        portable_relative_path(value)


def test_http_credentials_are_rejected(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
repositories:
  unsafe:
    module: ERRM
    url: https://user:secret@example.invalid/repo.git
    revisions: [main]
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="credentials"):
        load_config(str(config))


def test_malformed_yaml_is_reported_as_configuration_error(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("repositories: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_config(str(config))
