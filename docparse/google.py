"""Google-style docstring parser. Code adapted from Napoleon:
https://github.com/sphinx-contrib/napoleon/blob/master/sphinxcontrib/napoleon/docstring.py
"""
from functools import partial
import re
from typing import Tuple, Dict, Sequence, Optional, cast

from docparse import DocString, DocStyle, Paragraphs, Typed, Field, parser


SECTION_RE = re.compile(r"^(\w[\w ]+):$")
DIRECTIVE_RE = re.compile(r"^.. ([\w ]+):$")
XREF_RE = re.compile(r"(:(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:`.+?`)")
SINGLE_COLON_RE = re.compile(r"(?<!:):(?!:)")
INDENT_RE = re.compile(r"^(\s*)(.*)$")
TYPED_PARAM_RE = re.compile(r"\s*(.+?)\s*\(\s*(.*[^\s]+)\s*\)")
KEYWORD_RE = re.compile(r"[^\w]")
NAME_RE = re.compile(
    r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`| (?P<name2>[a-zA-Z0-9_.-]+))\s*",
    re.X
)

SECTION_PARSERS = {}
ALIASES = {}


@parser(DocStyle.GOOGLE)
def parse_google_docstring(docstring, allow_directives=True) -> DocString:
    lines = docstring.splitlines()
    num_lines = len(lines)

    if num_lines == 0:
        return DocString()

    def check_section_header(_line) -> Tuple[Optional[str], bool]:
        match = SECTION_RE.match(_line)
        if match:
            name = match.group(1)
            if name in ALIASES:
                name = ALIASES[name]
            if name in SECTION_PARSERS:
                return name, False
        if allow_directives:
            match = DIRECTIVE_RE.match(_line)
            if match:
                return match.group(1), True
        return None, False

    def add_section(_name, _is_directive, _lines, _sections, _directives):
        if _is_directive:
            _directives[_name] = _parse_generic_section(_lines)
        else:
            parser_func = SECTION_PARSERS.get(_name, _parse_generic_section)
            _sections[KEYWORD_RE.sub("_", _name.lower())] = parser_func(_lines)

    sections = {}
    directives = {}
    cur_section = "Description"
    cur_directive = False
    cur_lines = []

    for line in lines:
        section, is_directive = check_section_header(line)
        if section:
            add_section(cur_section, cur_directive, cur_lines, sections, directives)
            cur_section = section
            cur_directive = is_directive
            cur_lines = []
        else:
            cur_lines.append(line)

    if cur_lines:
        add_section(cur_section, cur_directive, cur_lines, sections, directives)

    return DocString(directives=directives, **sections)


def add_aliases(name: str, *aliases: str):
    for alias in aliases:
        ALIASES[alias] = name


add_aliases("Examples", "Example")
add_aliases("Keyword Arguments", "Keyword Args")
add_aliases("Notes", "Note")
add_aliases("Parameters", "Args", "Arguments")
add_aliases("Returns", "Return")
add_aliases("Warning", "Warnings")
add_aliases("Yields", "Yield")


def section_parser(*sections: str):
    """Decorator that registers a function as a section paraser.
    """
    def decorator(f):
        for section in sections:
            if isinstance(section, str):
                SECTION_PARSERS[section] = f
            else:
                name, kwargs = cast(Tuple[str, dict], section)
                SECTION_PARSERS[name] = partial(f, **kwargs)
        return f

    return decorator


@section_parser(
    "Attention",
    "Caution",
    "Danger",
    "Error",
    "Hint",
    "Important",
    "Note",
    "References",
    "See also",
    "Tip",
    "Todo",
    "Warning"
)
def _parse_generic_section(lines: Sequence[str]) -> Paragraphs:
    """Combine lines and remove indents. Lines separated by blank lines are
    grouped into paragraphs.

    Args:
        lines: A sequence of line strings.

    Returns:
        A tuple of paragraph strings.
    """
    return Paragraphs.from_lines(tuple(line.strip() for line in lines))


@section_parser("Examples")
def _parse_verbatim_section(lines: Sequence[str]) -> Sequence[str]:
    return _dedent(lines)


@section_parser(
    ("Parameters", dict(parse_type=True)),
    ("Keyword Arguments", dict(parse_type=True)),
    ("Other Parameters", dict(parse_type=True)),
    "Methods",
    "Warns"
)
def _parse_fields_section(
    lines: Sequence[str], parse_type: bool = False, prefer_type=False
) -> Dict[str, Field]:
    cur_indent = None
    fields = []

    for line in lines:
        indent, line = INDENT_RE.match(line).groups()
        indent_size = len(indent)
        if line and (cur_indent is None or indent_size <= cur_indent):
            # New parameter
            cur_indent = indent_size
            before, colon, after = _partition_field_on_colon(line)
            field_type = None
            if parse_type:
                field_name, field_type = _parse_parameter_type(before)
            else:
                field_name = before
            if prefer_type and not field_type:
                field_type, field_name = field_name, field_type
            fields.append((
                _escape_args_and_kwargs(field_name),
                field_type,
                [after.lstrip()]
            ))
        elif fields:
            # Add additional lines to current parameter
            fields[-1][2].append(line.lstrip())
        else:
            raise ValueError(f"Unexpected line in Args block: {line}")

    return dict(
        (field[0], Field(field[0], field[1], Paragraphs.from_lines(field[2])))
        for field in fields
    )


@section_parser(
    "Returns",
    "Yields"
)
def _parse_returns_section(lines: Sequence[str]) -> Typed:
    before, colon, after = _partition_field_on_colon(lines[0])
    return_type = None
    if colon:
        if after:
            return_desc = [after] + list(lines[1:])
        else:
            return_desc = lines[1:]
        return_type = before
    else:
        return_desc = lines

    return Typed(return_type, Paragraphs.from_lines(return_desc))


@section_parser("Raises")
def _parse_raises_section(lines: Sequence[str]) -> Dict[str, Field]:
    fields = _parse_fields_section(lines, prefer_type=True)
    for field in fields.values():
        match = NAME_RE.match(field.datatype).groupdict()
        if match["role"]:
            field.datatype = match["name"]
    return fields


def _partition_field_on_colon(line: str) -> Tuple[str, str, str]:
    before_colon = []
    after_colon = []
    colon = ""
    found_colon = False

    for i, source in enumerate(XREF_RE.split(line)):
        if found_colon:
            after_colon.append(source)
        else:
            m = SINGLE_COLON_RE.search(source)
            if (i % 2) == 0 and m:
                found_colon = True
                colon = source[m.start(): m.end()]
                before_colon.append(source[:m.start()])
                after_colon.append(source[m.end():])
            else:
                before_colon.append(source)

    return (
        "".join(before_colon).strip(),
        colon,
        "".join(after_colon).strip()
    )


def _parse_parameter_type(name_type_str: str) -> Tuple[str, Optional[str]]:
    match = TYPED_PARAM_RE.match(name_type_str)  # type: ignore
    if match:
        return match.group(1), match.group(2)
    else:
        return name_type_str, None


def _escape_args_and_kwargs(name: str) -> str:
    if name.startswith("**"):
        return r"\*\*" + name[2:]
    elif name.startswith("*"):
        return r"\*" + name[1:]
    else:
        return name


def _dedent(lines: Sequence[str]) -> Sequence[str]:
    lens = [
        len(INDENT_RE.match(line).group(1))
        for line in lines if line
    ]
    min_indent = min(lens) if lens else 0
    return [line[min_indent:] for line in lines]
