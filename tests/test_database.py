import sqlite3
from pathlib import Path

import pytest

from codeatlas import SCHEMA_VERSION
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
    assert version == SCHEMA_VERSION


def test_schema_v1_is_migrated_without_rebuilding_database(tmp_path: Path):
    database = tmp_path / "v1.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO schema_metadata(key, value) VALUES ('schema_version', '1');
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                signature TEXT,
                normalized_hash TEXT NOT NULL,
                blob_id INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(kind, name, normalized_hash)
            );
            """
        )
    connection = initialize(database)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
    version = connection.execute(
        "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
    ).fetchone()["value"]
    connection.close()
    assert version == SCHEMA_VERSION
    assert {"similarity_method", "similarity_fingerprint", "token_count"} <= columns


def test_schema_v2_is_migrated_to_token_fingerprints(tmp_path: Path):
    database = tmp_path / "v2.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO schema_metadata(key, value) VALUES ('schema_version', '2');
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                signature TEXT,
                normalized_hash TEXT NOT NULL,
                structural_hash TEXT,
                structural_signature TEXT,
                blob_id INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(kind, name, normalized_hash)
            );
            """
        )
    connection = initialize(database)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
    version = connection.execute(
        "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
    ).fetchone()["value"]
    connection.close()
    assert version == SCHEMA_VERSION
    assert {"similarity_method", "similarity_fingerprint", "token_count"} <= columns


def test_legacy_unversioned_database_is_rejected(tmp_path: Path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE repositories(id INTEGER PRIMARY KEY)")
    with pytest.raises(CodeAtlasError, match="Legacy unversioned"):
        initialize(database)
