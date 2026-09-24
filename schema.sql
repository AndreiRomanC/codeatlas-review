PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_metadata(key, value) VALUES ('schema_version', '3');

CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    module TEXT NOT NULL,
    origin TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('local', 'git'))
);

CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    revision_name TEXT NOT NULL,
    revision_kind TEXT NOT NULL,
    resolved_commit TEXT NOT NULL,
    indexed_at TEXT,
    index_version TEXT,
    UNIQUE(repository_id, revision_name, resolved_commit),
    FOREIGN KEY(repository_id) REFERENCES repositories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_blobs (
    id INTEGER PRIMARY KEY,
    content_hash TEXT NOT NULL,
    normalization TEXT NOT NULL,
    content TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    UNIQUE(content_hash, normalization)
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    revision_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    encoding TEXT,
    size_bytes INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    blob_id INTEGER,
    index_version TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    UNIQUE(revision_id, path),
    FOREIGN KEY(revision_id) REFERENCES revisions(id) ON DELETE CASCADE,
    FOREIGN KEY(blob_id) REFERENCES content_blobs(id)
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    signature TEXT,
    normalized_hash TEXT NOT NULL,
    structural_hash TEXT,
    structural_signature TEXT,
    similarity_method TEXT,
    similarity_fingerprint TEXT,
    token_count INTEGER,
    blob_id INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(kind, name, normalized_hash),
    FOREIGN KEY(blob_id) REFERENCES content_blobs(id)
);

CREATE TABLE IF NOT EXISTS occurrences (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    start_byte INTEGER,
    end_byte INTEGER,
    UNIQUE(entity_id, file_id, start_line, end_line),
    FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifact_identifiers (
    file_id INTEGER NOT NULL,
    identifier TEXT NOT NULL,
    identifier_kind TEXT NOT NULL,
    PRIMARY KEY(file_id, identifier, identifier_kind),
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS index_runs (
    id INTEGER PRIMARY KEY,
    revision_id INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    index_version TEXT NOT NULL,
    stats_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    FOREIGN KEY(revision_id) REFERENCES revisions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS index_errors (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES index_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_repositories_module ON repositories(module);
CREATE INDEX IF NOT EXISTS idx_revisions_lookup ON revisions(repository_id, revision_name, resolved_commit);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities(kind);
CREATE INDEX IF NOT EXISTS idx_entities_hash ON entities(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_entities_structural_hash ON entities(structural_hash);
CREATE INDEX IF NOT EXISTS idx_entities_similarity_method ON entities(similarity_method);
CREATE INDEX IF NOT EXISTS idx_occurrences_entity ON occurrences(entity_id);
CREATE INDEX IF NOT EXISTS idx_artifact_identifiers_identifier ON artifact_identifiers(identifier);
