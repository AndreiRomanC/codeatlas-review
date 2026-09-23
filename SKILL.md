---
name: codeatlas-review
description: Review automotive C code and GRR/configuration artifacts against an applicable specification, using a compact indexed catalog of historical implementations only as supporting evidence. Use for module, file, function, configuration, and implementation-drift reviews; do not use reference consensus as a substitute for a specification.
---

# CodeAtlas Review

The applicable specification is authoritative. Historical implementations may be wrong, old, or variant-specific. Agreement among references is evidence of a pattern, not evidence of correctness.

Use scripts for repository access, parsing, hashing, indexing, search, and exact retrieval. Use agent reasoning for scope selection, specification interpretation, semantic comparison, and findings. Never load a complete repository into context.

## Workflow

1. Resolve the target module, file, function or artifact and the intended revision.
2. Retrieve the applicable specification. If the provider is unavailable, say so explicitly and do not claim specification compliance.
3. Check index status. Fetch configured references and refresh only stale data when authorized by the request.
4. Search for a compact catalog. Start with a narrow query and a small limit.
5. Select normally 2–4 useful IDs based on provenance, variant, revision, and hash differences.
6. Retrieve only those IDs. Request additional dependencies only when the review requires them.
7. Compare the target with the specification first. Use references only for patterns, missing handling, edge cases, and drift.
8. Preserve repository, revision, file, entity, and line provenance for every reference observation.

For command details and configuration, read [references/configuration.md](references/configuration.md) only when preparing or refreshing the index. For the required review reasoning and report structure, read [references/review-workflow.md](references/review-workflow.md) when performing a review.

Do not reset, clean, commit, push, or otherwise modify reference repositories. Do not invent specification content, GRR grammar, repository locations, credentials, or internal APIs.
