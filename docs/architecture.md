# Architecture

Target -> specification adapter -> compact CodeAtlas search -> selected retrieval -> spec-grounded review.

## Deterministic layer

- Configured local repositories are read without mutation.
- Remote Git references are fetched into CodeAtlas-owned bare mirrors and materialized as immutable commit snapshots.
- Tree-sitter C extracts function boundaries, signatures, source ranges, and bodies without requiring a complete compiler environment.
- Normalized C token shingles provide a reusable similarity fingerprint; Jaccard scores are calculated only for requested candidates and are never stored pairwise.
- Conservative normalization changes line endings and trailing whitespace only.
- SQLite stores repositories, revisions, files, entities, occurrences, identifiers, index runs, and errors.
- Incremental refresh uses revision identity, file hashes, and an index version.

Content blobs are separate from entity metadata. Identical normalized functions or identical artifacts share stored content while every occurrence keeps repository, revision, path, and line provenance.

## Artifact layer

AQ4 ERRM contains `.grl` and `.grl2` artifacts. V1 indexes them at file level and extracts only declaration forms observed in those files. This is a bootstrap identifier extractor, not a claimed GRR/GRL grammar. Other formats can be added through configuration after representative examples are inspected.

## Reasoning layer

The agent requests a small catalog, chooses a few references, retrieves exact content, and compares the target against the specification first. Call/use/reference graphs remain out of V1 until a demonstrated review need justifies them.

## Specification adapters

The current `folder_txt` provider resolves a module to its configured `d` directory and reads bounded `.txt` specifications. It deduplicates identical documents, preserves every source path, and refuses to choose among distinct documents without an explicit filename. Plain files cannot independently prove a requested revision, so that limitation remains visible in provenance.

When `folder_txt` is configured with `repository` and `revision`, it resolves the specification from the same immutable snapshot used by the index and records the resolved commit. Explicit filesystem roots remain available for specifications maintained outside a configured repository.

LIMAS remains a future provider behind the same interface; adding it must not change the review or indexing layers.
