"""Tests for bleach compatibility layer.

Tests that blanch.compat.bleach provides the same API surface as bleach.
"""

from __future__ import annotations

import blanch.compat.bleach as bleach


class TestBleachCompatAPI:
    """Verify all public bleach APIs are available."""

    def test_clean_available(self) -> None:
        assert callable(bleach.clean)

    def test_linkify_available(self) -> None:
        assert callable(bleach.linkify)

    def test_cleaner_available(self) -> None:
        assert bleach.Cleaner is not None

    def test_linker_available(self) -> None:
        assert bleach.Linker is not None

    def test_css_sanitizer_available(self) -> None:
        assert bleach.CSSSanitizer is not None

    def test_constants_available(self) -> None:
        assert isinstance(bleach.ALLOWED_TAGS, frozenset)
        assert isinstance(bleach.ALLOWED_ATTRIBUTES, dict)
        assert isinstance(bleach.ALLOWED_PROTOCOLS, frozenset)

    def test_default_callbacks_available(self) -> None:
        assert isinstance(bleach.DEFAULT_CALLBACKS, list)

    def test_build_url_re_available(self) -> None:
        assert callable(bleach.build_url_re)

    def test_build_email_re_available(self) -> None:
        assert callable(bleach.build_email_re)


class TestBleachCompatClean:
    """Test that clean() works through the compatibility module."""

    def test_basic_clean(self) -> None:
        result = bleach.clean("<script>alert('xss')</script>")
        assert "<script>" not in result

    def test_allowed_tags(self) -> None:
        result = bleach.clean("<b>bold</b>")
        assert result == "<b>bold</b>"

    def test_custom_tags(self) -> None:
        result = bleach.clean("<div>hi</div>", tags=["div"])
        assert "<div>hi</div>" == result

    def test_strip_mode(self) -> None:
        result = bleach.clean("<script>bad</script>", strip=True)
        assert "bad" in result
        assert "<script>" not in result

    def test_attributes_dict(self) -> None:
        result = bleach.clean(
            '<a href="http://x.com" onclick="bad">link</a>',
            attributes={"a": ["href"]},
        )
        assert "href" in result
        assert "onclick" not in result

    def test_protocols(self) -> None:
        result = bleach.clean('<a href="javascript:alert(1)">xss</a>')
        assert "javascript:" not in result

    def test_strip_comments(self) -> None:
        result = bleach.clean("text<!-- comment -->more")
        assert "comment" not in result

    def test_css_sanitizer(self) -> None:
        css = bleach.CSSSanitizer()
        result = bleach.clean(
            '<p style="color: red; position: absolute">text</p>',
            tags=["p"],
            attributes={"p": ["style"]},
            css_sanitizer=css,
        )
        assert "color: red" in result
        assert "position" not in result


class TestBleachCompatLinkify:
    """Test that linkify() works through the compatibility module."""

    def test_basic_linkify(self) -> None:
        result = bleach.linkify("http://example.com")
        assert '<a href="http://example.com"' in result

    def test_nofollow(self) -> None:
        result = bleach.linkify("http://example.com")
        assert 'rel="nofollow"' in result

    def test_parse_email(self) -> None:
        result = bleach.linkify("user@example.com", parse_email=True)
        assert "mailto:" in result

    def test_skip_tags(self) -> None:
        result = bleach.linkify("<code>http://example.com</code>")
        assert "<a " not in result

    def test_callbacks(self) -> None:
        def add_class(
            attrs: dict[str | int, str], new: bool
        ) -> dict[str | int, str]:
            attrs["class"] = "external"
            return attrs

        result = bleach.linkify(
            "http://example.com", callbacks=[add_class]
        )
        assert 'class="external"' in result


class TestBleachCompatCleaner:
    """Test Cleaner class through compat module."""

    def test_cleaner_instance(self) -> None:
        cleaner = bleach.Cleaner(tags=["b", "i"])
        result = cleaner.clean("<b>bold</b><script>bad</script>")
        assert "<b>bold</b>" in result
        assert "<script>" not in result

    def test_cleaner_strip(self) -> None:
        cleaner = bleach.Cleaner(strip=True)
        result = cleaner.clean("<div>content</div>")
        assert result == "content"


class TestBleachCompatConstants:
    """Verify constant values match bleach defaults."""

    def test_allowed_tags_values(self) -> None:
        expected = {
            "a", "abbr", "acronym", "b", "blockquote",
            "code", "em", "i", "li", "ol", "strong", "ul",
        }
        assert bleach.ALLOWED_TAGS == expected

    def test_allowed_attributes_values(self) -> None:
        assert "a" in bleach.ALLOWED_ATTRIBUTES
        assert "href" in bleach.ALLOWED_ATTRIBUTES["a"]
        assert "title" in bleach.ALLOWED_ATTRIBUTES["a"]
        assert "abbr" in bleach.ALLOWED_ATTRIBUTES
        assert "acronym" in bleach.ALLOWED_ATTRIBUTES

    def test_allowed_protocols_values(self) -> None:
        assert bleach.ALLOWED_PROTOCOLS == {"http", "https", "mailto"}
