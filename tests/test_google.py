from docparse import Paragraphs, get_docstring
from docparse.google import parse_google_docstring
from . import google_style


def test_functions():
    docs = parse_google_docstring(
        get_docstring(google_style.function_with_types_in_docstring)
    )
    assert docs.summary == "Example function with types documented in the docstring."
    assert tuple(docs.description.paragraphs) == (
        "Example function with types documented in the docstring.",
        "`PEP 484`_ type annotations are supported. If attribute, parameter, and "
        "return types are annotated according to `PEP 484`_, they do not need to be "
        "included in the docstring:"
    )
    assert len(docs.parameters) == 2
    assert "param1" in docs.parameters
    param1 = docs.parameters["param1"]
    assert param1.name == "param1"
    assert param1.datatype == "int"
    assert str(param1.description) == "The first parameter."
    assert "param2" in docs.parameters
    param2 = docs.parameters["param2"]
    assert param2.datatype == "str"
    assert str(param2.description) == "The second parameter."
    returns = docs.returns
    assert returns.datatype == "bool"
    assert str(returns.description) == \
        "The return value. True for success, False otherwise."
    assert docs.directives == {
        "_PEP 484": Paragraphs(["https://www.python.org/dev/peps/pep-0484/"])
    }
