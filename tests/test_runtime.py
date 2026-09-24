import os
import sys
from pathlib import Path

from codeatlas import runtime


def test_runtime_resolver_selects_compatible_ready_interpreter(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "interpreter_candidates",
        lambda _root: [(0, "test", Path(sys.executable))],
    )
    result = runtime.resolve_python(tmp_path)
    assert os.path.samefile(result["selected"]["executable"], sys.executable)
    assert result["dependencies_ready"] is True
