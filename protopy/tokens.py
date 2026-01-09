from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .spans import Span


class TokenKind(str, Enum):
    # Identifiers and literals
    IDENT = "IDENT"
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"

    # Punctuation / operators
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    LPAREN = "("
    RPAREN = ")"
    LANGLE = "<"
    RANGLE = ">"
    SEMI = ";"
    COMMA = ","
    DOT = "."
    EQ = "="
    COLON = ":"
    SLASH = "/"

    # Keywords (proto3)
    SYNTAX = "syntax"
    IMPORT = "import"
    PACKAGE = "package"
    OPTION = "option"
    MESSAGE = "message"
    ENUM = "enum"
    SERVICE = "service"
    RPC = "rpc"
    RETURNS = "returns"
    STREAM = "stream"
    ONEOF = "oneof"
    MAP = "map"
    REPEATED = "repeated"
    RESERVED = "reserved"
    TO = "to"
    MAX = "max"
    WEAK = "weak"
    PUBLIC = "public"

    # Constants / booleans
    TRUE = "true"
    FALSE = "false"

    EOF = "EOF"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    span: Span

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.lexeme!r}, {self.span.format()})"

