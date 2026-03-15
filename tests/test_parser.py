"""Tests for the HTML parser/tokenizer."""

from __future__ import annotations

from blanch.parser import (
    BlanchHTMLParser,
    CharRef,
    Comment,
    Data,
    Doctype,
    EndTag,
    EntityRef,
    StartTag,
    serialize_tokens,
    strip_null_bytes,
    tokenize,
    walk,
)


class TestTokenize:
    def test_simple_text(self) -> None:
        tokens = tokenize("hello world")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Data)
        assert tokens[0].data == "hello world"

    def test_simple_tag(self) -> None:
        tokens = tokenize("<b>bold</b>")
        assert len(tokens) == 3
        assert isinstance(tokens[0], StartTag)
        assert tokens[0].tag == "b"
        assert isinstance(tokens[1], Data)
        assert tokens[1].data == "bold"
        assert isinstance(tokens[2], EndTag)
        assert tokens[2].tag == "b"

    def test_tag_with_attributes(self) -> None:
        tokens = tokenize('<a href="http://example.com" title="test">link</a>')
        assert isinstance(tokens[0], StartTag)
        assert tokens[0].tag == "a"
        assert tokens[0].attrs == [
            ("href", "http://example.com"),
            ("title", "test"),
        ]

    def test_void_element(self) -> None:
        tokens = tokenize("hello<br>world")
        assert len(tokens) == 3
        assert isinstance(tokens[0], Data)
        assert isinstance(tokens[1], StartTag)
        assert tokens[1].tag == "br"
        assert tokens[1].self_closing is True
        assert isinstance(tokens[2], Data)

    def test_self_closing_void(self) -> None:
        tokens = tokenize("hello<br/>world")
        assert len(tokens) == 3
        assert isinstance(tokens[1], StartTag)
        assert tokens[1].tag == "br"
        assert tokens[1].self_closing is True

    def test_comment(self) -> None:
        tokens = tokenize("<!-- comment -->")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Comment)
        assert tokens[0].data == " comment "

    def test_entity_ref(self) -> None:
        tokens = tokenize("&amp;")
        assert len(tokens) == 1
        assert isinstance(tokens[0], EntityRef)
        assert tokens[0].name == "amp"

    def test_char_ref_decimal(self) -> None:
        tokens = tokenize("&#38;")
        assert len(tokens) == 1
        assert isinstance(tokens[0], CharRef)
        assert tokens[0].name == "38"

    def test_char_ref_hex(self) -> None:
        tokens = tokenize("&#x26;")
        assert len(tokens) == 1
        assert isinstance(tokens[0], CharRef)
        assert tokens[0].name == "x26"

    def test_mixed_content(self) -> None:
        tokens = tokenize("<p>Hello &amp; <b>world</b></p>")
        assert len(tokens) == 8
        assert isinstance(tokens[0], StartTag)
        assert isinstance(tokens[1], Data)
        assert isinstance(tokens[2], EntityRef)
        assert isinstance(tokens[3], Data)  # " "
        assert isinstance(tokens[4], StartTag)
        assert isinstance(tokens[5], Data)

    def test_uppercase_tags_normalized(self) -> None:
        tokens = tokenize("<DIV>content</DIV>")
        assert isinstance(tokens[0], StartTag)
        assert tokens[0].tag == "div"
        assert isinstance(tokens[2], EndTag)
        assert tokens[2].tag == "div"

    def test_nested_tags(self) -> None:
        tokens = tokenize("<div><p><b>deep</b></p></div>")
        tags = [(type(t).__name__, getattr(t, "tag", None)) for t in tokens]
        assert tags == [
            ("StartTag", "div"),
            ("StartTag", "p"),
            ("StartTag", "b"),
            ("Data", None),
            ("EndTag", "b"),
            ("EndTag", "p"),
            ("EndTag", "div"),
        ]

    def test_malformed_unclosed_tag(self) -> None:
        tokens = tokenize("<p>unclosed")
        assert len(tokens) == 2
        assert isinstance(tokens[0], StartTag)
        assert isinstance(tokens[1], Data)

    def test_doctype(self) -> None:
        tokens = tokenize("<!DOCTYPE html>")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Doctype)

    def test_boolean_attribute(self) -> None:
        tokens = tokenize("<input disabled>")
        assert isinstance(tokens[0], StartTag)
        assert tokens[0].attrs == [("disabled", None)]

    def test_empty_string(self) -> None:
        tokens = tokenize("")
        assert tokens == []


class TestStripNullBytes:
    def test_strips_null(self) -> None:
        assert strip_null_bytes("hel\x00lo") == "hello"

    def test_no_nulls(self) -> None:
        assert strip_null_bytes("hello") == "hello"

    def test_multiple_nulls(self) -> None:
        assert strip_null_bytes("\x00a\x00b\x00") == "ab"


class TestSerializeTokens:
    def test_roundtrip_simple(self) -> None:
        html = "<b>bold</b>"
        assert serialize_tokens(tokenize(html)) == html

    def test_roundtrip_attrs(self) -> None:
        html = '<a href="http://example.com">link</a>'
        assert serialize_tokens(tokenize(html)) == html

    def test_roundtrip_entity(self) -> None:
        html = "&amp;"
        assert serialize_tokens(tokenize(html)) == html

    def test_roundtrip_comment(self) -> None:
        html = "<!-- hello -->"
        assert serialize_tokens(tokenize(html)) == html

    def test_escapes_attr_quotes(self) -> None:
        tokens = [StartTag("a", [("title", 'say "hi"')])]
        result = serialize_tokens(tokens)
        assert result == '<a title="say &quot;hi&quot;">'

    def test_boolean_attr_serialization(self) -> None:
        tokens = [StartTag("input", [("disabled", None)], self_closing=True)]
        result = serialize_tokens(tokens)
        assert result == "<input disabled>"


class TestWalk:
    def test_identity(self) -> None:
        tokens = tokenize("<b>hello</b>")
        result = walk(tokens, lambda t: t)
        assert len(result) == 3

    def test_remove(self) -> None:
        tokens = tokenize("<!-- remove -->text")
        result = walk(tokens, lambda t: None if isinstance(t, Comment) else t)
        assert len(result) == 1
        assert isinstance(result[0], Data)

    def test_replace_with_list(self) -> None:
        tokens = tokenize("hello")

        def expand(t: object) -> object:
            if isinstance(t, Data):
                return [Data("a"), Data("b")]
            return t

        result = walk(tokens, expand)  # type: ignore[arg-type]
        assert len(result) == 2


class TestNestingDepthLimit:
    def test_excessive_nesting_ignored(self) -> None:
        # Build deeply nested HTML exceeding MAX_NESTING_DEPTH
        depth = 600
        html = "<div>" * depth + "x" + "</div>" * depth
        tokens = tokenize(html)
        # Should not crash; some inner tags get dropped
        start_tags = [t for t in tokens if isinstance(t, StartTag)]
        assert len(start_tags) < depth
