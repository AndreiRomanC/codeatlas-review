import re
from typing import Any, Dict, List

from .config import CodeAtlasConfig
from .errors import CodeAtlasError
from .hashing import decode_text
from .paths import iter_index_files
from .repository import prepare_module, source_revision


MAX_SOURCE_RESULTS = 50


def search_source(
    config: CodeAtlasConfig,
    module: str,
    query: str,
    *,
    regex: bool = False,
    ignore_case: bool = False,
    context: int = 2,
    limit: int = 20,
    refresh: bool = False,
) -> Dict[str, Any]:
    if not query:
        raise CodeAtlasError("query must not be empty")
    if not 0 <= context <= 20:
        raise CodeAtlasError("context must be between 0 and 20")
    if not 1 <= limit <= MAX_SOURCE_RESULTS:
        raise CodeAtlasError(f"limit must be between 1 and {MAX_SOURCE_RESULTS}")
    flags = re.IGNORECASE if ignore_case else 0
    try:
        pattern = re.compile(query if regex else re.escape(query), flags)
    except re.error as exc:
        raise CodeAtlasError(f"invalid regular expression: {exc}") from exc

    prepare_module(config, module, update=refresh)
    results: List[Dict[str, Any]] = []
    truncated = False
    for repository in config.repositories_for_module(module):
        for revision in repository.revisions:
            source = source_revision(config, repository, revision)
            for relative, path in iter_index_files(source.root, config.index.include, config.index.exclude):
                if path.suffix.lower() not in {".c", ".h", ".grl", ".grl2"}:
                    continue
                if path.stat().st_size > config.index.max_file_bytes:
                    continue
                text, _encoding = decode_text(path.read_bytes())
                lines = text.splitlines()
                for line_number, line in enumerate(lines, 1):
                    if not pattern.search(line):
                        continue
                    if len(results) >= limit:
                        truncated = True
                        break
                    start = max(1, line_number - context)
                    end = min(len(lines), line_number + context)
                    results.append(
                        {
                            "repository": repository.name,
                            "module": repository.module,
                            "revision": source.revision_name,
                            "resolved_commit": source.resolved_commit,
                            "path": relative,
                            "line": line_number,
                            "context_start": start,
                            "context_end": end,
                            "context": [
                                {"line": number, "text": lines[number - 1]}
                                for number in range(start, end + 1)
                            ],
                        }
                    )
                if truncated:
                    break
            if truncated:
                break
        if truncated:
            break
    return {
        "module": module,
        "query": query,
        "regex": regex,
        "ignore_case": ignore_case,
        "count": len(results),
        "limit": limit,
        "truncated": truncated,
        "results": results,
    }
