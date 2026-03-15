"""Tests for the HTML sanitizer — bleach.clean() compatible behavior."""

from __future__ import annotations

from blanch.sanitizer import Cleaner, clean


class TestCleanBasic:
    def test_plain_text_unchanged(self) -> None:
        assert clean("hello world") == "hello world"

    def test_allowed_tag_passes(self) -> None:
        assert clean("<b>bold</b>") == "<b>bold</b>"

    def test_disallowed_tag_escaped(self) -> None:
        result = clean("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result

    def test_disallowed_tag_stripped(self) -> None:
        result = clean("<script>alert('xss')</script>", strip=True)
        assert "<script>" not in result
        assert "&lt;script&gt;" not in result
        assert "alert('xss')" in result

    def test_allowed_attrs_pass(self) -> None:
        result = clean('<a href="http://example.com">link</a>')
        assert 'href="http://example.com"' in result

    def test_disallowed_attrs_stripped(self) -> None:
        result = clean('<a href="http://example.com" onclick="evil()">link</a>')
        assert "onclick" not in result
        assert 'href="http://example.com"' in result

    def test_empty_string(self) -> None:
        assert clean("") == ""

    def test_entities_preserved(self) -> None:
        result = clean("&amp; &lt; &gt;")
        assert "&amp;" in result

    def test_nested_allowed_tags(self) -> None:
        result = clean("<b><i>bold italic</i></b>")
        assert "<b>" in result
        assert "<i>" in result

    def test_mixed_allowed_disallowed(self) -> None:
        result = clean("<b>bold</b><script>evil</script>")
        assert "<b>bold</b>" in result
        assert "&lt;script&gt;" in result


class TestCleanTags:
    def test_custom_tags(self) -> None:
        result = clean("<div>content</div>", tags=["div"])
        assert result == "<div>content</div>"

    def test_frozenset_tags(self) -> None:
        result = clean("<div>content</div>", tags=frozenset(["div"]))
        assert result == "<div>content</div>"

    def test_empty_tags_escapes_all(self) -> None:
        result = clean("<b>bold</b>", tags=[])
        assert "&lt;b&gt;" in result

    def test_empty_tags_strips_all(self) -> None:
        result = clean("<b>bold</b>", tags=[], strip=True)
        assert result == "bold"


class TestCleanAttributes:
    def test_dict_attributes(self) -> None:
        result = clean(
            '<a href="url" title="t">link</a>',
            attributes={"a": ["href"]},
        )
        assert "href" in result
        assert "title" not in result

    def test_list_attributes(self) -> None:
        result = clean(
            '<a href="url" class="c">link</a>',
            tags=["a"],
            attributes=["href", "class"],
        )
        assert "href" in result
        assert "class" in result

    def test_callable_attributes(self) -> None:
        def allow_data(tag: str, name: str, value: str) -> bool:
            return name.startswith("data-")

        result = clean(
            '<div data-x="1" onclick="bad">text</div>',
            tags=["div"],
            attributes=allow_data,
        )
        assert "data-x" in result
        assert "onclick" not in result

    def test_wildcard_attributes(self) -> None:
        result = clean(
            '<b class="x">text</b>',
            attributes={"*": ["class"]},
        )
        assert 'class="x"' in result

    def test_callable_per_tag(self) -> None:
        def allow_all(tag: str, name: str, value: str) -> bool:
            return True

        result = clean(
            '<a href="url" data-x="1">link</a>',
            attributes={"a": allow_all},
        )
        assert "href" in result
        assert "data-x" in result


class TestCleanProtocols:
    def test_allowed_protocol_passes(self) -> None:
        result = clean('<a href="http://example.com">link</a>')
        assert "http://example.com" in result

    def test_https_allowed(self) -> None:
        result = clean('<a href="https://example.com">link</a>')
        assert "https://example.com" in result

    def test_mailto_allowed(self) -> None:
        result = clean('<a href="mailto:test@example.com">mail</a>')
        assert "mailto:test@example.com" in result

    def test_javascript_blocked(self) -> None:
        result = clean('<a href="javascript:alert(1)">xss</a>')
        assert "javascript:" not in result

    def test_data_uri_blocked(self) -> None:
        result = clean('<a href="data:text/html,<script>alert(1)</script>">xss</a>')
        assert "data:" not in result

    def test_relative_url_allowed(self) -> None:
        result = clean('<a href="/path/to/page">link</a>')
        assert "/path/to/page" in result

    def test_custom_protocols(self) -> None:
        result = clean(
            '<a href="ftp://files.example.com">files</a>',
            protocols=["http", "https", "ftp"],
        )
        assert "ftp://files.example.com" in result

    def test_entity_encoded_protocol_blocked(self) -> None:
        # javascript encoded as entities should still be caught
        result = clean('<a href="&#106;avascript:alert(1)">xss</a>')
        assert "javascript" not in result.lower() or "href" not in result


class TestCleanComments:
    def test_comments_stripped_by_default(self) -> None:
        result = clean("text<!-- comment -->more")
        assert "<!--" not in result
        assert "comment" not in result

    def test_comments_preserved_when_requested(self) -> None:
        result = clean("text<!-- comment -->more", strip_comments=False)
        assert "<!-- comment -->" in result


class TestCleanStrip:
    def test_strip_removes_tag_keeps_content(self) -> None:
        result = clean("<div>content</div>", strip=True)
        assert result == "content"
        assert "<div>" not in result

    def test_strip_nested(self) -> None:
        result = clean("<div><b>bold</b></div>", strip=True)
        assert "<b>bold</b>" in result
        assert "<div>" not in result

    def test_escape_shows_tag(self) -> None:
        result = clean("<div>content</div>")
        assert "&lt;div&gt;" in result
        assert "&lt;/div&gt;" in result


class TestCleanerClass:
    def test_reusable(self) -> None:
        cleaner = Cleaner(tags=["b"])
        assert cleaner.clean("<b>one</b>") == "<b>one</b>"
        assert "b>" in cleaner.clean("<b>two</b>")

    def test_with_filters(self) -> None:
        def uppercase(text: str) -> str:
            return text.upper()

        cleaner = Cleaner(filters=[uppercase])
        result = cleaner.clean("hello")
        assert result == "HELLO"


class TestXSSVectors:
    """Basic XSS attack vector tests."""

    def test_script_tag(self) -> None:
        result = clean("<script>alert(document.cookie)</script>")
        assert "<script>" not in result

    def test_img_onerror(self) -> None:
        # img is not in ALLOWED_TAGS, so escaped (attributes visible as text but not rendered)
        result = clean('<img src=x onerror=alert(1)>')
        assert "<img" not in result  # no actual HTML tag

    def test_svg_onload(self) -> None:
        result = clean("<svg onload=alert(1)>")
        assert "<svg" not in result  # no actual HTML tag

    def test_event_handler_attrs(self) -> None:
        for event in ["onclick", "onmouseover", "onfocus", "onload", "onerror"]:
            result = clean(f'<b {event}="alert(1)">text</b>')
            assert event not in result

    def test_javascript_href(self) -> None:
        result = clean('<a href="javascript:void(0)">click</a>')
        assert "javascript:" not in result

    def test_null_byte_in_tag(self) -> None:
        result = clean("<scr\x00ipt>alert(1)</scr\x00ipt>")
        assert "<script>" not in result

    def test_mixed_case_script(self) -> None:
        result = clean("<ScRiPt>alert(1)</ScRiPt>")
        assert "<script>" not in result.lower()

    def test_iframe(self) -> None:
        result = clean('<iframe src="http://evil.com">')
        assert "<iframe" not in result

    def test_object_tag(self) -> None:
        result = clean('<object data="http://evil.com">')
        assert "<object" not in result

    def test_style_tag(self) -> None:
        result = clean("<style>body{display:none}</style>")
        assert "<style>" not in result
