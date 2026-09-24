from codeatlas.c_parser import extract_functions
from codeatlas.similarity import SIMILARITY_METHOD, fingerprint_similarity


def test_parser_extracts_function_boundaries_and_signature():
    source = b"""#include <example.h>\r
#define MEM_CODE MEM_CODE_10MS\r
static unsigned first(void)\r
{\r
    return 1U;\r
}\r
\r
void second(int value) {\r
    (void)value;\r
}\r
"""
    functions = extract_functions(source)
    assert [item.name for item in functions] == ["first", "second"]
    assert functions[0].signature == "static unsigned first(void)"
    assert (functions[0].start_line, functions[0].end_line) == (3, 6)
    assert (functions[1].start_line, functions[1].end_line) == (8, 10)
    assert functions[0].similarity_method == SIMILARITY_METHOD
    assert functions[0].token_count > 0
    assert functions[0].similarity_fingerprint.startswith("[")


def test_malformed_input_does_not_invent_functions():
    assert extract_functions(b"this is not a C function {\n") == []


def test_token_similarity_ranks_nearby_code_above_unrelated_code():
    nearby_a = extract_functions(
        b"int sample(int value) { if (value > 0) { return value + 1; } return 0; }"
    )[0]
    nearby_b = extract_functions(
        b"int renamed(int input) { if (input > 7) { return input + 2; } return 0; }"
    )[0]
    unrelated = extract_functions(
        b"void reset(void) { for (;;) { service_watchdog(); } }"
    )[0]
    high = fingerprint_similarity(
        nearby_a.similarity_fingerprint, nearby_b.similarity_fingerprint
    )
    low = fingerprint_similarity(
        nearby_a.similarity_fingerprint, unrelated.similarity_fingerprint
    )
    assert high >= 0.8
    assert low < high
