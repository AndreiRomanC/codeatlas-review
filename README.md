# CodeAtlas Review

CodeAtlas Review is a reusable AI Agent Skill for spec-grounded automotive software review. It builds a deterministic SQLite index over configured reference sources and gives the reviewing agent only a compact candidate catalog followed by explicitly selected content.

The specification is authoritative; historical/reference code is evidence only.

Data lookups should use the Python CLIs directly. They return deterministic results
without requiring semantic analysis.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

CodeAtlas supports Python 3.9+. Resolve an existing compatible interpreter before repository operations:

```bash
python scripts/doctor.py --json
python scripts/doctor.py --resolve
```

The resolver prefers `CODEATLAS_PYTHON`, an AURA or project venv, approved Windows
installations, and finally compatible PATH interpreters. Use its selected executable
for all commands; Python 3.6 is unsupported.

Copy `config.example.yaml` to a local ignored configuration and supply repository locations. The current workspace uses `config.local.yaml` for the AQ4 ERRM corpus.

```bash
.venv/bin/python scripts/fetch_repos.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/build_index.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/index_status.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/get_specification.py --config config.local.yaml --module errm_selct_emivar
.venv/bin/python scripts/find_references.py --db .codeatlas/aq4-errm.db --kind function --name NAME --limit 10
.venv/bin/python scripts/get_reference.py --db .codeatlas/aq4-errm.db --id ID
.venv/bin/python scripts/find_similar_functions.py --db .codeatlas/aq4-errm.db --id ID --min-score 0.80 --limit 10
.venv/bin/python scripts/find_similar_functions.py --db .codeatlas/aq4-errm.db --source target.c --function NAME --limit 10
.venv/bin/python scripts/list_implementations.py --db .codeatlas/aq4-errm.db --name NAME
.venv/bin/python scripts/search_source.py --module ERRM --config config.local.yaml --query SYMBOL --limit 10
.venv/bin/python scripts/list_revisions.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/extract_grl.py --db .codeatlas/aq4-errm.db --identifier IDENTIFIER --limit 50
.venv/bin/python scripts/extract_grl.py --db .codeatlas/aq4-errm.db --identifier IDENTIFIER --format text --limit 50
.venv/bin/python scripts/rank_grl.py --db .codeatlas/aq4-errm.db --limit 20
```

All command output is JSON. Candidate queries accept at most 50 results, and exact retrieval has a bounded content size.

For low-context operation, append `--summary` to `index_status.py` and `build_index.py`.
The default JSON is compact; use full output only to diagnose a specific revision.

The first preparation run creates a local mirror and snapshots under `.codeatlas/`.
It never pushes or changes the configured source repository. Configure actual branch
or tag names from the repository; `main` is not assumed. Include patterns are relative
to each snapshot root, so inspect an external repository before narrowing them to a
project-specific path.

Similarity search uses normalized C token shingles and deterministic Jaccard scoring. It is a reference-selection aid only; the applicable specification remains authoritative.

GitHub Copilot discovers the project skill at `.github/skills/codeatlas-review/SKILL.md`.
The Copilot layer remains thin; the reusable Python package, database, and tests stay independent.

## Validation

```bash
CODEATLAS_ERRM_ROOT=/path/to/aq4/data/errm .venv/bin/pytest
```
