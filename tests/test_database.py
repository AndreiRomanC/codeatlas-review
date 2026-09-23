import sqlite3
from pathlib import Path

import pytest

from codeatlas.database import initialize
from codeatlas.errors import CodeAtlasError


def test_database_initialization_is_idempotent(tmp_path: Path):
    database = tmp_path / "nested" / "atlas.db"
    first = initialize(database)
    first.close()
    second = initialize(database)
    version = second.execute(
        "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
    ).fetchone()["value"]
    second.close()
    assert version == "1"


def test_legacy_unversioned_database_is_rejected(tmp_path: Path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE repositories(id INTEGER PRIMARY KEY)")
    with pytest.raises(CodeAtlasError, match="Legacy unversioned"):
        initialize(database)

