import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database import open_existing
from .errors import CodeAtlasError


MAX_RESULTS = 50
MAX_REFERENCE_BYTES = 1_000_000


def _literal_contains(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def find_references(
    database: Path,
    *,
    kind: Optional[str] = None,
    name: Optional[str] = None,
    name_mode: str = "exact",
    hash_prefix: Optional[str] = None,
    module: Optional[str] = None,
    repository: Optional[str] = None,
    revision: Optional[str] = None,
    identifier: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    if not 1 <= limit <= MAX_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_RESULTS}")
    if name_mode not in {"exact", "contains"}:
        raise CodeAtlasError("name_mode must be exact or contains")
    if hash_prefix and (len(hash_prefix) < 4 or not re.fullmatch(r"[0-9a-fA-F]+", hash_prefix)):
        raise CodeAtlasError("hash must be a hexadecimal prefix of at least 4 characters")

    sql = """
        SELECT DISTINCT
            e.id, e.kind, e.name, e.normalized_hash,
            r.name AS repository, r.module,
            v.revision_name, v.resolved_commit,
            f.path, f.size_bytes, f.line_count,
            o.start_line, o.end_line
        FROM entities e
        JOIN occurrences o ON o.entity_id = e.id
        JOIN files f ON f.id = o.file_id
        JOIN revisions v ON v.id = f.revision_id
        JOIN repositories r ON r.id = v.repository_id
    """
    params: List[Any] = []
    where = ["1 = 1"]
    if identifier:
        sql += " JOIN artifact_identifiers ai ON ai.file_id = f.id"
        where.append("ai.identifier = ?")
        params.append(identifier)
    if kind:
        where.append("e.kind = ?")
        params.append(kind)
    if name:
        if name_mode == "exact":
            where.append("e.name = ?")
            params.append(name)
        else:
            where.append("e.name LIKE ? ESCAPE '\\'")
            params.append(_literal_contains(name))
    if hash_prefix:
        where.append("e.normalized_hash LIKE ?")
        params.append(hash_prefix.lower() + "%")
    if module:
        where.append("r.module = ? COLLATE NOCASE")
        params.append(module)
    if repository:
        where.append("r.name = ?")
        params.append(repository)
    if revision:
        where.append("v.revision_name = ?")
        params.append(revision)
    sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.name, r.name, v.revision_name, f.path, o.start_line LIMIT ?"
    params.append(limit + 1)

    connection = open_existing(database)
    try:
        rows = connection.execute(sql, params).fetchall()
    finally:
        connection.close()
    truncated = len(rows) > limit
    rows = rows[:limit]
    results = []
    for row in rows:
        start = int(row["start_line"])
        end = int(row["end_line"])
        results.append(
            {
                "id": int(row["id"]),
                "kind": row["kind"],
                "name": row["name"],
                "hash": row["normalized_hash"],
                "repository": row["repository"],
                "module": row["module"],
                "revision": row["revision_name"],
                "resolved_commit": row["resolved_commit"],
                "path": row["path"],
                "start_line": start,
                "end_line": end,
                "length_lines": end - start + 1,
                "file_size_bytes": int(row["size_bytes"]),
                "file_line_count": int(row["line_count"]),
            }
        )
    return {"count": len(results), "limit": limit, "truncated": truncated, "results": results}


def get_reference(database: Path, entity_id: int, *, max_bytes: int = 200_000) -> Dict[str, Any]:
    if entity_id < 1:
        raise CodeAtlasError("id must be a positive integer")
    if not 1 <= max_bytes <= MAX_REFERENCE_BYTES:
        raise CodeAtlasError(f"max_bytes must be between 1 and {MAX_REFERENCE_BYTES}")
    connection = open_existing(database)
    try:
        row = connection.execute(
            """
            SELECT e.id, e.kind, e.name, e.signature, e.normalized_hash,
                   e.metadata_json, b.content, b.byte_size, b.normalization
            FROM entities e
            JOIN content_blobs b ON b.id = e.blob_id
            WHERE e.id = ?
            """,
            (entity_id,),
        ).fetchone()
        if row is None:
            raise CodeAtlasError(f"Reference ID not found: {entity_id}")
        if int(row["byte_size"]) > max_bytes:
            raise CodeAtlasError(
                f"Reference is {row['byte_size']} bytes, above max_bytes={max_bytes}; "
                f"increase explicitly up to {MAX_REFERENCE_BYTES}"
            )
        occurrences = connection.execute(
            """
            SELECT r.name AS repository, r.module, v.revision_name, v.resolved_commit,
                   f.path, o.start_line, o.end_line
            FROM occurrences o
            JOIN files f ON f.id = o.file_id
            JOIN revisions v ON v.id = f.revision_id
            JOIN repositories r ON r.id = v.repository_id
            WHERE o.entity_id = ?
            ORDER BY r.name, v.revision_name, f.path, o.start_line
            """,
            (entity_id,),
        ).fetchall()
    finally:
        connection.close()
    try:
        metadata = json.loads(row["metadata_json"])
    except json.JSONDecodeError:
        metadata = {"raw": row["metadata_json"]}
    return {
        "reference": {
            "id": int(row["id"]),
            "kind": row["kind"],
            "name": row["name"],
            "signature": row["signature"],
            "hash": row["normalized_hash"],
            "normalization": row["normalization"],
            "size_bytes": int(row["byte_size"]),
            "metadata": metadata,
            "content": row["content"],
            "occurrences": [
                {
                    "repository": item["repository"],
                    "module": item["module"],
                    "revision": item["revision_name"],
                    "resolved_commit": item["resolved_commit"],
                    "path": item["path"],
                    "start_line": int(item["start_line"]),
                    "end_line": int(item["end_line"]),
                }
                for item in occurrences
            ],
        }
    }

