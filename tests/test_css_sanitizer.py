"""Tests for CSS sanitizer."""

from __future__ import annotations

from blanch.css_sanitizer import CSSSanitizer


class TestCSSSanitizer:
    def test_allowed_property(self) -> None:
        s = CSSSanitizer()
        assert s.sanitize_css("color: red") == "color: red"

    def test_disallowed_property(self) -> None:
        s = CSSSanitizer()
        assert s.sanitize_css("position: absolute") == ""

    def test_multiple_properties(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("color: red; font-size: 14px; position: absolute")
        assert "color: red" in result
        assert "font-size: 14px" in result
        assert "position" not in result

    def test_url_blocked(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("background-color: url(http://evil.com)")
        assert result == ""

    def test_expression_blocked(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("color: expression(alert(1))")
        assert result == ""

    def test_javascript_blocked(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("background-color: javascript:alert(1)")
        assert result == ""

    def test_custom_allowed_properties(self) -> None:
        s = CSSSanitizer(allowed_css_properties=["position", "top", "left"])
        result = s.sanitize_css("position: absolute; top: 10px; color: red")
        assert "position: absolute" in result
        assert "top: 10px" in result
        assert "color" not in result

    def test_svg_properties(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("fill: #ff0000; stroke: black")
        assert "fill: #ff0000" in result
        assert "stroke: black" in result

    def test_empty_style(self) -> None:
        s = CSSSanitizer()
        assert s.sanitize_css("") == ""

    def test_moz_binding_blocked(self) -> None:
        s = CSSSanitizer()
        result = s.sanitize_css("color: -moz-binding")
        assert result == ""
