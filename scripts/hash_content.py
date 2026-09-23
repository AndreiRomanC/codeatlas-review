"""Compatibility wrapper for the reusable hashing implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codeatlas.hashing import normalize_text as normalize  # noqa: E402
from codeatlas.hashing import sha256_text  # noqa: E402,F401


__all__ = ["normalize", "sha256_text"]
