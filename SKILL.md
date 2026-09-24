---
name: codeatlas-review
description: Review automotive C code and GRR/configuration artifacts against an applicable specification, using a compact indexed catalog of historical implementations only as supporting evidence. Use for module, file, function, configuration, and implementation-drift reviews; do not use reference consensus as a substitute for a specification.
---

# CodeAtlas Review

The applicable specification is authoritative. Historical implementations may be wrong, old, or variant-specific. Agreement among references is evidence of a pattern, not evidence of correctness.

Use scripts for repository access, parsing, hashing, indexing, search, and exact retrieval. Use agent reasoning for scope selection, specification interpretation, semantic comparison, and findings. Never load a complete repository into context.

When the user asks to find data, run the relevant Python CLI directly and return its
machine-readable or requested text output. Do not replace a data query with manual SQL,
manual repository browsing, or semantic analysis unless explicitly requested.

## Workflow

1. Resolve the target module, file, function or artifact and the intended revision.
2. Retrieve the applicable specification. If the provider is unavailable, say so explicitly and do not claim specification compliance.
3. Prepare the configured repositories. For an external Git URL, clone a local mirror and inspect available refs before choosing revisions. Never push, commit, reset, clean, or checkout in the source repository.
4. Check index status. Refresh only stale data when authorized by the request.
5. Build the index one configured revision at a time. Use immutable snapshots; empty branches may be recorded but must be reported as empty.
6. Search for a compact catalog. Start with a narrow query and a small limit.
7. When useful, find token-similar functions with `find_similar_functions.py`; use the result for candidate selection, not as proof of semantic equivalence.
8. Select normally 2–4 useful IDs based on provenance, variant, revision, exact hash, and similarity score.
9. Retrieve only those IDs. Request additional dependencies only when the review requires them.
10. Compare the target with the specification first. Use references only for patterns, missing handling, edge cases, and drift.
11. Fetch more context only on demand.

For a requested GRL identifier, run `extract_grl.py` and return its complete definitions
grouped by revision. Use `--all-revisions --format text` for full branch coverage. Do not infer missing
definitions or analyze them unless asked.

To list exact implementation variants and all occurrences, run `list_implementations.py`.
To find bounded source context, run `search_source.py` instead of repeated ad-hoc shell searches.
To find the most common GRL data, run `rank_grl.py`; it ranks identifiers by the number
of indexed revisions before any definition extraction.

## Preparation checklist

- Do not install Python automatically. Run any available Python 3.9+ with `scripts/doctor.py`; it prefers `CODEATLAS_PYTHON`, the AURA/project venv, approved Windows installations, then compatible PATH interpreters.
- Use the interpreter reported by `doctor.py --resolve` consistently. It checks Git, PyYAML, Tree-sitter, and Tree-sitter C before repository operations.
- Keep the database, mirrors, and snapshots below `.codeatlas/`; these are local working data and are not source-repository changes.
- For a local source tree use `local_path` and `WORKTREE`. For an external repository use `url`; do not mix the two.
- Discover branch and tag names with `list_revisions.py`. Do not assume `main`; automotive repositories often use variant-specific refs.
- Configure every requested branch or tag explicitly. The indexer stores each ref as a separate revision and preserves its commit provenance.
- Set include globs relative to the snapshot root. Do not copy a path from a different project; inspect the external repository layout first. A dedicated module repository often needs `**/*.c`, `**/*.h`, and `**/*.grl`.
- Run `fetch_repos.py`, then `index_status.py`, then `build_index.py`, and finish with `index_status.py`. Use `--force` only after a parser or schema change.
- Use `--summary` for routine multi-branch runs; request full per-revision JSON only when diagnosing a failure.
- Snapshot extraction uses `git archive` without a shell and must never checkout into or alter the source repository.

## Similarity search

Exact SHA-256 hashes identify identical normalized implementations. They do not measure
closeness. For candidate discovery, the index stores a deterministic normalized-token
shingle fingerprint. The `find_similar_functions.py` command calculates Jaccard similarity
and accepts either an indexed ID or a function from a current source file.

Use similarity scores only to select references for inspection. A high score is not a
specification result and does not establish semantic equivalence or correctness.

For command details and configuration, read [references/configuration.md](references/configuration.md) only when preparing or refreshing the index. For the required review reasoning and report structure, read [references/review-workflow.md](references/review-workflow.md) when performing a review.

Do not reset, clean, commit, push, or otherwise modify reference repositories. Do not invent specification content, GRR grammar, repository locations, credentials, or internal APIs.
