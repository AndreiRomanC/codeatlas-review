import sqlite3
from pathlib import Path
from typing import Optional

from . import SCHEMA_VERSION
from .errors import CodeAtlasError


def schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schema.sql"


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize(path: Path, schema: Optional[Path] = None) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    tables = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "repositories" in tables and "schema_metadata" not in tables:
        connection.close()
        raise CodeAtlasError(
            "Legacy unversioned CodeAtlas database detected; rebuild it with the current schema"
        )
    if "schema_metadata" in tables:
        version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if version is not None and version["value"] == "1":
            connection.execute("ALTER TABLE entities ADD COLUMN structural_hash TEXT")
            connection.execute("ALTER TABLE entities ADD COLUMN structural_signature TEXT")
            connection.execute("UPDATE schema_metadata SET value = '2' WHERE key = 'schema_version'")
            connection.commit()
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
        if version is not None and version["value"] == "2":
            connection.execute("ALTER TABLE entities ADD COLUMN similarity_method TEXT")
            connection.execute("ALTER TABLE entities ADD COLUMN similarity_fingerprint TEXT")
            connection.execute("ALTER TABLE entities ADD COLUMN token_count INTEGER")
            connection.execute("UPDATE schema_metadata SET value = '3' WHERE key = 'schema_version'")
            connection.commit()
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
        if version is None or version["value"] != SCHEMA_VERSION:
            connection.close()
            value = version["value"] if version is not None else "missing"
            raise CodeAtlasError(f"Database migration required for schema version: {value}")
    connection.executescript((schema or schema_path()).read_text(encoding="utf-8"))
    version = connection.execute(
        "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
    ).fetchone()
    if version is None or version["value"] != SCHEMA_VERSION:
        connection.close()
        value = version["value"] if version is not None else "missing"
        raise CodeAtlasError(f"Unsupported database schema version: {value}")
    return connection


def open_existing(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise CodeAtlasError(f"Database not found: {path}")
    connection = connect(path)
    try:
        version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        connection.close()
        raise CodeAtlasError(f"Invalid CodeAtlas database: {path}") from exc
    if version is None or version["value"] != SCHEMA_VERSION:
        connection.close()
        raise CodeAtlasError("Database schema version is missing or unsupported")
    return connection
