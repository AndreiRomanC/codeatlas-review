# CodeAtlas Review

CodeAtlas Review is a reusable AI Agent Skill for spec-grounded automotive software review. It builds a deterministic SQLite index over configured reference sources and gives the reviewing agent only a compact candidate catalog followed by explicitly selected content.

The specification is authoritative; historical/reference code is evidence only.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Copy `config.example.yaml` to a local ignored configuration and supply repository locations. The current workspace uses `config.local.yaml` for the AQ4 ERRM corpus.

```bash
.venv/bin/python scripts/fetch_repos.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/build_index.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/index_status.py --module ERRM --config config.local.yaml
.venv/bin/python scripts/get_specification.py --config config.local.yaml --module errm_selct_emivar
.venv/bin/python scripts/find_references.py --db .codeatlas/aq4-errm.db --kind function --name NAME --limit 10
.venv/bin/python scripts/get_reference.py --db .codeatlas/aq4-errm.db --id ID
```

All command output is JSON. Candidate queries accept at most 50 results, and exact retrieval has a bounded content size.

## Validation

```bash
CODEATLAS_ERRM_ROOT=/path/to/aq4/data/errm .venv/bin/pytest
```
