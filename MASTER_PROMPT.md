# CodeAtlas Review — Master Prompt for Codex

Implement and harden the attached `CodeAtlas_Review` starter as a reusable AI Agent Skill.

## Objective
Create a spec-grounded review system for automotive software. It must use historical/reference implementations as non-authoritative evidence without loading entire repositories into LLM context.

## Fundamental split
**Scripts do deterministic mechanics. The LLM does orchestration and reasoning.**

Scripts must handle repository acquisition, deterministic parsing, normalization, SHA-256 hashing, deduplication, SQLite indexing, candidate search, and exact retrieval. The LLM decides what evidence is relevant and performs the semantic review.

## Source-of-truth rule
The applicable specification is authoritative. Reference code can be wrong, old, project-specific, or based on another specification revision. Never mark code correct merely because references do the same thing, and never mark it wrong merely because it differs. Explicitly flag conflicts between common historical patterns and the specification.

## Required workflow
1. User requests review of a module/file/function/GRR artifact.
2. Resolve repository/module/revision from configuration or parameters; do not hard-code company paths.
3. Ensure required reference repositories are locally available. Clone/fetch safely only when needed.
4. Reuse the SQLite index if current; support incremental refresh and forced rebuild.
5. Parse source deterministically. Do not use the LLM to find function boundaries.
6. Extract function name, signature where possible, file, start/end lines, body, normalized body, and SHA-256 content hash.
7. Deduplicate identical normalized entities across repositories/revisions, while preserving every occurrence and provenance.
8. Index GRR as a first-class artifact. Initially use robust file-level indexing: hash, path, size, line count, identifiers/names, full content stored once. Only create GRR sub-entities after inspecting real examples.
9. Search returns only a compact candidate catalog: ID, kind/name, repo, revision, path, line range/size, hash prefix, and useful metadata.
10. The LLM selects only a few IDs (normally 2–4).
11. A separate retrieval command returns full content for selected IDs.
12. Obtain the relevant specification through a configurable adapter. Do not invent LIMAS/internal API details.
13. Review target against specification first; use references for patterns, edge cases, drift, and questions.
14. Fetch more context only on demand.

## SQLite
Use the provided generic schema as a starting point, not a fixed final design. Keep repositories, revisions, files, deduplicated entities, and occurrences. Make the DB reusable for future searches such as “find this function everywhere.” Use parameterized SQL and useful indexes.

The entity hash is our own SHA-256 over normalized extracted content; it is NOT a Git commit hash.

## Parsing
Prefer, based on what is permitted in the real environment:
1. existing approved project parser/tool;
2. tree-sitter C;
3. libclang/Clang;
4. another robust parser;
5. clearly documented bootstrap fallback.

Inspect representative real C before finalizing parsing/normalization. Normalization must be conservative enough not to collapse semantically different code.

## Repository acquisition
Implement `fetch_repos.py` with configurable module/repo mapping, local cache, revision selection, and existing authentication. Never store credentials. Never reset/clean/push/commit reference repositories. Detect local modifications and fail safely.

## Retrieval commands
Provide machine-readable JSON CLIs conceptually like:
- `fetch_repos.py --module MODULE --config config.yaml`
- `build_index.py --module MODULE --config config.yaml`
- `index_status.py --module MODULE --config config.yaml`
- `find_references.py --kind function --name NAME --limit 10 --db ...`
- `get_reference.py --id ID --db ...`
- GRR search by identifier/name.

Add strict result/content limits to prevent context explosion.

## Specification adapter
Create an interface for the real specification provider. The user will later supply where/how specs are accessed. If unavailable, report that explicitly rather than pretending.

## Review output
Separate:
- Summary
- Specification findings
- Defects / risks
- Reference comparison
- Drift / inconsistencies
- Uncertainties / missing evidence
- Recommended checks

Every reference comparison should preserve provenance (repo/revision/file/entity/lines).

## Tests
Add tests for deterministic hashing, duplicate bodies across revisions, same name/different body, occurrence preservation, parser line ranges, schema initialization/migration, search limits, retrieval by ID, GRR deduplication, malformed input, and Windows/macOS/Linux path handling where practical.

## Before calling it production-ready
Inspect:
- real C examples;
- real GRR examples;
- repository and branch/tag/label conventions;
- permitted parser dependencies;
- specification access;
- representative index size and indexing time.

If information is missing, leave a clean adapter/TODO. Do not guess company-specific details.

Treat the attached starter as an architectural proposal. Improve or replace parts when the real environment shows a better design.
