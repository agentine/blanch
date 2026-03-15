"""Tests for the linkifier — bleach.linkify() compatible behavior."""

from __future__ import annotations

from blanch.linkifier import (
    DEFAULT_CALLBACKS,
    Linker,
    build_email_re,
    build_url_re,
    linkify,
)


class TestLinkifyBasic:
    def test_plain_text_unchanged(self) -> None:
        assert linkify("hello world") == "hello world"

    def test_url_with_protocol(self) -> None:
        result = linkify("visit http://example.com today")
        assert '<a href="http://example.com"' in result
        assert "http://example.com</a>" in result

    def test_https_url(self) -> None:
        result = linkify("visit https://example.com today")
        assert '<a href="https://example.com"' in result

    def test_nofollow_default(self) -> None:
        result = linkify("http://example.com")
        assert 'rel="nofollow"' in result

    def test_www_url(self) -> None:
        result = linkify("visit www.example.com today")
        assert '<a href="https://www.example.com"' in result

    def test_no_double_linkify(self) -> None:
        # Already-linked URLs should not be double-linked
        result = linkify('<a href="http://example.com">example</a>')
        assert result.count("<a ") == 1

    def test_empty_string(self) -> None:
        assert linkify("") == ""

    def test_multiple_urls(self) -> None:
        result = linkify("visit http://a.com and http://b.com")
        assert result.count("<a ") == 2


class TestLinkifyEmail:
    def test_email_not_linked_by_default(self) -> None:
        result = linkify("email user@example.com please")
        assert "<a " not in result

    def test_email_linked_when_enabled(self) -> None:
        result = linkify("email user@example.com please", parse_email=True)
        assert '<a href="mailto:user@example.com"' in result

    def test_email_with_nofollow(self) -> None:
        result = linkify("user@example.com", parse_email=True)
        assert 'rel="nofollow"' in result


class TestLinkifyCallbacks:
    def test_custom_callback(self) -> None:
        def add_target(
            attrs: dict[str | int, str], new: bool
        ) -> dict[str | int, str]:
            attrs["target"] = "_blank"
            return attrs

        result = linkify(
            "http://example.com", callbacks=[add_target]
        )
        assert 'target="_blank"' in result

    def test_callback_returns_none_prevents_link(self) -> None:
        def block_all(
            attrs: dict[str | int, str], new: bool
        ) -> dict[str | int, str] | None:
            return None

        result = linkify("http://example.com", callbacks=[block_all])
        assert "<a " not in result
        assert "http://example.com" in result

    def test_default_callbacks(self) -> None:
        assert len(DEFAULT_CALLBACKS) == 1


class TestLinkifySkipTags:
    def test_skip_pre(self) -> None:
        result = linkify("<pre>http://example.com</pre>")
        assert "<a " not in result

    def test_skip_code(self) -> None:
        result = linkify("<code>http://example.com</code>")
        assert "<a " not in result

    def test_custom_skip_tags(self) -> None:
        result = linkify(
            "<div>http://example.com</div>",
            skip_tags=["div"],
        )
        assert "<a " not in result

    def test_normal_tags_not_skipped(self) -> None:
        result = linkify("<p>http://example.com</p>")
        assert "<a " in result


class TestLinkerClass:
    def test_reusable(self) -> None:
        linker = Linker()
        r1 = linker.linkify("http://a.com")
        r2 = linker.linkify("http://b.com")
        assert "a.com" in r1
        assert "b.com" in r2

    def test_custom_url_re(self) -> None:
        custom_re = build_url_re(protocols=["http", "https", "ftp"])
        linker = Linker(url_re=custom_re)
        result = linker.linkify("ftp://files.example.com")
        assert '<a href="ftp://files.example.com"' in result


class TestBuildRegex:
    def test_url_re_matches_http(self) -> None:
        pattern = build_url_re()
        assert pattern.search("visit http://example.com today")

    def test_url_re_matches_https(self) -> None:
        pattern = build_url_re()
        assert pattern.search("visit https://example.com/path today")

    def test_email_re_matches(self) -> None:
        pattern = build_email_re()
        assert pattern.search("email user@example.com today")

    def test_url_re_custom_tlds(self) -> None:
        pattern = build_url_re(tlds="custom")
        assert pattern.search("example.custom")

    def test_url_re_custom_protocols(self) -> None:
        pattern = build_url_re(protocols=["gopher"])
        assert pattern.search("gopher://example.com")
