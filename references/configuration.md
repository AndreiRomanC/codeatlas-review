# Configuration and commands

Read this reference only when preparing repositories, building the index, checking freshness, or troubleshooting deterministic retrieval.

For data requests, use the Python command first: `find_references.py` for catalog
metadata, `get_reference.py` for an indexed entity, and `extract_grl.py` for complete
GRL definitions. Return the command result directly; use SQL or analysis only for an
explicitly requested diagnostic.

## Reliable preparation sequence

Use an existing Python 3.9+ environment. Resolve it deterministically and do not
install Python automatically.

```bash
python scripts/doctor.py --json
CODEATLAS_PYTHON="$(python scripts/doctor.py --resolve)"
"$CODEATLAS_PYTHON" scripts/fetch_repos.py --module MODULE --config CONFIG
"$CODEATLAS_PYTHON" scripts/index_status.py --module MODULE --config CONFIG
"$CODEATLAS_PYTHON" scripts/build_index.py --module MODULE --config CONFIG
"$CODEATLAS_PYTHON" scripts/index_status.py --module MODULE --config CONFIG
```

For routine multi-branch runs, append `--summary` to the index and status commands.
The default JSON is compact; detailed per-revision output is for diagnosis only.

On Windows, `doctor.py` also inspects the `py` launcher and `C:\LegacyApp\`.
Use the same selected executable for installation and all commands.

The first command creates or updates only the CodeAtlas-owned mirror. It must not
perform a push or change the source repository. If a repository has no `main` ref,
inspect the mirror's actual branch/tag names and configure those names explicitly.
Do not assume that a successful clone means the selected ref contains files; an
empty branch is valid Git data and should be reported as empty.

## Configuration

Start from `config.example.yaml`. Repository information belongs in configuration, never in Python code. A repository defines one `module`, exactly one `local_path` or `url`, and one or more revisions.

- Use `ref: WORKTREE` only for a local directory whose current files should be indexed.
- A Git ref is resolved to a commit and indexed from a CodeAtlas-owned immutable snapshot.
- HTTP URLs containing embedded usernames or passwords are rejected. Authentication must already be available in the environment.
- `artifact_kinds` maps generic entity kinds to file suffixes. The default `grr` mapping covers the observed `.grl` and `.grl2` files.
- Paths relative to the configuration file are resolved from that file's directory.
- Include/exclude patterns are matched relative to each immutable snapshot root, not
	relative to the original local project. Inspect the repository tree before choosing
	the patterns.

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
python scripts/list_implementations.py --db DATABASE --name NAME --limit 20
python scripts/find_similar_functions.py --db DATABASE --id ID --limit 10
python scripts/find_similar_functions.py --db DATABASE --source TARGET.c --function NAME --limit 10
python scripts/search_source.py --module MODULE --config CONFIG --query SYMBOL --limit 10
python scripts/find_references.py --db DATABASE --kind grr --identifier IDENTIFIER --limit 10
python scripts/get_reference.py --db DATABASE --id ID
python scripts/extract_grl.py --db DATABASE --identifier IDENTIFIER --limit 50
python scripts/extract_grl.py --db DATABASE --identifier IDENTIFIER --format text --limit 50
python scripts/extract_grl.py --db DATABASE --identifier IDENTIFIER --all-revisions --format text
python scripts/rank_grl.py --db DATABASE --limit 20
```

`extract_grl.py` returns only matching GRL blocks with repository, revision, commit,
path, line range, and the complete nested block. Use `--format text` for readable
output or the default JSON for automation. A zero-result response means the identifier was not indexed;
do not invent definitions for other revisions.

Search supports module, repository, revision, hash prefix, exact name, and literal name containment. Limits must be between 1 and 50. Retrieval rejects oversized content unless the caller explicitly raises `--max-bytes` within the absolute safety bound.

Specification retrieval is an adapter boundary. The temporary `folder_txt` provider searches configured roots using a safe pattern such as `agf/{module}/d`, reads only `.txt` files, and preserves path, encoding, size, and SHA-256 provenance:

```bash
python scripts/get_specification.py --config CONFIG --module MODULE --feature FEATURE --revision REVISION
```

Identical files are deduplicated while all source paths are preserved. If a module contains distinct documents, the provider returns an ambiguity instead of choosing one; repeat the command with `--document FILENAME`. A requested revision is recorded but marked unverified because a plain text file has no authoritative revision API.

The unconfigured provider returns an explicit unavailable result. The future LIMAS provider will implement the same adapter contract, so the review workflow does not need to change. Do not infer a LIMAS API from nearby files or legacy tooling.
