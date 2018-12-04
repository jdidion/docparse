from dataclasses import dataclass
from enum import Enum
import inspect
from pkg_resources import iter_entry_points
from typing import Callable, Dict, Optional, Sequence, cast


class DocStyle(Enum):
    """Enumeration of supported DocTypes.
    """
    GOOGLE = "google"


@dataclass
class Paragraphs:
    paragraphs: Sequence[str]

    def __len__(self):
        return len(self.paragraphs)

    def __getitem__(self, item):
        return self.paragraphs[item]

    def __str__(self):
        return "\n".join(self.paragraphs)

    @staticmethod
    def from_lines(lines: Sequence[str]) -> "Paragraphs":
        """Join consecutive non-empty lines.
        """
        paragraphs = []
        start = 0
        n = len(lines)

        while start < n:
            try:
                end = lines.index("", start)
                paragraphs.append(" ".join(lines[start: end]))
                start = end + 1
            except ValueError:
                paragraphs.append(" ".join(lines[start:]))
                break

        return Paragraphs(paragraphs)


@dataclass
class Named:
    names: str
    description: Paragraphs = None


@dataclass
class Typed:
    datatype: str
    description: Paragraphs = None


@dataclass
class Field:
    name: str
    datatype: str = None
    description: Paragraphs = None


class DocString:
    def __init__(
        self,
        description: Optional[Paragraphs] = None,
        parameters: Optional[Dict[str, Field]] = None,
        keyword_arguments: Optional[Dict[str, Field]] = None,
        returns: Optional[Typed] = None,
        yields: Optional[Typed] = None,
        raises: Optional[Dict[str, Field]] = None,
        directives: Optional[Dict[str, Paragraphs]] = None,
        **kwargs
    ):
        self.sections = dict(
            description=description,
            parameters=parameters,
            keyword_arguments=keyword_arguments,
            returns=returns,
            yields=yields,
            raises=raises,
        )
        self.sections.update(kwargs)
        self.directives = directives

    def __contains__(self, section):
        return section in self.sections

    def __getattr__(self, section):
        return self.sections[section]

    def __getitem__(self, section):
        return self.sections[section]

    @property
    def summary(self) -> Optional[str]:
        if self.description and len(self.description) > 0:
            return self.description[0]
        return None

    def has_directive(self, name):
        return self.directives and name in self.directives

    def get_directive(self, name) -> Paragraphs:
        if not self.has_directive(name):
            raise ValueError(f"Directive not found: '{name}'")
        return self.directives[name]


REGISTRY: Dict[DocStyle, Callable[[str], DocString]] = None


def parser(docstyle: DocStyle):
    """Decorator for a parser function.
    """
    def decorator(f):
        REGISTRY[docstyle] = f
        return f

    return decorator


def parse_docs(obj, docstyle: DocStyle) -> Optional[DocString]:
    """Parses a docstring of the specified style.

    Args:
        obj: Either a docstring or an object that has an associated docstring.
        docstyle: The docstring style.

    Returns:
        A DocString object, or None if `obj` is None or has no docstring.
    """
    parse_func = REGISTRY[docstyle]
    docstring = get_docstring(obj)
    if docstring:
        return parse_func(docstring)


def get_docstring(obj) -> str:
    if isinstance(obj, str):
        return inspect.cleandoc(cast(str, obj))
    else:
        return inspect.getdoc(obj)


if REGISTRY is None:
    REGISTRY = {}
    defaults = {}
    # process entry points, defer loading default parsers
    for entry_point in iter_entry_points(group="docparse.parsers"):
        if entry_point.name.endswith("_default"):
            defaults[entry_point.name[:-8]] = entry_point
        else:
            entry_point.load()
    # load default parsers for doc styles that haven't been overridden
    for name, entry_point in defaults.items():
        if name not in REGISTRY:
            entry_point.load()
