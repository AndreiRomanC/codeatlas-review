# Configuration and commands

Read this reference only when preparing repositories, building the index, checking freshness, or troubleshooting deterministic retrieval.

## Configuration

Start from `config.example.yaml`. Repository information belongs in configuration, never in Python code. A repository defines one `module`, exactly one `local_path` or `url`, and one or more revisions.

- Use `ref: WORKTREE` only for a local directory whose current files should be indexed.
- A Git ref is resolved to a commit and indexed from a CodeAtlas-owned immutable snapshot.
- HTTP URLs containing embedded usernames or passwords are rejected. Authentication must already be available in the environment.
- `artifact_kinds` maps generic entity kinds to file suffixes. The default `grr` mapping covers the observed `.grl` and `.grl2` files.
- Paths relative to the configuration file are resolved from that file's directory.

## Commands

Prepare references without changing local repositories:

```bash
python scripts/fetch_repos.py --module MODULE --config CONFIG
```

Check freshness, then build or incrementally refresh:

```bash
python scripts/index_status.py --module MODULE --config CONFIG
python scripts/build_index.py --module MODULE --config CONFIG
```

Use `--force` only for an intentional full reparse. It does not reset or clean reference repositories.

Search compact metadata before retrieving content:

```bash
python scripts/find_references.py --db DATABASE --kind function --name NAME --limit 10
python scripts/find_references.py --db DATABASE --kind grr --identifier IDENTIFIER --limit 10
python scripts/get_reference.py --db DATABASE --id ID
```

Search supports module, repository, revision, hash prefix, exact name, and literal name containment. Limits must be between 1 and 50. Retrieval rejects oversized content unless the caller explicitly raises `--max-bytes` within the absolute safety bound.

Specification retrieval is an adapter boundary. The temporary `folder_txt` provider searches configured roots using a safe pattern such as `agf/{module}/d`, reads only `.txt` files, and preserves path, encoding, size, and SHA-256 provenance:

```bash
python scripts/get_specification.py --config CONFIG --module MODULE --feature FEATURE --revision REVISION
```

Identical files are deduplicated while all source paths are preserved. If a module contains distinct documents, the provider returns an ambiguity instead of choosing one; repeat the command with `--document FILENAME`. A requested revision is recorded but marked unverified because a plain text file has no authoritative revision API.

The unconfigured provider returns an explicit unavailable result. The future LIMAS provider will implement the same adapter contract, so the review workflow does not need to change. Do not infer a LIMAS API from nearby files or legacy tooling.
