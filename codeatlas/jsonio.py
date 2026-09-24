import json
import sys
from typing import Any, Callable, Dict

from .errors import CodeAtlasError


def emit(payload: Dict[str, Any], *, stream: Any = sys.stdout, pretty: bool = False) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, ensure_ascii=False, sort_keys=True), file=stream)


def run_cli(action: Callable[[], Dict[str, Any]]) -> int:
    try:
        payload = action()
        emit({"ok": True, **payload})
        return 0
    except CodeAtlasError as exc:
        emit({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, stream=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        emit({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, stream=sys.stderr)
        return 2

