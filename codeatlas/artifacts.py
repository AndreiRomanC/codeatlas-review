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

