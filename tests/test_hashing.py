from codeatlas.hashing import normalize_text, sha256_text


def test_hash_is_stable_across_line_endings_and_trailing_whitespace():
    left = "int f(void) {\r\n    return 1;   \r\n}\r\n"
    right = "int f(void) {\n    return 1;\n}\n"
    assert normalize_text(left) == normalize_text(right)
    assert sha256_text(left) == sha256_text(right)


def test_hash_preserves_semantic_text_changes():
    assert sha256_text("return 1;") != sha256_text("return 2;")

