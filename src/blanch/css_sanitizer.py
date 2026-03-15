"""CSS sanitizer for style attribute sanitization.

Strips disallowed CSS properties and blocks dangerous CSS values.
"""

from __future__ import annotations

import re

# Default safe CSS properties (matches common bleach CSSSanitizer defaults)
DEFAULT_ALLOWED_CSS_PROPERTIES: frozenset[str] = frozenset(
    {
        "azimuth",
        "background-color",
        "border-bottom-color",
        "border-collapse",
        "border-color",
        "border-left-color",
        "border-right-color",
        "border-top-color",
        "clear",
        "color",
        "cursor",
        "direction",
        "display",
        "elevation",
        "float",
        "font",
        "font-family",
        "font-size",
        "font-style",
        "font-variant",
        "font-weight",
        "height",
        "letter-spacing",
        "line-height",
        "margin",
        "margin-bottom",
        "margin-left",
        "margin-right",
        "margin-top",
        "overflow",
        "padding",
        "padding-bottom",
        "padding-left",
        "padding-right",
        "padding-top",
        "pause",
        "pause-after",
        "pause-before",
        "pitch",
        "pitch-range",
        "richness",
        "speak",
        "speak-header",
        "speak-numeral",
        "speak-punctuation",
        "speech-rate",
        "stress",
        "text-align",
        "text-decoration",
        "text-indent",
        "unicode-bidi",
        "vertical-align",
        "voice-family",
        "volume",
        "white-space",
        "width",
    }
)

DEFAULT_ALLOWED_SVG_PROPERTIES: frozenset[str] = frozenset(
    {
        "fill",
        "fill-opacity",
        "fill-rule",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "opacity",
    }
)

# Dangerous CSS value patterns
_DANGEROUS_VALUE_RE = re.compile(
    r"""
    url\s*\(        |  # url() function
    expression\s*\( |  # IE expression()
    javascript\s*:  |  # javascript: protocol
    vbscript\s*:    |  # vbscript: protocol
    -moz-binding       # Firefox XBL binding
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Parse CSS property:value pairs
_CSS_PROP_RE = re.compile(
    r"""
    \s*
    ([a-zA-Z\-]+)   # property name
    \s*:\s*          # colon
    ([^;]*)          # value (up to semicolon or end)
    """,
    re.VERBOSE,
)


class CSSSanitizer:
    """Sanitizes CSS in style attributes.

    Args:
        allowed_css_properties: Set of allowed CSS property names.
            Defaults to DEFAULT_ALLOWED_CSS_PROPERTIES.
        allowed_svg_properties: Set of allowed SVG CSS property names.
            Defaults to DEFAULT_ALLOWED_SVG_PROPERTIES.
    """

    def __init__(
        self,
        allowed_css_properties: frozenset[str] | set[str] | list[str] | None = None,
        allowed_svg_properties: frozenset[str] | set[str] | list[str] | None = None,
    ) -> None:
        self.allowed_css_properties: frozenset[str] = (
            frozenset(allowed_css_properties)
            if allowed_css_properties is not None
            else DEFAULT_ALLOWED_CSS_PROPERTIES
        )
        self.allowed_svg_properties: frozenset[str] = (
            frozenset(allowed_svg_properties)
            if allowed_svg_properties is not None
            else DEFAULT_ALLOWED_SVG_PROPERTIES
        )

    def sanitize_css(self, style: str) -> str:
        """Sanitize a CSS style string, keeping only allowed properties."""
        allowed = self.allowed_css_properties | self.allowed_svg_properties
        safe_parts: list[str] = []

        for match in _CSS_PROP_RE.finditer(style):
            prop = match.group(1).strip().lower()
            value = match.group(2).strip()

            if prop not in allowed:
                continue

            if _DANGEROUS_VALUE_RE.search(value):
                continue

            safe_parts.append(f"{prop}: {value}")

        return "; ".join(safe_parts)
