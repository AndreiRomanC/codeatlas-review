---
name: codeatlas-review
description: Review automotive C and GRL implementations against an applicable specification using deterministic indexed evidence. Use for module, function, configuration, cross-project implementation, similarity, and implementation-drift reviews.
---

# CodeAtlas Review

The applicable specification is authoritative. Historical implementations are supporting evidence, never a substitute for requirements.

## Operating contract

Use CodeAtlas scripts before manual repository searches whenever they can answer the question. Scripts establish locations, identity, similarity, occurrences, and configuration facts. Use model reasoning for specification interpretation, semantic differences, risks, and review findings.

Never load an entire repository or database into context. Search compact metadata first and retrieve only selected IDs.

## Route the task

1. Run `doctor` to resolve a compatible Python interpreter and verify dependencies.
2. For repository preparation, run `list-revisions`, `fetch`, `status`, and `index` as needed. Do not modify source repositories.
3. Retrieve the specification before claiming compliance.
4. Use `find` for compact candidates, `implementations` for exact variants grouped by hash, and `similar` for deterministic token-based ranking.
5. Use `source-search` for bounded symbol/context lookup instead of repeated ad-hoc shell searches.
6. Use `get` only for the few references selected for semantic analysis.
7. Use `grl` or `rank-grl` for configuration evidence.

Run commands through [codeatlas.py](./scripts/codeatlas.py). Read [commands.md](./references/commands.md) only when command options or result semantics are needed. Read the repository's `references/review-workflow.md` before producing a formal review.

## Invariants

- Exact SHA-256 means identity; token-shingle similarity is only a ranking signal.
- Preserve repository, revision, commit, path, and line provenance.
- If specification retrieval fails, report the limitation and do not label findings as specification violations.
- Do not reset, clean, commit, push, or checkout in a configured source repository.
- If a repeatable deterministic query is missing, improve CodeAtlas rather than repeatedly recreating it with shell searches.
- Stop and report missing access, credentials, ambiguous specification revisions, or unsupported database migrations.
