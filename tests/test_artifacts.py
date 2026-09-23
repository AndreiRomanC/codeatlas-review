from codeatlas.artifacts import extract_artifact_identifiers


def test_observed_grl_declarations_are_extracted_conservatively():
    source = """
    cFile 'module_data.c' {
    }
    parameter c_limit_max {
    }
    cTag STRUCT_NAME {
    }
    """
    assert extract_artifact_identifiers("grr", source) == [
        ("STRUCT_NAME", "cTag"),
        ("c_limit_max", "parameter"),
        ("module_data.c", "cFile"),
    ]
    assert extract_artifact_identifiers("unknown", source) == []

