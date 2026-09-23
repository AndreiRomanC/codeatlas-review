import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from . import INDEX_VERSION
from .artifacts import extract_artifact_identifiers
from .c_parser import CFunction, extract_functions
from .config import CodeAtlasConfig, RepositoryConfig
from .database import initialize, open_existing
from .errors import CodeAtlasError, ParserUnavailableError
from .hashing import decode_text, sha256_bytes
from .paths import iter_index_files
from .repository import SourceRevision, source_revision


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _line_count(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _repository_id(connection: sqlite3.Connection, repository: RepositoryConfig) -> int:
    connection.execute(
        """
        INSERT INTO repositories(name, module, origin, source_type)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            module = excluded.module,
            origin = excluded.origin,
            source_type = excluded.source_type
        """,
        (repository.name, repository.module, repository.origin, repository.source_type),
    )
    row = connection.execute("SELECT id FROM repositories WHERE name = ?", (repository.name,)).fetchone()
    assert row is not None
    return int(row["id"])


def _revision_id(
    connection: sqlite3.Connection,
    repository_id: int,
    source: SourceRevision,
) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO revisions(
            repository_id, revision_name, revision_kind, resolved_commit
        ) VALUES (?, ?, ?, ?)
        """,
        (repository_id, source.revision_name, source.revision_kind, source.resolved_commit),
    )
    row = connection.execute(
        """
        SELECT id FROM revisions
        WHERE repository_id = ? AND revision_name = ? AND resolved_commit = ?
        """,
        (repository_id, source.revision_name, source.resolved_commit),
    ).fetchone()
    assert row is not None
    return int(row["id"])


def _blob_id(
    connection: sqlite3.Connection,
    content_hash: str,
    normalization: str,
    content: str,
) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO content_blobs(content_hash, normalization, content, byte_size)
        VALUES (?, ?, ?, ?)
        """,
        (content_hash, normalization, content, len(content.encode("utf-8"))),
    )
    row = connection.execute(
        "SELECT id FROM content_blobs WHERE content_hash = ? AND normalization = ?",
        (content_hash, normalization),
    ).fetchone()
    assert row is not None
    return int(row["id"])


def _entity_id(
    connection: sqlite3.Connection,
    *,
    kind: str,
    name: str,
    signature: Optional[str],
    normalized_hash: str,
    blob_id: int,
    metadata: Mapping[str, Any],
) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO entities(
            kind, name, signature, normalized_hash, blob_id, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (kind, name, signature, normalized_hash, blob_id, json.dumps(metadata, sort_keys=True)),
    )
    row = connection.execute(
        "SELECT id FROM entities WHERE kind = ? AND name = ? AND normalized_hash = ?",
        (kind, name, normalized_hash),
    ).fetchone()
    assert row is not None
    return int(row["id"])


def _index_function(connection: sqlite3.Connection, file_id: int, function: CFunction) -> None:
    blob_id = _blob_id(
        connection,
        function.normalized_hash,
        "c-conservative-v1",
        function.content,
    )
    entity_id = _entity_id(
        connection,
        kind="function",
        name=function.name,
        signature=function.signature,
        normalized_hash=function.normalized_hash,
        blob_id=blob_id,
        metadata={"parser": "tree-sitter-c", "parse_has_error": function.parse_has_error},
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO occurrences(
            entity_id, file_id, start_line, end_line, start_byte, end_byte
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            file_id,
            function.start_line,
            function.end_line,
            function.start_byte,
            function.end_byte,
        ),
    )


def _index_artifact(
    connection: sqlite3.Connection,
    file_id: int,
    path: str,
    kind: str,
    data: bytes,
    line_count: int,
) -> None:
    text, _encoding = decode_text(data)
    digest = sha256_bytes(data)
    blob_id = _blob_id(connection, digest, "raw-file-v1", text)
    identifiers = extract_artifact_identifiers(kind, text)
    entity_id = _entity_id(
        connection,
        kind=kind,
        name=Path(path).name,
        signature=None,
        normalized_hash=digest,
        blob_id=blob_id,
        metadata={"identifier_count": len(identifiers), "scope": "file"},
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO occurrences(entity_id, file_id, start_line, end_line)
        VALUES (?, ?, ?, ?)
        """,
        (entity_id, file_id, 1, max(line_count, 1)),
    )
    connection.executemany(
        "INSERT OR IGNORE INTO artifact_identifiers(file_id, identifier, identifier_kind) VALUES (?, ?, ?)",
        ((file_id, identifier, identifier_kind) for identifier, identifier_kind in identifiers),
    )


def _cleanup_orphans(connection: sqlite3.Connection) -> None:
    connection.execute(
        "DELETE FROM entities WHERE NOT EXISTS (SELECT 1 FROM occurrences WHERE occurrences.entity_id = entities.id)"
    )
    connection.execute(
        """
        DELETE FROM content_blobs
        WHERE NOT EXISTS (SELECT 1 FROM files WHERE files.blob_id = content_blobs.id)
          AND NOT EXISTS (SELECT 1 FROM entities WHERE entities.blob_id = content_blobs.id)
        """
    )


def _index_revision(
    connection: sqlite3.Connection,
    config: CodeAtlasConfig,
    repository: RepositoryConfig,
    source: SourceRevision,
    *,
    force: bool,
) -> Dict[str, Any]:
    repository_id = _repository_id(connection, repository)
    revision_id = _revision_id(connection, repository_id, source)
    started = _now()
    cursor = connection.execute(
        """
        INSERT INTO index_runs(revision_id, started_at, status, index_version)
        VALUES (?, ?, 'running', ?)
        """,
        (revision_id, started, INDEX_VERSION),
    )
    run_id = int(cursor.lastrowid)
    connection.commit()
    existing = {
        row["path"]: row
        for row in connection.execute(
            "SELECT id, path, content_hash, index_version FROM files WHERE revision_id = ?",
            (revision_id,),
        )
    }
    seen: Set[str] = set()
    stats: Dict[str, int] = {
        "discovered": 0,
        "indexed": 0,
        "unchanged": 0,
        "removed": 0,
        "functions": 0,
        "artifacts": 0,
        "errors": 0,
        "skipped_large": 0,
    }
    try:
        for relative, file_path in iter_index_files(source.root, config.index.include, config.index.exclude):
            stats["discovered"] += 1
            seen.add(relative)
            size = file_path.stat().st_size
            previous = existing.get(relative)
            if size > config.index.max_file_bytes:
                if previous is not None:
                    connection.execute("DELETE FROM files WHERE id = ?", (previous["id"],))
                stats["skipped_large"] += 1
                connection.execute(
                    "INSERT INTO index_errors(run_id, path, message) VALUES (?, ?, ?)",
                    (run_id, relative, f"File exceeds max_file_bytes ({size})"),
                )
                continue
            data = file_path.read_bytes()
            digest = sha256_bytes(data)
            if (
                not force
                and previous is not None
                and previous["content_hash"] == digest
                and previous["index_version"] == INDEX_VERSION
            ):
                stats["unchanged"] += 1
                continue
            if previous is not None:
                connection.execute("DELETE FROM files WHERE id = ?", (previous["id"],))

            suffix = file_path.suffix.lower()
            artifact_kind = config.index.artifact_kind_for(suffix)
            kind = "c-source" if suffix == ".c" else "c-header" if suffix == ".h" else artifact_kind or "file"
            text, encoding = decode_text(data)
            line_count = _line_count(data)
            file_blob_id = None
            if artifact_kind:
                file_blob_id = _blob_id(connection, digest, "raw-file-v1", text)
            cursor = connection.execute(
                """
                INSERT INTO files(
                    revision_id, path, kind, encoding, size_bytes, line_count,
                    content_hash, blob_id, index_version, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    relative,
                    kind,
                    encoding,
                    len(data),
                    line_count,
                    digest,
                    file_blob_id,
                    INDEX_VERSION,
                    _now(),
                ),
            )
            file_id = int(cursor.lastrowid)
            try:
                if suffix == ".c":
                    functions = extract_functions(data)
                    for function in functions:
                        _index_function(connection, file_id, function)
                    stats["functions"] += len(functions)
                elif artifact_kind:
                    _index_artifact(connection, file_id, relative, artifact_kind, data, line_count)
                    stats["artifacts"] += 1
            except ParserUnavailableError:
                raise
            except Exception as exc:
                stats["errors"] += 1
                connection.execute(
                    "INSERT INTO index_errors(run_id, path, message) VALUES (?, ?, ?)",
                    (run_id, relative, str(exc)),
                )
            stats["indexed"] += 1

        for relative, row in existing.items():
            if relative not in seen:
                connection.execute("DELETE FROM files WHERE id = ?", (row["id"],))
                stats["removed"] += 1
        _cleanup_orphans(connection)
        finished = _now()
        connection.execute(
            """
            UPDATE revisions SET indexed_at = ?, index_version = ? WHERE id = ?
            """,
            (finished, INDEX_VERSION, revision_id),
        )
        connection.execute(
            """
            UPDATE index_runs
            SET finished_at = ?, status = 'complete', stats_json = ?
            WHERE id = ?
            """,
            (finished, json.dumps(stats, sort_keys=True), run_id),
        )
        connection.commit()
        return {
            "repository": repository.name,
            "module": repository.module,
            "revision": source.revision_name,
            "resolved_commit": source.resolved_commit,
            "stats": stats,
        }
    except Exception as exc:
        connection.rollback()
        connection.execute(
            """
            UPDATE index_runs
            SET finished_at = ?, status = 'failed', stats_json = ?, error = ?
            WHERE id = ?
            """,
            (_now(), json.dumps(stats, sort_keys=True), str(exc), run_id),
        )
        connection.commit()
        raise


def index_module(config: CodeAtlasConfig, module: str, *, force: bool = False) -> List[Dict[str, Any]]:
    connection = initialize(config.database)
    results: List[Dict[str, Any]] = []
    try:
        for repository in config.repositories_for_module(module):
            for revision in repository.revisions:
                source = source_revision(config, repository, revision)
                results.append(
                    _index_revision(connection, config, repository, source, force=force)
                )
    finally:
        connection.close()
    return results


def _current_hashes(config: CodeAtlasConfig, root: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for relative, path in iter_index_files(root, config.index.include, config.index.exclude):
        if path.stat().st_size <= config.index.max_file_bytes:
            hashes[relative] = sha256_bytes(path.read_bytes())
    return hashes


def index_status(config: CodeAtlasConfig, module: str) -> Dict[str, Any]:
    if not config.database.is_file():
        return {"initialized": False, "stale": True, "repositories": []}
    connection = open_existing(config.database)
    statuses: List[Dict[str, Any]] = []
    try:
        for repository in config.repositories_for_module(module):
            for revision in repository.revisions:
                source = source_revision(config, repository, revision)
                row = connection.execute(
                    """
                    SELECT v.id, v.indexed_at, v.index_version
                    FROM revisions v JOIN repositories r ON r.id = v.repository_id
                    WHERE r.name = ? AND v.revision_name = ? AND v.resolved_commit = ?
                    """,
                    (repository.name, source.revision_name, source.resolved_commit),
                ).fetchone()
                if row is None:
                    statuses.append(
                        {
                            "repository": repository.name,
                            "revision": source.revision_name,
                            "indexed": False,
                            "stale": True,
                        }
                    )
                    continue
                current = _current_hashes(config, source.root)
                indexed = {
                    item["path"]: item["content_hash"]
                    for item in connection.execute(
                        "SELECT path, content_hash FROM files WHERE revision_id = ?", (row["id"],)
                    )
                }
                added = sorted(set(current) - set(indexed))
                removed = sorted(set(indexed) - set(current))
                changed = sorted(path for path in set(current) & set(indexed) if current[path] != indexed[path])
                stale = bool(added or removed or changed or row["index_version"] != INDEX_VERSION)
                statuses.append(
                    {
                        "repository": repository.name,
                        "revision": source.revision_name,
                        "indexed": True,
                        "indexed_at": row["indexed_at"],
                        "stale": stale,
                        "added": len(added),
                        "changed": len(changed),
                        "removed": len(removed),
                    }
                )
    finally:
        connection.close()
    return {
        "initialized": True,
        "stale": any(item["stale"] for item in statuses),
        "repositories": statuses,
    }
