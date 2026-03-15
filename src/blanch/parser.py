"""HTML tokenizer/parser built on stdlib html.parser.HTMLParser.

Security-focused parser that handles malformed HTML gracefully:
- Self-closing tags
- Missing end tags
- Entity normalization
- Null byte stripping
- Nesting depth limits
"""

from __future__ import annotations

import html.parser
import re
from typing import Callable

# Void elements that never have closing tags
VOID_ELEMENTS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

# Maximum nesting depth to prevent stack overflow attacks
MAX_NESTING_DEPTH = 500

# Null bytes and control characters to strip
_NULL_RE = re.compile(r"\x00")


class Token:
    """Base class for parser tokens."""

    __slots__ = ()


class StartTag(Token):
    """An opening HTML tag with attributes."""

    __slots__ = ("tag", "attrs", "self_closing")

    def __init__(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        self_closing: bool = False,
    ) -> None:
        self.tag = tag
        self.attrs = attrs
        self.self_closing = self_closing


class EndTag(Token):
    """A closing HTML tag."""

    __slots__ = ("tag",)

    def __init__(self, tag: str) -> None:
        self.tag = tag


class Data(Token):
    """Text data between tags."""

    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class Comment(Token):
    """An HTML comment."""

    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class EntityRef(Token):
    """A named entity reference like &amp;."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class CharRef(Token):
    """A numeric character reference like &#38; or &#x26;."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class Doctype(Token):
    """A DOCTYPE declaration."""

    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class PI(Token):
    """A processing instruction."""

    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class BlanchHTMLParser(html.parser.HTMLParser):
    """Security-focused HTML tokenizer.

    Emits a stream of Token objects for processing by the sanitizer.
    Handles malformed HTML gracefully and enforces nesting limits.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.tokens: list[Token] = []
        self._depth = 0

    def reset_tokens(self) -> None:
        """Clear accumulated tokens."""
        self.tokens = []
        self._depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        self_closing = tag in VOID_ELEMENTS
        if not self_closing:
            self._depth += 1
            if self._depth > MAX_NESTING_DEPTH:
                # Exceed nesting limit — treat as data
                self._depth -= 1
                return
        self.tokens.append(StartTag(tag, attrs, self_closing))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag not in VOID_ELEMENTS:
            self._depth = max(0, self._depth - 1)
        self.tokens.append(EndTag(tag))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        self.tokens.append(StartTag(tag, attrs, self_closing=True))

    def handle_data(self, data: str) -> None:
        self.tokens.append(Data(data))

    def handle_comment(self, data: str) -> None:
        self.tokens.append(Comment(data))

    def handle_entityref(self, name: str) -> None:
        self.tokens.append(EntityRef(name))

    def handle_charref(self, name: str) -> None:
        self.tokens.append(CharRef(name))

    def handle_decl(self, decl: str) -> None:
        self.tokens.append(Doctype(decl))

    def handle_pi(self, data: str) -> None:
        self.tokens.append(PI(data))

    def unknown_decl(self, data: str) -> None:
        # Treat unknown declarations as comments for safety
        self.tokens.append(Comment(data))


def strip_null_bytes(text: str) -> str:
    """Remove null bytes from text."""
    return _NULL_RE.sub("", text)


def tokenize(text: str) -> list[Token]:
    """Tokenize HTML text into a list of Token objects.

    Strips null bytes, handles malformed HTML gracefully.
    """
    text = strip_null_bytes(text)
    parser = BlanchHTMLParser()
    parser.feed(text)
    return parser.tokens


def serialize_tokens(tokens: list[Token]) -> str:
    """Serialize a list of tokens back to HTML string."""
    parts: list[str] = []
    for token in tokens:
        if isinstance(token, StartTag):
            attrs_str = _serialize_attrs(token.attrs)
            if token.self_closing:
                parts.append(f"<{token.tag}{attrs_str}>")
            else:
                parts.append(f"<{token.tag}{attrs_str}>")
        elif isinstance(token, EndTag):
            parts.append(f"</{token.tag}>")
        elif isinstance(token, Data):
            parts.append(token.data)
        elif isinstance(token, Comment):
            parts.append(f"<!--{token.data}-->")
        elif isinstance(token, EntityRef):
            parts.append(f"&{token.name};")
        elif isinstance(token, CharRef):
            parts.append(f"&#{token.name};")
        elif isinstance(token, Doctype):
            parts.append(f"<!{token.data}>")
        elif isinstance(token, PI):
            parts.append(f"<?{token.data}>")
    return "".join(parts)


def _serialize_attrs(attrs: list[tuple[str, str | None]]) -> str:
    """Serialize attribute list to HTML string."""
    if not attrs:
        return ""
    parts: list[str] = []
    for name, value in attrs:
        if value is None:
            parts.append(f" {name}")
        else:
            escaped = value.replace("&", "&amp;").replace('"', "&quot;")
            parts.append(f' {name}="{escaped}"')
    return "".join(parts)


def walk(
    tokens: list[Token],
    callback: Callable[[Token], Token | list[Token] | None],
) -> list[Token]:
    """Walk tokens, calling callback on each. Callback returns replacement(s) or None to remove."""
    result: list[Token] = []
    for token in tokens:
        out = callback(token)
        if out is None:
            continue
        if isinstance(out, list):
            result.extend(out)
        else:
            result.append(out)
    return result
