import hashlib
import json
from typing import Any, Iterable, List, Sequence, Set, Tuple


SIMILARITY_METHOD = "c-token-shingles-v1"
SHINGLE_SIZE = 5

_IDENTIFIER_TYPES = {
    "identifier",
    "field_identifier",
    "statement_identifier",
    "type_identifier",
}
_LITERAL_TYPES = {
    "char_literal": "CHAR",
    "concatenated_string": "STRING",
    "number_literal": "NUMBER",
    "string_literal": "STRING",
    "system_lib_string": "STRING",
}


def _walk_leaves(node: Any) -> Iterable[Any]:
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "comment":
            continue
        if current.child_count == 0:
            yield current
        else:
            stack.extend(reversed(current.children))


def normalized_c_tokens(node: Any, source: bytes) -> List[str]:
    """Return conservative lexical tokens suitable for similarity, not identity."""
    tokens: List[str] = []
    for leaf in _walk_leaves(node):
        if leaf.type in _IDENTIFIER_TYPES:
            tokens.append("IDENTIFIER")
            continue
        replacement = _LITERAL_TYPES.get(leaf.type)
        if replacement is not None:
            tokens.append(replacement)
            continue
        value = source[leaf.start_byte:leaf.end_byte].decode("utf-8", errors="replace").strip()
        if value:
            tokens.append(leaf.type if leaf.type == value else f"{leaf.type}:{value}")
    return tokens


def _digest_shingle(tokens: Sequence[str]) -> str:
    payload = "\x1f".join(tokens).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def fingerprint_tokens(tokens: Sequence[str], shingle_size: int = SHINGLE_SIZE) -> Tuple[str, int]:
    if shingle_size < 1:
        raise ValueError("shingle_size must be positive")
    if not tokens:
        return "[]", 0
    if len(tokens) < shingle_size:
        shingles = {_digest_shingle(tokens)}
    else:
        shingles = {
            _digest_shingle(tokens[index:index + shingle_size])
            for index in range(len(tokens) - shingle_size + 1)
        }
    return json.dumps(sorted(shingles), separators=(",", ":")), len(tokens)


def fingerprint_function(node: Any, source: bytes) -> Tuple[str, int]:
    return fingerprint_tokens(normalized_c_tokens(node, source))


def decode_fingerprint(value: str) -> Set[str]:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid similarity fingerprint") from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise ValueError("invalid similarity fingerprint")
    return set(decoded)


def fingerprint_similarity(left: str, right: str) -> float:
    left_set = decode_fingerprint(left)
    right_set = decode_fingerprint(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)
