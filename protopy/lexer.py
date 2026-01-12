import re
from dataclasses import dataclass

from .errors import ParseError
from .grammar import KEYWORDS, PUNCTUATION, Token
from .spans import Position, Span

# Import terminal instances (not type classes)
from .grammar import EOF, FLOAT, IDENT, INT, STRING

# These are type classes, need their symbol instances
EOF = EOF.symbol
FLOAT = FLOAT.symbol
IDENT = IDENT.symbol
INT = INT.symbol
STRING = STRING.symbol

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INT_RE = re.compile(r"[+-]?(?:0|[1-9][0-9]*)")
_FLOAT_RE = re.compile(
    r"[+-]?(?:"
    r"(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    r"|[0-9]+[eE][+-]?[0-9]+"
    r")"
)


@dataclass(slots=True)
class _Cursor:
    file: str
    src: str
    i: int = 0
    line: int = 1
    col: int = 1

    def eof(self) -> bool:
        return self.i >= len(self.src)

    def peek(self, n: int = 0) -> str:
        j = self.i + n
        if j >= len(self.src):
            return ""
        return self.src[j]

    def advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.eof():
                return
            ch = self.src[self.i]
            self.i += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1

    def pos(self) -> Position:
        return Position(offset=self.i, line=self.line, column=self.col)


def tokenize(src: str, *, file: str = "<memory>") -> list[Token]:
    cur = _Cursor(file=file, src=src)
    tokens: list[Token] = []

    def make_span(start: Position, end: Position) -> Span:
        return Span(file=file, start=start, end=end)

    def error_at(start: Position, msg: str, hint: str | None = None) -> ParseError:
        end = cur.pos()
        if end.offset < start.offset:
            end = start
        return ParseError(span=make_span(start, end), message=msg, hint=hint)

    while not cur.eof():
        ch = cur.peek()

        # whitespace
        if ch in " \t\r\n":
            cur.advance()
            continue

        # line comment //
        if ch == "/" and cur.peek(1) == "/":
            cur.advance(2)
            while not cur.eof() and cur.peek() != "\n":
                cur.advance()
            continue

        # block comment /* ... */
        if ch == "/" and cur.peek(1) == "*":
            start = cur.pos()
            cur.advance(2)
            while not cur.eof():
                if cur.peek() == "*" and cur.peek(1) == "/":
                    cur.advance(2)
                    break
                cur.advance()
            else:
                raise error_at(start, "unterminated block comment", hint="add closing */")
            continue

        start = cur.pos()

        # strings: "..." or '...'
        if ch in "\"'":
            quote = ch
            cur.advance()
            buf: list[str] = []
            while not cur.eof():
                c = cur.peek()
                if c == quote:
                    cur.advance()
                    end = cur.pos()
                    lex = "".join(buf)
                    tokens.append(Token(STRING, lex, make_span(start, end)))
                    break
                if c == "\n":
                    raise error_at(start, "unterminated string literal", hint="close the quote")
                if c == "\\":
                    cur.advance()
                    esc = cur.peek()
                    if esc == "":
                        raise error_at(start, "unterminated string escape")
                    # Keep escapes as-is; parser/AST keeps raw string content.
                    buf.append("\\" + esc)
                    cur.advance()
                    continue
                buf.append(c)
                cur.advance()
            else:
                raise error_at(start, "unterminated string literal", hint="close the quote")
            continue

        # numbers (float before int)
        m = _FLOAT_RE.match(src, cur.i)
        if m:
            lex = m.group(0)
            cur.advance(len(lex))
            end = cur.pos()
            tokens.append(Token(FLOAT, lex, make_span(start, end)))
            continue

        m = _INT_RE.match(src, cur.i)
        if m:
            lex = m.group(0)
            cur.advance(len(lex))
            end = cur.pos()
            tokens.append(Token(INT, lex, make_span(start, end)))
            continue

        # identifiers / keywords
        m = _IDENT_RE.match(src, cur.i)
        if m:
            lex = m.group(0)
            cur.advance(len(lex))
            end = cur.pos()
            kind = KEYWORDS.get(lex, IDENT)
            tokens.append(Token(kind, lex, make_span(start, end)))
            continue

        # punctuation
        k = PUNCTUATION.get(ch)
        if k is not None:
            cur.advance()
            end = cur.pos()
            tokens.append(Token(k, ch, make_span(start, end)))
            continue

        raise error_at(
            start,
            f"unexpected character {ch!r}",
            hint="remove the character or replace with valid proto3 syntax",
        )

    eof_pos = cur.pos()
    tokens.append(Token(EOF, "", Span(file=file, start=eof_pos, end=eof_pos)))
    return tokens

