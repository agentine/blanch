"""XSS attack vector tests based on OWASP and common bypass techniques.

Ensures blanch properly neutralizes known XSS payloads.
"""

from __future__ import annotations

import blanch


class TestXSSScriptInjection:
    def test_basic_script(self) -> None:
        assert "<script>" not in blanch.clean("<script>alert(1)</script>")

    def test_script_with_attributes(self) -> None:
        result = blanch.clean('<script src="http://evil.com/xss.js"></script>')
        assert "<script" not in result

    def test_script_mixed_case(self) -> None:
        result = blanch.clean("<ScRiPt>alert(1)</ScRiPt>")
        assert "<script" not in result.lower()

    def test_script_with_newlines(self) -> None:
        result = blanch.clean("<script\n>alert(1)</script\n>")
        assert "<script" not in result.lower()

    def test_null_byte_in_script(self) -> None:
        result = blanch.clean("<scr\x00ipt>alert(1)</scr\x00ipt>")
        assert "<script" not in result.lower()


class TestXSSEventHandlers:
    def test_onclick(self) -> None:
        result = blanch.clean('<b onclick="alert(1)">text</b>')
        assert "onclick" not in result

    def test_onmouseover(self) -> None:
        result = blanch.clean('<b onmouseover="alert(1)">text</b>')
        assert "onmouseover" not in result

    def test_onfocus(self) -> None:
        result = blanch.clean('<b onfocus="alert(1)">text</b>')
        assert "onfocus" not in result

    def test_onerror_img(self) -> None:
        result = blanch.clean('<img src=x onerror="alert(1)">')
        assert "<img" not in result  # img not in allowed tags

    def test_onload_body(self) -> None:
        # body is not in ALLOWED_TAGS, so it's escaped (attributes visible as text, not rendered)
        result = blanch.clean('<body onload="alert(1)">text</body>')
        assert "<body" not in result


class TestXSSProtocolHandlers:
    def test_javascript_href(self) -> None:
        result = blanch.clean('<a href="javascript:alert(1)">link</a>')
        assert "javascript:" not in result

    def test_javascript_upper(self) -> None:
        result = blanch.clean('<a href="JAVASCRIPT:alert(1)">link</a>')
        assert "javascript" not in result.lower() or "href" not in result

    def test_javascript_tab(self) -> None:
        result = blanch.clean('<a href="java\tscript:alert(1)">link</a>')
        # html.parser may normalize this; just ensure no executable href
        assert "javascript" not in result.lower() or "href" not in result

    def test_vbscript(self) -> None:
        result = blanch.clean('<a href="vbscript:MsgBox(1)">link</a>')
        assert "vbscript:" not in result

    def test_data_uri(self) -> None:
        result = blanch.clean(
            '<a href="data:text/html,<script>alert(1)</script>">xss</a>'
        )
        assert "data:" not in result

    def test_entity_encoded_javascript(self) -> None:
        result = blanch.clean('<a href="&#106;avascript:alert(1)">xss</a>')
        # After entity decoding, should still block javascript:
        assert "href" not in result or "javascript" not in result.lower()


class TestXSSDangerousTags:
    def test_iframe(self) -> None:
        result = blanch.clean('<iframe src="http://evil.com">')
        assert "<iframe" not in result

    def test_object(self) -> None:
        result = blanch.clean('<object data="http://evil.com">')
        assert "<object" not in result

    def test_embed(self) -> None:
        result = blanch.clean('<embed src="http://evil.com">')
        assert "<embed" not in result

    def test_form(self) -> None:
        result = blanch.clean('<form action="http://evil.com"><input></form>')
        assert "<form" not in result

    def test_meta_refresh(self) -> None:
        result = blanch.clean(
            '<meta http-equiv="refresh" content="0;url=http://evil.com">'
        )
        assert "<meta" not in result

    def test_svg(self) -> None:
        result = blanch.clean("<svg><g onload=alert(1)></g></svg>")
        assert "<svg" not in result

    def test_math(self) -> None:
        result = blanch.clean("<math><mi>x</mi></math>")
        assert "<math" not in result

    def test_style_tag(self) -> None:
        result = blanch.clean(
            "<style>body{background:url(javascript:alert(1))}</style>"
        )
        assert "<style" not in result

    def test_base_tag(self) -> None:
        result = blanch.clean('<base href="http://evil.com">')
        assert "<base" not in result


class TestXSSStrip:
    """Same tests but with strip=True to ensure tag content doesn't execute."""

    def test_strip_script(self) -> None:
        result = blanch.clean("<script>alert(1)</script>", strip=True)
        assert "<script" not in result

    def test_strip_iframe(self) -> None:
        result = blanch.clean(
            '<iframe src="http://evil.com"></iframe>', strip=True
        )
        assert "<iframe" not in result

    def test_strip_removes_dangerous(self) -> None:
        result = blanch.clean(
            '<div><script>alert(1)</script>safe</div>', strip=True
        )
        assert "<script" not in result
        assert "safe" in result


class TestXSSEdgeCases:
    def test_deeply_nested_tags(self) -> None:
        # Shouldn't crash on deeply nested input
        html = "<div>" * 100 + "text" + "</div>" * 100
        result = blanch.clean(html, strip=True)
        assert "text" in result

    def test_unclosed_tags(self) -> None:
        result = blanch.clean("<script>alert(1)")
        assert "<script" not in result

    def test_multiple_lt(self) -> None:
        result = blanch.clean("<<script>alert(1)</script>")
        assert "<script" not in result

    def test_comment_containing_script(self) -> None:
        result = blanch.clean("<!-- <script>alert(1)</script> -->")
        assert "<script" not in result

    def test_attribute_without_value(self) -> None:
        result = blanch.clean("<b disabled>text</b>")
        # disabled is not in allowed attributes for b
        assert "disabled" not in result
