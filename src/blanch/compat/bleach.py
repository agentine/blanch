"""Drop-in bleach compatibility module.

Usage:
    import blanch.compat.bleach as bleach

    bleach.clean("<script>bad</script>")
    bleach.linkify("http://example.com")

All public bleach APIs are re-exported here.
"""

from __future__ import annotations

from blanch.constants import ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS, ALLOWED_TAGS
from blanch.css_sanitizer import CSSSanitizer
from blanch.linkifier import (
    DEFAULT_CALLBACKS,
    Linker,
    build_email_re,
    build_url_re,
    linkify,
)
from blanch.sanitizer import Cleaner, clean

__all__ = [
    "ALLOWED_ATTRIBUTES",
    "ALLOWED_PROTOCOLS",
    "ALLOWED_TAGS",
    "CSSSanitizer",
    "Cleaner",
    "DEFAULT_CALLBACKS",
    "Linker",
    "build_email_re",
    "build_url_re",
    "clean",
    "linkify",
]
