"""HTML sanitizer — Cleaner class and clean() function.

Matches bleach.clean() signature for drop-in compatibility.
Allowlist-based: only permitted tags, attributes, and protocols pass through.
"""

from __future__ import annotations

import html
import re
from typing import Callable, Sequence

from blanch.constants import ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS, ALLOWED_TAGS
from blanch.parser import (
    CharRef,
    Comment,
    Data,
    Doctype,
    EndTag,
    EntityRef,
    PI,
    StartTag,
    Token,
    tokenize,
)

# Attributes that can contain URLs and must be protocol-checked
_URL_ATTRS: frozenset[str] = frozenset(
    {"href", "src", "action", "formaction", "cite", "poster", "background", "dynsrc", "lowsrc"}
)

# Pattern for extracting protocol from a URL value
_PROTOCOL_RE = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9+\-.]*)\s*:", re.ASCII)


class Cleaner:
    """Reusable HTML sanitizer.

    Args:
        tags: Allowed HTML tags. Defaults to ALLOWED_TAGS.
        attributes: Allowed attributes per tag. Can be a dict mapping tag names
            to lists of attribute names, a list of attribute names (applied to all tags),
            or a callable(tag, name, value) -> bool.
        protocols: Allowed URL protocols. Defaults to ALLOWED_PROTOCOLS.
        strip: If True, disallowed tags are removed entirely.
            If False (default), they are escaped.
        strip_comments: If True (default), HTML comments are removed.
        filters: Post-processing filter callables.
        css_sanitizer: Optional CSSSanitizer instance for style attributes.
    """

    def __init__(
        self,
        tags: frozenset[str] | set[str] | list[str] | Sequence[str] | None = None,
        attributes: (
            dict[str, list[str] | Callable[[str, str, str], bool]]
            | list[str]
            | Callable[[str, str, str], bool]
            | None
        ) = None,
        protocols: frozenset[str] | set[str] | list[str] | Sequence[str] | None = None,
        strip: bool = False,
        strip_comments: bool = True,
        filters: list[Callable[[str], str]] | None = None,
        css_sanitizer: object | None = None,
    ) -> None:
        self.tags: frozenset[str] = (
            frozenset(tags) if tags is not None else ALLOWED_TAGS
        )
        self.attributes = attributes if attributes is not None else ALLOWED_ATTRIBUTES
        self.protocols: frozenset[str] = (
            frozenset(protocols) if protocols is not None else ALLOWED_PROTOCOLS
        )
        self.strip = strip
        self.strip_comments = strip_comments
        self.filters = filters or []
        self.css_sanitizer = css_sanitizer

    def clean(self, text: str) -> str:
        """Sanitize the given HTML string."""
        tokens = tokenize(text)
        result = self._process_tokens(tokens)
        output = self._serialize(result)
        for f in self.filters:
            output = f(output)
        return output

    def _is_attr_allowed(self, tag: str, attr_name: str, attr_value: str) -> bool:
        """Check if an attribute is allowed for the given tag."""
        attrs = self.attributes

        if callable(attrs):
            return attrs(tag, attr_name, attr_value)

        if isinstance(attrs, list):
            return attr_name in attrs

        if isinstance(attrs, dict):
            # Check tag-specific attributes
            tag_attrs = attrs.get(tag, [])
            if callable(tag_attrs):
                return tag_attrs(tag, attr_name, attr_value)
            if attr_name in tag_attrs:
                return True
            # Check wildcard attributes
            star_attrs = attrs.get("*", [])
            if callable(star_attrs):
                return star_attrs(tag, attr_name, attr_value)
            if attr_name in star_attrs:
                return True
            return False

        return False

    def _is_protocol_allowed(self, value: str) -> bool:
        """Check if a URL value uses an allowed protocol."""
        # Decode entities for protocol checking
        decoded = html.unescape(value).strip()
        m = _PROTOCOL_RE.match(decoded)
        if m:
            protocol = m.group(1).lower()
            return protocol in self.protocols
        # No protocol = relative URL, allowed
        return True

    def _process_tokens(self, tokens: list[Token]) -> list[Token]:
        """Process tokens through the sanitization pipeline."""
        result: list[Token] = []
        # Track which tags are being stripped so we can strip their end tags too
        strip_stack: list[str] = []

        for token in tokens:
            if isinstance(token, StartTag):
                if token.tag in self.tags:
                    # Allowed tag — filter its attributes
                    filtered_attrs = self._filter_attrs(token.tag, token.attrs)
                    result.append(
                        StartTag(token.tag, filtered_attrs, token.self_closing)
                    )
                elif self.strip:
                    # Strip mode: remove the tag entirely
                    if not token.self_closing:
                        strip_stack.append(token.tag)
                else:
                    # Escape mode: convert to visible text
                    result.append(Data(_escape_tag(token)))

            elif isinstance(token, EndTag):
                if token.tag in self.tags:
                    result.append(token)
                elif self.strip:
                    # Pop from strip stack if present
                    if strip_stack and strip_stack[-1] == token.tag:
                        strip_stack.pop()
                else:
                    result.append(Data(f"&lt;/{token.tag}&gt;"))

            elif isinstance(token, Comment):
                if not self.strip_comments:
                    result.append(token)

            elif isinstance(token, (Doctype, PI)):
                # Always strip doctype and processing instructions
                pass

            else:
                # Data, EntityRef, CharRef — pass through
                result.append(token)

        return result

    def _filter_attrs(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> list[tuple[str, str | None]]:
        """Filter attributes for an allowed tag."""
        filtered: list[tuple[str, str | None]] = []
        for name, value in attrs:
            name = name.lower()
            val_str = value if value is not None else ""

            if not self._is_attr_allowed(tag, name, val_str):
                continue

            # Protocol check for URL attributes
            if name in _URL_ATTRS and value is not None:
                if not self._is_protocol_allowed(value):
                    continue

            # CSS sanitizer for style attributes
            if name == "style" and value is not None and self.css_sanitizer is not None:
                sanitize_css = getattr(self.css_sanitizer, "sanitize_css", None)
                if sanitize_css is not None:
                    value = sanitize_css(value)
                    if not value:
                        continue

            filtered.append((name, value))
        return filtered

    def _serialize(self, tokens: list[Token]) -> str:
        """Serialize processed tokens back to HTML."""
        parts: list[str] = []
        for token in tokens:
            if isinstance(token, StartTag):
                attrs_str = _serialize_attrs(token.attrs)
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
        return "".join(parts)


def _escape_tag(tag: StartTag) -> str:
    """Escape a tag to visible HTML entities."""
    attrs_str = _serialize_attrs(tag.attrs)
    return f"&lt;{tag.tag}{attrs_str}&gt;"


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


def clean(
    text: str,
    tags: frozenset[str] | set[str] | list[str] | Sequence[str] | None = None,
    attributes: (
        dict[str, list[str] | Callable[[str, str, str], bool]]
        | list[str]
        | Callable[[str, str, str], bool]
        | None
    ) = None,
    protocols: frozenset[str] | set[str] | list[str] | Sequence[str] | None = None,
    strip: bool = False,
    strip_comments: bool = True,
    css_sanitizer: object | None = None,
) -> str:
    """Sanitize HTML text, allowing only specified tags, attributes, and protocols.

    Drop-in replacement for bleach.clean().
    """
    cleaner = Cleaner(
        tags=tags,
        attributes=attributes,
        protocols=protocols,
        strip=strip,
        strip_comments=strip_comments,
        css_sanitizer=css_sanitizer,
    )
    return cleaner.clean(text)
