"""Linkifier — converts URLs and emails in text to clickable links.

Matches bleach.linkify() signature for drop-in compatibility.
HTML-aware: skips content inside specified tags.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence

from blanch.parser import (
    Data,
    EndTag,
    StartTag,
    Token,
    tokenize,
)

# Type for linkify callbacks: (attrs, new) -> attrs or None
LinkifyCallback = Callable[[dict[str | int, str], bool], dict[str | int, str] | None]

# Common TLDs for URL detection
_TLDS = (
    "com|org|net|edu|gov|mil|int|info|biz|name|pro|aero|coop|museum|"
    "io|co|me|tv|cc|us|uk|de|fr|es|it|nl|au|ca|in|br|ru|jp|kr|cn|"
    "app|dev|tech|ai|xyz|online|site|store|blog|cloud"
)


def _nofollow_callback(
    attrs: dict[str | int, str], new: bool
) -> dict[str | int, str]:
    """Default callback that adds rel="nofollow" to new links."""
    if new:
        attrs["rel"] = "nofollow"
    return attrs


DEFAULT_CALLBACKS: list[LinkifyCallback] = [_nofollow_callback]

# Default tags to skip linkification inside
_DEFAULT_SKIP_TAGS: frozenset[str] = frozenset(
    {"pre", "code", "kbd", "script", "style", "textarea"}
)


def build_url_re(
    tlds: str | None = None, protocols: Sequence[str] | None = None
) -> re.Pattern[str]:
    """Build a regex for matching URLs in text.

    Args:
        tlds: Pipe-separated TLD pattern. Defaults to common TLDs.
        protocols: List of protocols to match. Defaults to http, https, ftp.
    """
    tld_pattern = tlds or _TLDS
    proto_list = protocols or ["http", "https", "ftp"]
    proto_pattern = "|".join(re.escape(p) for p in proto_list)

    return re.compile(
        rf"""
        \b
        (?:
            # Protocol-prefixed URLs
            (?:{proto_pattern})://
            [^\s<>\[\]{{}}\|\\^`"']*
            [^\s<>\[\]{{}}\|\\^`"'.,;:!?\)\]}}]
        |
            # www. prefixed URLs
            www\.
            [^\s<>\[\]{{}}\|\\^`"']*
            [^\s<>\[\]{{}}\|\\^`"'.,;:!?\)\]}}]
        |
            # Bare domain URLs (domain.tld/path) — not preceded by @
            (?<![@./])
            [a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?
            \.(?:{tld_pattern})
            (?:/[^\s<>\[\]{{}}\|\\^`"']*
               [^\s<>\[\]{{}}\|\\^`"'.,;:!?\)\]}}])?
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )


def build_email_re(tlds: str | None = None) -> re.Pattern[str]:
    """Build a regex for matching email addresses in text."""
    tld_pattern = tlds or _TLDS
    return re.compile(
        rf"""
        \b
        [a-zA-Z0-9._%+\-]+
        @
        [a-zA-Z0-9.\-]+
        \.(?:{tld_pattern})
        \b
        """,
        re.VERBOSE | re.IGNORECASE,
    )


class Linker:
    """Reusable linkifier instance.

    Args:
        callbacks: List of callbacks to modify link attributes.
            Each callback receives (attrs, new) and returns attrs or None.
        skip_tags: Tags whose content should not be linkified.
        parse_email: Whether to detect and linkify email addresses.
        url_re: Custom URL regex pattern.
        email_re: Custom email regex pattern.
    """

    def __init__(
        self,
        callbacks: list[LinkifyCallback] | None = None,
        skip_tags: list[str] | Sequence[str] | None = None,
        parse_email: bool = False,
        url_re: re.Pattern[str] | None = None,
        email_re: re.Pattern[str] | None = None,
    ) -> None:
        self.callbacks = callbacks if callbacks is not None else list(DEFAULT_CALLBACKS)
        self.skip_tags: frozenset[str] = (
            frozenset(skip_tags) if skip_tags is not None else _DEFAULT_SKIP_TAGS
        )
        self.parse_email = parse_email
        self.url_re = url_re or build_url_re()
        self.email_re = email_re or build_email_re()

    def linkify(self, text: str) -> str:
        """Linkify URLs (and optionally emails) in the given text."""
        tokens = tokenize(text)
        result = self._process_tokens(tokens)
        return self._serialize(result)

    def _process_tokens(self, tokens: list[Token]) -> list[Token]:
        """Process tokens, linkifying text data outside skip tags."""
        result: list[Token] = []
        skip_depth = 0
        skip_tag: str | None = None

        for token in tokens:
            if isinstance(token, StartTag):
                if token.tag in self.skip_tags:
                    if skip_depth == 0:
                        skip_tag = token.tag
                    skip_depth += 1
                # Check if already inside an <a> tag
                if token.tag == "a":
                    skip_depth += 1
                    if skip_tag is None:
                        skip_tag = "a"
                result.append(token)
            elif isinstance(token, EndTag):
                if skip_tag is not None and token.tag == skip_tag:
                    skip_depth -= 1
                    if skip_depth <= 0:
                        skip_depth = 0
                        skip_tag = None
                elif token.tag == "a" and skip_tag == "a":
                    skip_depth -= 1
                    if skip_depth <= 0:
                        skip_depth = 0
                        skip_tag = None
                result.append(token)
            elif isinstance(token, Data) and skip_depth == 0:
                result.extend(self._linkify_text(token.data))
            else:
                result.append(token)

        return result

    def _linkify_text(self, text: str) -> list[Token]:
        """Find URLs/emails in a text string and create link tokens."""
        # Build combined pattern
        patterns: list[tuple[re.Pattern[str], str]] = [
            (self.url_re, "url"),
        ]
        if self.parse_email:
            patterns.append((self.email_re, "email"))

        # Find all matches with their positions
        matches: list[tuple[int, int, str, str]] = []
        for pattern, kind in patterns:
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), m.group(), kind))

        if not matches:
            return [Data(text)]

        # Sort by position, remove overlapping matches
        matches.sort(key=lambda x: x[0])
        filtered: list[tuple[int, int, str, str]] = []
        last_end = 0
        for start, end, match_text, kind in matches:
            if start >= last_end:
                filtered.append((start, end, match_text, kind))
                last_end = end

        tokens: list[Token] = []
        pos = 0

        for start, end, match_text, kind in filtered:
            # Add text before match
            if start > pos:
                tokens.append(Data(text[pos:start]))

            # Determine href
            if kind == "email":
                href = f"mailto:{match_text}"
            elif match_text.startswith(("http://", "https://", "ftp://")):
                href = match_text
            else:
                href = f"https://{match_text}"

            # Build attrs dict
            attrs: dict[str | int, str] = {
                "_text": match_text,
                "href": href,
            }

            # Apply callbacks
            new = True
            for cb in self.callbacks:
                result = cb(attrs, new)
                if result is None:
                    attrs = {}
                    break
                attrs = result

            if attrs:
                link_text = attrs.pop("_text", match_text)
                # Build link tokens
                link_attrs: list[tuple[str, str | None]] = []
                for k, v in attrs.items():
                    if isinstance(k, str):
                        link_attrs.append((k, v))

                tokens.append(StartTag("a", link_attrs))
                tokens.append(Data(link_text))
                tokens.append(EndTag("a"))
            else:
                # Callback returned None — keep original text
                tokens.append(Data(match_text))

            pos = end

        # Add remaining text
        if pos < len(text):
            tokens.append(Data(text[pos:]))

        return tokens

    def _serialize(self, tokens: list[Token]) -> str:
        """Serialize tokens back to HTML."""
        from blanch.parser import serialize_tokens

        return serialize_tokens(tokens)


def linkify(
    text: str,
    callbacks: list[LinkifyCallback] | list[object] | None = None,
    skip_tags: list[str] | Sequence[str] | None = None,
    parse_email: bool = False,
) -> str:
    """Convert URLs and emails in text to clickable links.

    Drop-in replacement for bleach.linkify().
    """
    linker = Linker(
        callbacks=callbacks,  # type: ignore[arg-type]
        skip_tags=skip_tags,
        parse_email=parse_email,
    )
    return linker.linkify(text)
