from codeatlas.c_parser import extract_functions


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


def test_malformed_input_does_not_invent_functions():
    assert extract_functions(b"this is not a C function {\n") == []

