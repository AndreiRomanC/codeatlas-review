from codeatlas.artifacts import extract_artifact_identifiers, extract_grl_definition


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


def test_nested_grl_definition_is_extracted_with_line_range():
    source = """header
online sample_value {
    sourceSection = sourceSectionRef {
        declFile = sourceSection MEM_DATA;
    }
    description = "brace } inside string";
}
tail
"""
    definition, start, end = extract_grl_definition(source, "sample_value")
    assert definition.startswith("online sample_value")
    assert "sourceSectionRef" in definition
    assert (start, end) == (2, 7)
