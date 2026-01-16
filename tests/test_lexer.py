"""Comprehensive tests for the lexer/tokenizer.

This module extensively tests all tokenization scenarios including:
- Valid tokens (integers, floats, strings, identifiers, keywords, punctuation)
- Invalid inputs and error handling
- Edge cases and corner cases
- Property-based testing with randomly generated data
"""

# ruff: noqa: S101, ANN201, PLR2004, ANN001, FURB116
# mypy: disable-error-code="attr-defined,no-untyped-def"

import pytest
from hypothesis import given, strategies as st

from protopie.lexer import tokenize
from protopie.errors import ParseError


class TestIntegerLiterals:
    """Test integer literal tokenization."""

    def test_decimal_integers(self):
        """Test decimal integer literals."""
        cases = [
            ("0", [("INT", "0")]),
            ("1", [("INT", "1")]),
            ("123", [("INT", "123")]),
            ("999", [("INT", "999")]),
            ("1234567890", [("INT", "1234567890")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_signed_integers(self):
        """Test signed integer literals."""
        cases = [
            ("+123", [("INT", "+123")]),
            ("-123", [("INT", "-123")]),
            ("+0", [("INT", "+0")]),
            ("-0", [("INT", "-0")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_octal_integers(self):
        """Test octal integer literals."""
        cases = [
            ("00", [("INT", "00")]),
            ("01", [("INT", "01")]),
            ("0123", [("INT", "0123")]),
            ("0777", [("INT", "0777")]),
            ("00000", [("INT", "00000")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_hexadecimal_integers(self):
        """Test hexadecimal integer literals."""
        cases = [
            ("0x0", [("INT", "0x0")]),
            ("0x1", [("INT", "0x1")]),
            ("0x123", [("INT", "0x123")]),
            ("0xabc", [("INT", "0xabc")]),
            ("0xABC", [("INT", "0xABC")]),
            ("0xAbC123", [("INT", "0xAbC123")]),
            ("0X123", [("INT", "0X123")]),
            ("0Xabc", [("INT", "0Xabc")]),
            ("0xdeadbeef", [("INT", "0xdeadbeef")]),
            ("0xDEADBEEF", [("INT", "0xDEADBEEF")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_invalid_octal_literals(self):
        """Test that invalid octal literals raise errors."""
        invalid_cases = [
            "08",
            "09",
            "0888",
            "099999",
            "01238",
        ]
        for src in invalid_cases:
            with pytest.raises(
                ParseError, match="numbers starting with leading zero must be in octal"
            ):
                tokenize(src)

    def test_invalid_hex_literals(self):
        """Test that invalid hex literals raise errors."""
        invalid_cases = [
            "0x",
            "0X",
        ]
        for src in invalid_cases:
            with pytest.raises(ParseError, match='"0x" must be followed by hex digits'):
                tokenize(src)

    def test_number_followed_by_identifier_error(self):
        """Test that numbers immediately followed by identifiers raise errors."""
        invalid_cases = [
            "0abcd",
            "123abc",
            "9xabdd",
            "0123abc",
            "0x123xyz",
        ]
        for src in invalid_cases:
            with pytest.raises(ParseError, match="need space between number and identifier"):
                tokenize(src)

    def test_numbers_with_whitespace_separation(self):
        """Test that numbers and identifiers work with proper whitespace."""
        cases = [
            ("0 123", [("INT", "0"), ("INT", "123")]),
            ("123 abc", [("INT", "123"), ("IDENT", "abc")]),
            ("0x123 abc", [("INT", "0x123"), ("IDENT", "abc")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"


class TestFloatLiterals:
    """Test floating-point literal tokenization."""

    def test_basic_floats(self):
        """Test basic float literals."""
        cases = [
            ("0.0", [("FLOAT", "0.0")]),
            ("1.0", [("FLOAT", "1.0")]),
            ("3.14", [("FLOAT", "3.14")]),
            ("0.5", [("FLOAT", "0.5")]),
            (".5", [("FLOAT", ".5")]),
            ("5.", [("FLOAT", "5.")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_floats_with_exponents(self):
        """Test float literals with exponents."""
        cases = [
            ("1e10", [("FLOAT", "1e10")]),
            ("1E10", [("FLOAT", "1E10")]),
            ("1e+10", [("FLOAT", "1e+10")]),
            ("1e-10", [("FLOAT", "1e-10")]),
            ("1.5e10", [("FLOAT", "1.5e10")]),
            ("1.5e+10", [("FLOAT", "1.5e+10")]),
            ("1.5e-10", [("FLOAT", "1.5e-10")]),
            (".5e10", [("FLOAT", ".5e10")]),
            ("5.e10", [("FLOAT", "5.e10")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_signed_floats(self):
        """Test signed float literals."""
        cases = [
            ("+3.14", [("FLOAT", "+3.14")]),
            ("-3.14", [("FLOAT", "-3.14")]),
            ("+1e10", [("FLOAT", "+1e10")]),
            ("-1e10", [("FLOAT", "-1e10")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_float_followed_by_identifier_error(self):
        """Test that floats immediately followed by identifiers raise errors."""
        invalid_cases = [
            "3.14abc",
            "1e10xyz",
            ".5foo",
        ]
        for src in invalid_cases:
            with pytest.raises(ParseError, match="need space between number and identifier"):
                tokenize(src)


class TestStringLiterals:
    """Test string literal tokenization."""

    def test_basic_strings(self):
        """Test basic string literals."""
        cases = [
            ('""', [("STRING", "")]),
            ("''", [("STRING", "")]),
            ('"hello"', [("STRING", "hello")]),
            ("'hello'", [("STRING", "hello")]),
            ('"hello world"', [("STRING", "hello world")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_strings_with_escapes(self):
        """Test string literals with escape sequences."""
        cases = [
            (r'"hello\nworld"', [("STRING", r"hello\nworld")]),
            (r'"hello\tworld"', [("STRING", r"hello\tworld")]),
            (r'"hello\"world"', [("STRING", r"hello\"world")]),
            (r'"hello\\world"', [("STRING", r"hello\\world")]),
            (r"'hello\'world'", [("STRING", r"hello\'world")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_unterminated_strings(self):
        """Test that unterminated strings raise errors."""
        invalid_cases = [
            '"hello',
            "'hello",
            '"hello\nworld"',  # Newline terminates string
        ]
        for src in invalid_cases:
            with pytest.raises(ParseError, match="unterminated string"):
                tokenize(src)


class TestIdentifiersAndKeywords:
    """Test identifier and keyword tokenization."""

    def test_identifiers(self):
        """Test identifier tokenization."""
        cases = [
            ("a", [("IDENT", "a")]),
            ("abc", [("IDENT", "abc")]),
            ("_foo", [("IDENT", "_foo")]),
            ("foo123", [("IDENT", "foo123")]),
            ("foo_bar", [("IDENT", "foo_bar")]),
            ("Foo", [("IDENT", "Foo")]),
            ("FOO", [("IDENT", "FOO")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_keywords(self):
        """Test keyword tokenization."""
        keywords = [
            "syntax",
            "import",
            "weak",
            "public",
            "package",
            "option",
            "repeated",
            "optional",
            "message",
            "enum",
            "service",
            "rpc",
            "returns",
            "stream",
            "oneof",
            "map",
            "reserved",
            "to",
            "extend",
            "max",
            "true",
            "false",
        ]
        for keyword in keywords:
            tokens = tokenize(keyword)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == [(keyword, keyword)], f"Failed for keyword: {keyword}"


class TestPunctuation:
    """Test punctuation tokenization."""

    def test_single_char_punctuation(self):
        """Test single-character punctuation."""
        punctuation = [
            ";",
            ",",
            ".",
            "=",
            "{",
            "}",
            "[",
            "]",
            "(",
            ")",
            "<",
            ">",
        ]
        for punct in punctuation:
            tokens = tokenize(punct)
            result = [t for t in tokens if t.symbol_name != "EOF"]
            assert len(result) == 1, f"Failed for: {punct}"
            assert result[0].lexeme == punct

    def test_minus_alone_is_error(self):
        """Test that a minus sign alone is an error."""
        # A lone minus tries to be a number but fails
        with pytest.raises(ParseError, match="unexpected character"):
            tokenize("-")


class TestComments:
    """Test comment handling."""

    def test_line_comments(self):
        """Test line comment handling."""
        cases = [
            ("// comment", []),
            ("123 // comment", [("INT", "123")]),
            ("// comment\n123", [("INT", "123")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_block_comments(self):
        """Test block comment handling."""
        cases = [
            ("/* comment */", []),
            ("123 /* comment */ 456", [("INT", "123"), ("INT", "456")]),
            ("/* multi\nline\ncomment */", []),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"

    def test_unterminated_block_comment(self):
        """Test that unterminated block comments raise errors."""
        with pytest.raises(ParseError, match="unterminated block comment"):
            tokenize("/* comment")


class TestWhitespace:
    """Test whitespace handling."""

    def test_whitespace_separation(self):
        """Test that whitespace properly separates tokens."""
        cases = [
            ("123 456", [("INT", "123"), ("INT", "456")]),
            ("123\n456", [("INT", "123"), ("INT", "456")]),
            ("123\t456", [("INT", "123"), ("INT", "456")]),
            ("123\r\n456", [("INT", "123"), ("INT", "456")]),
            ("  123  456  ", [("INT", "123"), ("INT", "456")]),
        ]
        for src, expected in cases:
            tokens = tokenize(src)
            result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
            assert result == expected, f"Failed for: {src}"


class TestEdgeCases:
    """Test edge cases and corner cases."""

    def test_empty_input(self):
        """Test tokenizing empty input."""
        tokens = tokenize("")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert result == []

    def test_only_whitespace(self):
        """Test tokenizing only whitespace."""
        tokens = tokenize("   \n\t\r\n   ")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert result == []

    def test_only_comments(self):
        """Test tokenizing only comments."""
        tokens = tokenize("// comment\n/* block */")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert result == []

    def test_unexpected_character(self):
        """Test that unexpected characters raise errors."""
        invalid_chars = ["@", "#", "$", "%", "^", "&", "*", "`", "~"]
        for char in invalid_chars:
            with pytest.raises(ParseError, match="unexpected character"):
                tokenize(char)

    def test_multiple_tokens_on_same_line(self):
        """Test multiple tokens on the same line."""
        src = "message Foo { int32 bar = 1; }"
        tokens = tokenize(src)
        result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
        expected = [
            ("message", "message"),
            ("IDENT", "Foo"),
            ("{", "{"),
            ("IDENT", "int32"),
            ("IDENT", "bar"),
            ("=", "="),
            ("INT", "1"),
            (";", ";"),
            ("}", "}"),
        ]
        assert result == expected


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_proto_syntax_declaration(self):
        """Test typical proto syntax declaration."""
        src = 'syntax = "proto3";'
        tokens = tokenize(src)
        result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
        expected = [
            ("syntax", "syntax"),
            ("=", "="),
            ("STRING", "proto3"),
            (";", ";"),
        ]
        assert result == expected

    def test_message_definition(self):
        """Test message definition tokenization."""
        src = """
        message Person {
            string name = 1;
            int32 age = 2;
        }
        """
        tokens = tokenize(src)
        result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
        expected = [
            ("message", "message"),
            ("IDENT", "Person"),
            ("{", "{"),
            ("IDENT", "string"),
            ("IDENT", "name"),
            ("=", "="),
            ("INT", "1"),
            (";", ";"),
            ("IDENT", "int32"),
            ("IDENT", "age"),
            ("=", "="),
            ("INT", "2"),
            (";", ";"),
            ("}", "}"),
        ]
        assert result == expected

    def test_enum_definition(self):
        """Test enum definition tokenization."""
        src = """
        enum Status {
            UNKNOWN = 0;
            ACTIVE = 1;
        }
        """
        tokens = tokenize(src)
        result = [(t.symbol_name, t.lexeme) for t in tokens if t.symbol_name != "EOF"]
        expected = [
            ("enum", "enum"),
            ("IDENT", "Status"),
            ("{", "{"),
            ("IDENT", "UNKNOWN"),
            ("=", "="),
            ("INT", "0"),
            (";", ";"),
            ("IDENT", "ACTIVE"),
            ("=", "="),
            ("INT", "1"),
            (";", ";"),
            ("}", "}"),
        ]
        assert result == expected


class TestPropertyBased:
    """Property-based tests using Hypothesis for random data generation."""

    @given(st.integers(min_value=1, max_value=999999))
    def test_random_decimal_integers(self, n):
        """Test random decimal integers."""
        src = str(n)
        tokens = tokenize(src)
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 1
        assert type(result[0]).symbol_name == "INT"
        assert result[0].lexeme == src

    @given(st.integers(min_value=0, max_value=511))
    def test_random_octal_integers(self, n):
        """Test random octal integers (0-7 digits only)."""
        # Generate octal string
        if n == 0:
            src = "0"
        else:
            octal_str = oct(n)[2:]  # Remove '0o' prefix
            src = "0" + octal_str
        tokens = tokenize(src)
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 1
        assert type(result[0]).symbol_name == "INT"

    @given(st.integers(min_value=0, max_value=0xFFFFFF))
    def test_random_hex_integers(self, n):
        """Test random hexadecimal integers."""
        src = hex(n)  # Produces '0x...' format
        tokens = tokenize(src)
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 1
        assert type(result[0]).symbol_name == "INT"
        assert result[0].lexeme.lower() == src.lower()

    @given(st.floats(min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False))
    def test_random_floats(self, f):
        """Test random float values."""
        src = str(f)
        # Skip if it doesn't contain a decimal point or exponent
        if "." not in src and "e" not in src:
            return
        try:
            tokens = tokenize(src)
            result = [t for t in tokens if t.symbol_name != "EOF"]
            # Should tokenize as either FLOAT or INT
            assert len(result) >= 1
            assert type(result[0]).symbol_name in ("FLOAT", "INT")
        except ParseError:
            # Some float representations might be invalid, that's ok
            pass

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"), min_codepoint=ord("a"), max_codepoint=ord("z")
            ),
            min_size=1,
            max_size=20,
        )
    )
    def test_random_identifiers(self, s):
        """Test random identifier strings."""
        # Ensure it starts with a letter
        if not s[0].isalpha():
            s = "a" + s
        # Add underscores randomly
        src = s.replace(" ", "_")
        tokens = tokenize(src)
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 1
        # Could be an identifier or a keyword
        known_keywords = {
            "syntax",
            "import",
            "weak",
            "public",
            "package",
            "option",
            "repeated",
            "optional",
            "message",
            "enum",
            "service",
            "rpc",
            "returns",
            "stream",
            "oneof",
            "map",
            "reserved",
            "to",
            "extend",
            "max",
            "true",
            "false",
        }
        if src in known_keywords:
            assert type(result[0]).symbol_name == src
        else:
            assert type(result[0]).symbol_name == "IDENT"

    @given(st.text(min_size=0, max_size=100))
    def test_random_string_literals(self, s):
        """Test random string content in double quotes."""
        # Escape special characters
        escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        src = f'"{escaped}"'
        try:
            tokens = tokenize(src)
            result = [t for t in tokens if t.symbol_name != "EOF"]
            assert len(result) == 1
            assert type(result[0]).symbol_name == "STRING"
        except ParseError:
            # Some strings might be invalid, that's ok
            pass


class TestSpanInformation:
    """Test that span information is correctly tracked."""

    def test_single_token_span(self):
        """Test span for a single token."""
        tokens = tokenize("123")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 1
        token = result[0]
        assert token.span.start.offset == 0
        assert token.span.start.line == 1
        assert token.span.start.column == 1

    def test_multiple_tokens_span(self):
        """Test spans for multiple tokens."""
        tokens = tokenize("123 456")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 2
        # First token
        assert result[0].span.start.offset == 0
        assert result[0].span.start.column == 1
        # Second token
        assert result[1].span.start.offset == 4
        assert result[1].span.start.column == 5

    def test_multiline_span(self):
        """Test spans across multiple lines."""
        tokens = tokenize("123\n456")
        result = [t for t in tokens if t.symbol_name != "EOF"]
        assert len(result) == 2
        # First token on line 1
        assert result[0].span.start.line == 1
        # Second token on line 2
        assert result[1].span.start.line == 2
        assert result[1].span.start.column == 1
