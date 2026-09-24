import re
from typing import List, Tuple


# Bootstrap extractor grounded in the observed AQ4 ERRM .grl/.grl2 declarations.
# This intentionally does not attempt to define or validate a complete GRL grammar.
_GRR_DECLARATION = re.compile(
    r"^\s*(parameter|online|cBase|cTag|cFile)\s+(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_.]*))",
    re.MULTILINE,
)


def extract_artifact_identifiers(kind: str, text: str, limit: int = 10_000) -> List[Tuple[str, str]]:
    if kind != "grr":
        return []
    found = set()
    for match in _GRR_DECLARATION.finditer(text):
        identifier = match.group(2) or match.group(3)
        found.add((identifier, match.group(1)))
        if len(found) >= limit:
            break
    return sorted(found)


def extract_grl_definition(text: str, identifier: str) -> Tuple[str, int, int]:
    """Return one GRL declaration block and its 1-based line range."""
    if not identifier or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", identifier):
        raise ValueError("identifier must be a GRL identifier")
    declaration = re.compile(
        rf'''(?m)^\s*(?:parameter|online|cBase|cTag|cFile)\s+['"]?{re.escape(identifier)}['"]?\s*\{{'''
    )
    match = declaration.search(text)
    if match is None:
        raise ValueError(f"GRL definition not found: {identifier}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    quote = None
    escaped = False
    in_line_comment = False
    in_block_comment = False
    for index in range(opening, len(text)):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            continue
        if char in "'\"":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                return text[match.start():end].strip(), text.count("\n", 0, match.start()) + 1, text.count("\n", 0, end) + 1
    raise ValueError(f"Unclosed GRL definition: {identifier}")

