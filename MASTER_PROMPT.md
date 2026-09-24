# CodeAtlas Review — Current Design Contract

Improve the existing CodeAtlas Review implementation incrementally. Preserve working behavior and database compatibility; do not rebuild the project merely to change its AI integration layer.

## Primary rule: script first, AI second

Use deterministic CodeAtlas commands for repository acquisition, revision discovery, parsing, extraction, exact hashing, similarity fingerprints, indexing, filtering, grouping, searching, and retrieval. Do not use the model as a search engine for facts that these commands can establish.

Use model reasoning for specification interpretation, relevance selection, semantic differences, risk assessment, and review findings. If a repeatable deterministic operation is missing, add a small bounded command instead of repeatedly performing ad-hoc shell searches.

## Source of truth

The applicable specification is authoritative. Reference implementations are non-authoritative evidence and may be wrong, obsolete, project-specific, or based on a different specification revision. Report conflicts between reference consensus and the specification explicitly.

## Indexed engineering memory

SQLite is a general reference index containing repositories, revisions, files, entities, occurrences, identifiers, index runs, and errors. Preserve repository, revision, resolved commit, path, and line provenance.

Store exact content once and preserve every occurrence. Exact normalized SHA-256 answers whether implementations are identical. A separate versioned token fingerprint ranks approximate similarity. Never store all function-to-function pairs.

## Controlled retrieval

Use two stages:

1. compact search metadata, exact implementation grouping, or similarity ranking;
2. full retrieval only for selected IDs.

Never send complete repositories, database dumps, or large collections of implementations to the model. Use bounded deterministic source-context search only when indexed entities do not contain the required context.

## Repository and runtime behavior

- Resolve repositories and revisions from configuration.
- Fetch configured remote refs rather than relying on incidental local branches.
- Use CodeAtlas-owned mirrors and immutable snapshots.
- Never reset, clean, commit, push, or modify configured source repositories.
- Discover a compatible Python interpreter, preferring an explicit setting, AURA/project venv, or approved company installation.
- Do not install Python automatically or embed credentials.

## Artifacts and specification

Keep GRL/GRR indexing simple in V1: file-level exact deduplication, deterministic identifier extraction, bounded definition retrieval, and provenance. Do not invent a complete grammar.

Use the `folder_txt` provider for current specifications in module `d` folders. Prefer repository/revision-backed roots when the specification is versioned with code. Keep LIMAS as a future adapter behind the same interface.

## Copilot integration

The Python package, SQLite schema, configuration, and tests remain independent. GitHub Copilot uses the thin project skill in `.github/skills/codeatlas-review/`, following the AURA pattern of a short `SKILL.md` router with conditional references and deterministic scripts.

Do not copy the database or repository caches into the skill. Keep `.codeatlas/` local and ignored. Integrate into AURA later through a thin versioned wrapper or package dependency after the core behavior is stable.

## Validation requirements

Test remote revision acquisition, interpreter selection, exact deduplication, occurrence preservation, different implementations, high/low similarity, compact search without bodies, targeted retrieval, GRL lookup/deduplication, repository-backed specifications, and the real representative ERRM files when available.

Success means CodeAtlas can establish where implementations/configuration exist, which variants are identical or similar, and which revisions contain them. The AI then explains why differences matter and whether the target complies with its specification.
