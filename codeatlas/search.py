import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .artifacts import extract_grl_definition
from .c_parser import CFunction
from .database import open_existing
from .errors import CodeAtlasError
from .similarity import SIMILARITY_METHOD, fingerprint_similarity


MAX_RESULTS = 50
MAX_REFERENCE_BYTES = 1_000_000
MAX_SIMILAR_RESULTS = 50
MAX_GRL_RESULTS = 50


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


def extract_grl_definitions(
    database: Path,
    identifier: str,
    *,
    limit: int = 50,
    revision: Optional[str] = None,
    all_revisions: bool = False,
) -> Dict[str, Any]:
    if not 1 <= limit <= MAX_GRL_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_GRL_RESULTS}")
    connection = open_existing(database)
    try:
        sql = """
            SELECT DISTINCT v.revision_name, v.resolved_commit, r.name AS repository,
                   r.module, f.path, b.content
            FROM artifact_identifiers ai
            JOIN files f ON f.id = ai.file_id
            JOIN content_blobs b ON b.id = f.blob_id
            JOIN revisions v ON v.id = f.revision_id
            JOIN repositories r ON r.id = v.repository_id
            WHERE f.kind = 'grr' AND ai.identifier = ?
        """
        params: List[Any] = [identifier]
        if revision:
            sql += " AND v.revision_name = ?"
            params.append(revision)
        sql += " ORDER BY v.revision_name LIMIT ?"
        params.append(limit + 1)
        rows = connection.execute(sql, params).fetchall()
        revision_rows = []
        if all_revisions:
            revision_rows = connection.execute(
                """
                SELECT v.revision_name,
                       EXISTS(SELECT 1 FROM files f WHERE f.revision_id = v.id AND f.kind = 'grr') AS has_grl
                FROM revisions v ORDER BY v.revision_name
                """
            ).fetchall()
    finally:
        connection.close()

    results = []
    for row in rows[:limit]:
        try:
            definition, start_line, end_line = extract_grl_definition(row["content"], identifier)
        except ValueError:
            continue
        results.append(
            {
                "repository": row["repository"],
                "module": row["module"],
                "revision": row["revision_name"],
                "resolved_commit": row["resolved_commit"],
                "path": row["path"],
                "start_line": start_line,
                "end_line": end_line,
                "definition": definition,
            }
        )
    output = {"identifier": identifier, "count": len(results), "truncated": len(rows) > limit, "results": results}
    if all_revisions:
        found = {item["revision"] for item in results}
        output["revisions"] = [
            {
                "revision": row["revision_name"],
                "status": "found" if row["revision_name"] in found else "absent",
                "has_grl": bool(row["has_grl"]),
            }
            for row in revision_rows
        ]
    return output


def rank_grl_identifiers(database: Path, *, limit: int = 20) -> Dict[str, Any]:
    if not 1 <= limit <= MAX_GRL_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_GRL_RESULTS}")
    connection = open_existing(database)
    try:
        rows = connection.execute(
            """
            SELECT ai.identifier, ai.identifier_kind,
                   COUNT(DISTINCT f.revision_id) AS revisions,
                   COUNT(DISTINCT v.repository_id) AS repositories
            FROM artifact_identifiers ai
            JOIN files f ON f.id = ai.file_id
            JOIN revisions v ON v.id = f.revision_id
            WHERE f.kind = 'grr'
            GROUP BY ai.identifier, ai.identifier_kind
            ORDER BY revisions DESC, ai.identifier
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    return {
        "limit": limit,
        "count": len(rows),
        "results": [
            {
                "identifier": row["identifier"],
                "kind": row["identifier_kind"],
                "revisions": int(row["revisions"]),
                "repositories": int(row["repositories"]),
            }
            for row in rows
        ],
    }


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


def list_implementations(
    database: Path,
    name: str,
    *,
    kind: str = "function",
    module: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Group exact implementations by entity/hash and retain all occurrences."""
    if not name:
        raise CodeAtlasError("name must not be empty")
    if not 1 <= limit <= MAX_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_RESULTS}")
    sql = """
        SELECT e.id, e.kind, e.name, e.signature, e.normalized_hash,
               COUNT(o.id) AS occurrence_count
        FROM entities e
        JOIN occurrences o ON o.entity_id = e.id
        JOIN files f ON f.id = o.file_id
        JOIN revisions v ON v.id = f.revision_id
        JOIN repositories r ON r.id = v.repository_id
        WHERE e.kind = ? AND e.name = ?
    """
    params: List[Any] = [kind, name]
    if module:
        sql += " AND r.module = ? COLLATE NOCASE"
        params.append(module)
    sql += " GROUP BY e.id ORDER BY occurrence_count DESC, e.normalized_hash LIMIT ?"
    params.append(limit + 1)
    connection = open_existing(database)
    try:
        rows = connection.execute(sql, params).fetchall()
        selected = rows[:limit]
        implementations = []
        for row in selected:
            occurrences = connection.execute(
                """
                SELECT r.name AS repository, r.module, v.revision_name,
                       v.resolved_commit, f.path, o.start_line, o.end_line
                FROM occurrences o
                JOIN files f ON f.id = o.file_id
                JOIN revisions v ON v.id = f.revision_id
                JOIN repositories r ON r.id = v.repository_id
                WHERE o.entity_id = ?
                ORDER BY r.name, v.revision_name, f.path, o.start_line
                """,
                (row["id"],),
            ).fetchall()
            implementations.append(
                {
                    "id": int(row["id"]),
                    "kind": row["kind"],
                    "name": row["name"],
                    "signature": row["signature"],
                    "hash": row["normalized_hash"],
                    "occurrence_count": int(row["occurrence_count"]),
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
            )
    finally:
        connection.close()
    return {
        "name": name,
        "kind": kind,
        "unique_implementations": len(implementations),
        "total_occurrences": sum(item["occurrence_count"] for item in implementations),
        "limit": limit,
        "truncated": len(rows) > limit,
        "implementations": implementations,
    }


def _target_similarity_data(
    connection: Any,
    entity_id: Optional[int],
    target_function: Optional[CFunction],
) -> Tuple[Optional[int], str, str, int]:
    if (entity_id is None) == (target_function is None):
        raise CodeAtlasError("provide exactly one indexed entity ID or target function")
    if target_function is not None:
        return None, target_function.name, target_function.similarity_fingerprint, target_function.token_count
    assert entity_id is not None
    if entity_id < 1:
        raise CodeAtlasError("id must be a positive integer")
    target = connection.execute(
        """
        SELECT id, name, similarity_method, similarity_fingerprint, token_count
        FROM entities WHERE id = ? AND kind = 'function'
        """,
        (entity_id,),
    ).fetchone()
    if target is None or not target["similarity_fingerprint"]:
        raise CodeAtlasError(f"Function with similarity fingerprint not found: {entity_id}")
    if target["similarity_method"] != SIMILARITY_METHOD:
        raise CodeAtlasError(
            f"Function uses unsupported similarity method: {target['similarity_method']}"
        )
    return int(target["id"]), target["name"], target["similarity_fingerprint"], int(target["token_count"])


def find_similar_functions(
    database: Path,
    entity_id: Optional[int] = None,
    *,
    target_function: Optional[CFunction] = None,
    candidate_name: Optional[str] = None,
    module: Optional[str] = None,
    limit: int = 10,
    min_score: float = 0.0,
) -> Dict[str, Any]:
    """Rank unique functions by deterministic token-shingle Jaccard similarity."""
    if not 1 <= limit <= MAX_SIMILAR_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_SIMILAR_RESULTS}")
    if not 0.0 <= min_score <= 1.0:
        raise CodeAtlasError("min_score must be between 0 and 1")

    connection = open_existing(database)
    try:
        target_id, target_name, target_fingerprint, target_token_count = _target_similarity_data(
            connection, entity_id, target_function
        )
        sql = """
            SELECT e.id, e.name, e.normalized_hash, e.similarity_method,
                   e.similarity_fingerprint, e.token_count,
                   COUNT(o.id) AS occurrence_count
            FROM entities e
            JOIN occurrences o ON o.entity_id = e.id
            JOIN files f ON f.id = o.file_id
            JOIN revisions v ON v.id = f.revision_id
            JOIN repositories r ON r.id = v.repository_id
            WHERE e.kind = 'function'
              AND e.similarity_method = ?
              AND e.similarity_fingerprint IS NOT NULL
        """
        params: List[Any] = [SIMILARITY_METHOD]
        if target_id is not None:
            sql += " AND e.id <> ?"
            params.append(target_id)
        if candidate_name:
            sql += " AND e.name = ?"
            params.append(candidate_name)
        if module:
            sql += " AND r.module = ? COLLATE NOCASE"
            params.append(module)
        if target_token_count:
            sql += " AND e.token_count BETWEEN ? AND ?"
            params.extend((max(1, target_token_count // 4), target_token_count * 4))
        sql += " GROUP BY e.id"
        candidates = connection.execute(sql, params).fetchall()

        ranked = []
        for row in candidates:
            score = fingerprint_similarity(target_fingerprint, row["similarity_fingerprint"])
            if score >= min_score:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["name"], int(item[1]["id"])))

        results = []
        for score, row in ranked[:limit]:
            occurrences = connection.execute(
                """
                SELECT r.name AS repository, r.module, v.revision_name,
                       v.resolved_commit, f.path, o.start_line, o.end_line
                FROM occurrences o
                JOIN files f ON f.id = o.file_id
                JOIN revisions v ON v.id = f.revision_id
                JOIN repositories r ON r.id = v.repository_id
                WHERE o.entity_id = ?
                ORDER BY r.name, v.revision_name, f.path, o.start_line
                LIMIT 6
                """,
                (row["id"],),
            ).fetchall()
            results.append(
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "hash": row["normalized_hash"],
                    "score": round(score, 6),
                    "token_count": int(row["token_count"]),
                    "occurrence_count": int(row["occurrence_count"]),
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
                        for item in occurrences[:5]
                    ],
                    "occurrences_truncated": len(occurrences) > 5,
                }
            )
    finally:
        connection.close()
    return {
        "target_id": target_id,
        "target_name": target_name,
        "target_token_count": target_token_count,
        "method": SIMILARITY_METHOD,
        "count": len(results),
        "limit": limit,
        "truncated": len(ranked) > limit,
        "results": results,
    }
