"""blanch — Drop-in replacement for bleach HTML sanitization library."""

from __future__ import annotations

from typing import Callable

from blanch.constants import ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS, ALLOWED_TAGS
from blanch.css_sanitizer import CSSSanitizer
from blanch.linkifier import Linker
from blanch.sanitizer import Cleaner

__all__ = [
    "ALLOWED_ATTRIBUTES",
    "ALLOWED_PROTOCOLS",
    "ALLOWED_TAGS",
    "CSSSanitizer",
    "Cleaner",
    "Linker",
    "clean",
    "linkify",
]

__version__ = "0.1.0"


def clean(
    text: str,
    tags: frozenset[str] | set[str] | list[str] | None = None,
    attributes: (
        dict[str, list[str] | Callable[[str, str, str], bool]]
        | list[str]
        | Callable[[str, str, str], bool]
        | None
    ) = None,
    protocols: frozenset[str] | set[str] | list[str] | None = None,
    strip: bool = False,
    strip_comments: bool = True,
    css_sanitizer: object | None = None,
) -> str:
    """Sanitize HTML, allowing only specified tags, attributes, and protocols."""
    from blanch.sanitizer import clean as _clean

    return _clean(
        text,
        tags=tags,
        attributes=attributes,
        protocols=protocols,
        strip=strip,
        strip_comments=strip_comments,
        css_sanitizer=css_sanitizer,
    )


def linkify(
    text: str,
    callbacks: list[object] | None = None,
    skip_tags: list[str] | None = None,
    parse_email: bool = False,
) -> str:
    """Convert URLs and emails in text to clickable links."""
    from blanch.linkifier import linkify as _linkify

    return _linkify(
        text,
        callbacks=callbacks,
        skip_tags=skip_tags,
        parse_email=parse_email,
    )
