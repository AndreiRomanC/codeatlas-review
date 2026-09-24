# CodeAtlas command routing

The launcher locates the standalone CodeAtlas repository through `CODEATLAS_HOME` or an ancestor containing `pyproject.toml` and `codeatlas/`.

```text
python .github/skills/codeatlas-review/scripts/codeatlas.py COMMAND [arguments]
```

| Intent | Command | Primary output |
|---|---|---|
| Resolve runtime | `doctor --json` | selected interpreter and dependency checks |
| Inspect available refs | `list-revisions --module M --config C [--refresh]` | actual branches/tags and object IDs |
| Prepare repositories | `fetch --module M --config C` | mirror/fetch status |
| Check freshness | `status --module M --config C --summary` | stale/indexed status |
| Build index | `index --module M --config C --summary` | bounded indexing summary |
| Retrieve specification | `spec --module M --config C` | content and provenance |
| Find candidates | `find --db D ...` | compact occurrence metadata, never bodies |
| Group exact variants | `implementations --db D --name F` | unique hashes and all occurrences |
| Rank similar code | `similar --db D --id ID` or `similar --db D --source FILE --function F` | token-shingle similarity candidates |
| Retrieve one entity | `get --db D --id ID` | exact body and occurrences |
| Search bounded source context | `source-search --module M --config C --query Q` | small contextual matches with provenance |
| Extract GRL definitions | `grl --db D --identifier I` | matching blocks and provenance |
| Rank GRL identifiers | `rank-grl --db D` | revision/repository coverage |

Use small limits first. Full content belongs only in `get` or explicitly requested GRL extraction.
