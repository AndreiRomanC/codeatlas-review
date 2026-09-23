import os
from pathlib import Path

import pytest

from codeatlas.c_parser import extract_functions


def test_representative_real_errm_file_when_available():
    root_value = os.environ.get("CODEATLAS_ERRM_ROOT")
    if not root_value:
        pytest.skip("CODEATLAS_ERRM_ROOT is not configured")
    source = Path(root_value) / "agf" / "errm_dcmng" / "i" / "errm_dcmng.c"
    functions = extract_functions(source.read_bytes())
    names = {item.name for item in functions}
    assert "errm_dcmng_std_den_ind" in names
    assert all(item.start_line <= item.end_line for item in functions)
    assert len(functions) >= 10

