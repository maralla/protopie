"""Lexical analyzer for Protocol Buffers proto3 syntax.

This module provides tokenization of proto3 source code into a stream of tokens.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ParseError
from .grammar import KEYWORDS, PUNCTUATION, Token
from .spans import Position, Span

from .grammar import EOF, FLOAT, IDENT, INT, STRING

# Character sets for lexical analysis
HEX_LETTERS = ("a", "b", "c", "d", "e", "f")
OCTAL_DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7")
INVALID_OCTAL_DIGITS = ("8", "9")
DECIMAL_DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
SIGN_CHARS = ("+", "-")
HEX_PREFIX_CHARS = ("x", "X")
EXPONENT_CHARS = ("e", "E")
WHITESPACE_CHARS = (" ", "\t", "\r", "\n")
QUOTE_CHARS = ('"', "'")


def _is_identifier_start(char: str) -> bool:
    return char.isalpha() or char == "_"


def _is_identifier_continue(char: str) -> bool:
    return char.isalnum() or char == "_"


def _is_digit(char: str) -> bool:
    return "0" <= char <= "9"


@dataclass(slots=True)
class _SourceCursor:
    file: str
    source: str
    index: int = 0
    line: int = 1
    column: int = 1

    def is_at_end(self) -> bool:
        return self.index >= len(self.source)

    # Look ahead at character without advancing cursor
    def peek(self, offset: int = 0) -> str:
        position = self.index + offset
        if position >= len(self.source):
            return ""
        return self.source[position]

    # Move cursor forward by count characters, tracking line/column
    def advance(self, count: int = 1) -> None:
        for _ in range(count):
            if self.is_at_end():
                return
            char = self.source[self.index]
            self.index += 1
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1

    def current_position(self) -> Position:
        return Position(offset=self.index, line=self.line, column=self.column)

    def scan_identifier(self) -> str:
        start_index = self.index
        while not self.is_at_end() and _is_identifier_continue(self.peek()):
            self.advance()
        return self.source[start_index : self.index]

    def _is_hex_digit(self, char: str) -> bool:
        # Check if character is a hexadecimal digit
        return char.isdigit() or char.lower() in HEX_LETTERS

    def _scan_hex_digits(self) -> None:
        # Scan hexadecimal digits
        while True:
            ch = self.peek()
            if ch and self._is_hex_digit(ch):
                self.advance()
            else:
                break

    def _scan_octal_digits(self) -> None:
        # Scan octal digits
        while self.peek() in OCTAL_DIGITS:
            self.advance()

    def _validate_no_identifier_after_number(self, start_pos: Position) -> None:
        # Check if number is immediately followed by identifier (no whitespace)
        next_char = self.peek()
        if next_char and _is_identifier_start(next_char):
            end_pos = self.current_position()
            raise ParseError.detail(
                span=Span(file=self.file, start=start_pos, end=end_pos),
                message="need space between number and identifier",
                hint="add whitespace after the number",
            )

    def _scan_hex_literal(self, start_pos: Position) -> None:
        # Scan hexadecimal literal after 0x/0X
        hex_char = self.peek(1)
        if hex_char and self._is_hex_digit(hex_char):
            self.advance()  # consume x/X
            self._scan_hex_digits()
        else:
            # "0x" must be followed by hex digits
            end_pos = self.current_position()
            raise ParseError.detail(
                span=Span(file=self.file, start=start_pos, end=end_pos),
                message='"0x" must be followed by hex digits',
                hint="add hex digits after 0x or remove the x",
            )

    def _scan_octal_literal(self, start_pos: Position) -> None:
        # Scan octal literal - only 0-7 allowed
        self._scan_octal_digits()
        # Check if invalid octal digit (8 or 9) appears
        if self.peek() in INVALID_OCTAL_DIGITS:
            end_pos = self.current_position()
            raise ParseError.detail(
                span=Span(file=self.file, start=start_pos, end=end_pos),
                message="numbers starting with leading zero must be in octal",
                hint="remove leading zero or use only digits 0-7 for octal",
            )

    def scan_integer(self) -> str:
        char = self.peek()

        if not (_is_digit(char) or char in SIGN_CHARS):
            return ""

        start_index = self.index
        start_pos = self.current_position()
        saved_line = self.line
        saved_column = self.column

        if char in SIGN_CHARS:
            self.advance()
            if not _is_digit(self.peek()):
                self._restore_position(start_index, saved_line, saved_column)
                return ""
            char = self.peek()

        if char == "0":
            self.advance()
            next_char = self.peek()

            if next_char in HEX_PREFIX_CHARS:
                self._scan_hex_literal(start_pos)
            elif next_char in DECIMAL_DIGITS:
                self._scan_octal_literal(start_pos)
        else:
            # Decimal: [1-9][0-9]*
            while _is_digit(self.peek()):
                self.advance()

        self._validate_no_identifier_after_number(start_pos)
        return self.source[start_index : self.index]

    def _restore_position(self, index: int, line: int, column: int) -> None:
        self.index = index
        self.line = line
        self.column = column

    # Scan optional exponent part: e/E followed by optional sign and digits.
    # Returns True if valid exponent was found, False otherwise.
    def _scan_optional_exponent(self) -> bool:
        if self.peek() not in EXPONENT_CHARS:
            return True  # No exponent is valid

        self.advance()
        if self.peek() in SIGN_CHARS:
            self.advance()

        if not _is_digit(self.peek()):
            return False  # Invalid exponent

        while _is_digit(self.peek()):
            self.advance()

        return True

    def _try_scan_float_with_dot(self, start_index: int, digits_before: int) -> str:
        # Try to scan float with decimal point
        # digits_before: 0 if no digits before dot, >0 otherwise
        self.advance()  # consume dot
        digits_after = 0
        while _is_digit(self.peek()):
            digits_after += 1
            self.advance()

        # Must have digits before or after decimal point, and valid exponent
        if (digits_before > 0 or digits_after > 0) and self._scan_optional_exponent():
            return self.source[start_index : self.index]
        return ""

    def _try_scan_float_with_exponent(self, start_index: int) -> str:
        # Try to scan float with exponent (no decimal point)
        if self._scan_optional_exponent():
            return self.source[start_index : self.index]
        return ""

    # Scan a floating-point literal.
    # Recognizes: [digits].[digits][exponent] | .[digits][exponent] | [digits]exponent
    def scan_float(self) -> str:
        char = self.peek()

        if not (_is_digit(char) or char in SIGN_CHARS or char == "."):
            return ""

        start_index = self.index
        start_pos = self.current_position()
        saved_index = self.index
        saved_line = self.line
        saved_column = self.column
        result = ""

        if self.peek() in SIGN_CHARS:
            self.advance()

        digits_before_dot = 0
        while _is_digit(self.peek()):
            digits_before_dot += 1
            self.advance()

        # Try decimal point path
        if self.peek() == ".":
            result = self._try_scan_float_with_dot(start_index, digits_before_dot)
        # Try exponent-only path
        elif digits_before_dot > 0 and self.peek() in EXPONENT_CHARS:
            result = self._try_scan_float_with_exponent(start_index)

        if not result:
            self._restore_position(saved_index, saved_line, saved_column)
            return result

        self._validate_no_identifier_after_number(start_pos)
        return result

    def skip_whitespace(self) -> None:
        while self.peek() in WHITESPACE_CHARS:
            self.advance()

    # Skip line comment (// ...). Returns True if comment was found.
    def skip_line_comment(self) -> bool:
        if self.peek() == "/" and self.peek(1) == "/":
            self.advance(2)
            while not self.is_at_end() and self.peek() != "\n":
                self.advance()
            return True
        return False

    # Skip block comment (/* ... */). Returns True if comment was found.
    def skip_block_comment(self) -> bool:
        if self.peek() == "/" and self.peek(1) == "*":
            start = self.current_position()
            self.advance(2)
            while not self.is_at_end():
                if self.peek() == "*" and self.peek(1) == "/":
                    self.advance(2)
                    return True
                self.advance()

            # Unterminated block comment
            end = self.current_position()
            raise ParseError.detail(
                span=Span(file=self.file, start=start, end=end),
                message="unterminated block comment",
                hint="add closing */",
            )
        return False

    # Scan a string literal (double or single quoted)
    def scan_string_literal(self) -> tuple[str, Span]:
        start = self.current_position()
        quote = self.peek()
        self.advance()

        buffer: list[str] = []
        while not self.is_at_end():
            char = self.peek()

            if char == quote:
                self.advance()
                end = self.current_position()
                lexeme = "".join(buffer)
                return lexeme, Span(file=self.file, start=start, end=end)

            if char == "\n":
                end = self.current_position()
                raise ParseError.detail(
                    span=Span(file=self.file, start=start, end=end),
                    message="unterminated string literal",
                    hint="close the quote",
                )

            if char == "\\":
                self.advance()
                escape_char = self.peek()
                if escape_char == "":
                    end = self.current_position()
                    raise ParseError.detail(
                        span=Span(file=self.file, start=start, end=end),
                        message="unterminated string escape",
                    )

                # Keep escapes as-is; parser/AST keeps raw string content
                buffer.append("\\" + escape_char)
                self.advance()
                continue

            buffer.append(char)
            self.advance()

        # Unterminated string
        end = self.current_position()
        raise ParseError.detail(
            span=Span(file=self.file, start=start, end=end),
            message="unterminated string literal",
            hint="close the quote",
        )


def tokenize(source: str, *, file: str = "<memory>") -> list[Token]:
    """Tokenize proto3 source code into a list of tokens.

    Args:
        source: Proto3 source code as a string
        file: Filename for error messages (default: "<memory>")

    Returns:
        List of tokens including an EOF token at the end

    Raises:
        ParseError: If lexical errors are encountered (invalid syntax, unterminated strings, etc.)

    """
    cursor = _SourceCursor(file=file, source=source)
    tokens: list[Token] = []

    while not cursor.is_at_end():
        cursor.skip_whitespace()
        if cursor.is_at_end():
            break

        if cursor.skip_line_comment():
            continue
        if cursor.skip_block_comment():
            continue

        start = cursor.current_position()
        char = cursor.peek()

        # String literals
        if char in QUOTE_CHARS:
            lexeme, span = cursor.scan_string_literal()
            tokens.append(STRING(span=span, lexeme=lexeme))
            continue

        # must try before integers
        float_lexeme = cursor.scan_float()
        if float_lexeme:
            end = cursor.current_position()
            tokens.append(FLOAT(span=Span(file=file, start=start, end=end), lexeme=float_lexeme))
            continue

        int_lexeme = cursor.scan_integer()
        if int_lexeme:
            end = cursor.current_position()
            tokens.append(INT(span=Span(file=file, start=start, end=end), lexeme=int_lexeme))
            continue

        # Identifiers and keywords
        if _is_identifier_start(char):
            lexeme = cursor.scan_identifier()
            end = cursor.current_position()
            token_class = KEYWORDS.get(lexeme, IDENT)
            tokens.append(token_class(span=Span(file=file, start=start, end=end), lexeme=lexeme))
            continue

        # Punctuation
        punctuation_class = PUNCTUATION.get(char)
        if punctuation_class is not None:
            cursor.advance()
            end = cursor.current_position()
            span = Span(file=file, start=start, end=end)
            tokens.append(punctuation_class(span=span, lexeme=char))
            continue

        # Unexpected character
        cursor.advance()  # Move past the bad character
        end = cursor.current_position()
        raise ParseError.detail(
            span=Span(file=file, start=start, end=end),
            message=f"unexpected character {char!r}",
            hint="remove the character or replace with valid proto3 syntax",
        )

    # Add EOF token
    eof_position = cursor.current_position()
    eof_span = Span(file=file, start=eof_position, end=eof_position)
    tokens.append(EOF(span=eof_span, lexeme=""))
    return tokens
