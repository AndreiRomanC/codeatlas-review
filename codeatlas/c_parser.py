from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterator, List, Optional

from .errors import ParserUnavailableError
from .hashing import decode_text, normalized_text_and_hash
from .similarity import SIMILARITY_METHOD, fingerprint_function


@dataclass(frozen=True)
class CFunction:
    name: str
    signature: str
    content: str
    normalized_content: str
    normalized_hash: str
    similarity_method: str
    similarity_fingerprint: str
    token_count: int
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    parse_has_error: bool


@lru_cache(maxsize=1)
def _parser() -> Any:
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_c
    except ImportError as exc:
        raise ParserUnavailableError(
            "tree-sitter and tree-sitter-c are required for deterministic C parsing"
        ) from exc
    language = Language(tree_sitter_c.language())
    return Parser(language)


def _walk(node: Any) -> Iterator[Any]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _identifier_from_declarator(node: Any, source: bytes) -> Optional[str]:
    current = node
    while current is not None:
        if current.type in {"identifier", "field_identifier"}:
            return source[current.start_byte:current.end_byte].decode("utf-8", errors="replace")
        nested = current.child_by_field_name("declarator")
        if nested is None:
            break
        current = nested
    for descendant in _walk(node):
        if descendant.type == "identifier":
            return source[descendant.start_byte:descendant.end_byte].decode("utf-8", errors="replace")
    return None


def extract_functions(data: bytes) -> List[CFunction]:
    text, _encoding = decode_text(data)
    source = text.encode("utf-8")
    tree = _parser().parse(source)
    functions: List[CFunction] = []
    for node in _walk(tree.root_node):
        if node.type != "function_definition":
            continue
        if node.has_error:
            continue
        declarator = node.child_by_field_name("declarator")
        body = node.child_by_field_name("body")
        if declarator is None or body is None:
            continue
        name = _identifier_from_declarator(declarator, source)
        if not name:
            continue
        signature = source[node.start_byte:body.start_byte].decode("utf-8", errors="replace").strip()
        content = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        normalized, digest = normalized_text_and_hash(content)
        similarity_fingerprint, token_count = fingerprint_function(node, source)
        functions.append(
            CFunction(
                name=name,
                signature=signature,
                content=content,
                normalized_content=normalized,
                normalized_hash=digest,
                similarity_method=SIMILARITY_METHOD,
                similarity_fingerprint=similarity_fingerprint,
                token_count=token_count,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                parse_has_error=node.has_error,
            )
        )
    return functions
