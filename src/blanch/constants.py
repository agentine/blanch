"""Default allowlists for HTML sanitization, matching bleach defaults."""

from __future__ import annotations

# Default set of allowed HTML tags (matches bleach.ALLOWED_TAGS)
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "a",
        "abbr",
        "acronym",
        "b",
        "blockquote",
        "code",
        "em",
        "i",
        "li",
        "ol",
        "strong",
        "ul",
    }
)

# Default mapping of tags to their allowed attributes (matches bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],
}

# Default set of allowed URI protocols (matches bleach.ALLOWED_PROTOCOLS)
ALLOWED_PROTOCOLS: frozenset[str] = frozenset({"http", "https", "mailto"})
