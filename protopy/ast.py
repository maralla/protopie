from __future__ import annotations

from dataclasses import dataclass, field

from .spans import Span


@dataclass(frozen=True, slots=True)
class Node:
    span: Span


@dataclass(frozen=True, slots=True)
class QualifiedName(Node):
    """A dotted name, optionally absolute (leading dot in source)."""

    absolute: bool
    parts: tuple[str, ...]

    def __str__(self) -> str:
        dot = "." if self.absolute else ""
        return dot + ".".join(self.parts)


@dataclass(frozen=True, slots=True)
class Syntax(Node):
    value: str  # raw string literal content, not unescaped


@dataclass(frozen=True, slots=True)
class Import(Node):
    path: str  # raw string literal content, not unescaped
    modifier: str | None = None  # "weak" | "public" | None


@dataclass(frozen=True, slots=True)
class Package(Node):
    name: QualifiedName


@dataclass(frozen=True, slots=True)
class OptionName(Node):
    """Option name including custom options in parens.

    Examples:
      - java_package
      - (my.custom).opt
      - (my.custom).opt.sub
    """

    # If custom is False, base is the full dotted name and suffix must be empty.
    # If custom is True, base is the dotted name inside parentheses and suffix are the identifiers
    # after the closing paren.
    custom: bool
    base: QualifiedName
    suffix: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Constant(Node):
    kind: str  # "ident" | "int" | "float" | "string" | "bool" | "aggregate"
    value: object


@dataclass(frozen=True, slots=True)
class Option(Node):
    name: OptionName
    value: Constant


@dataclass(frozen=True, slots=True)
class OptionStmt(Node):
    option: Option


@dataclass(frozen=True, slots=True)
class FieldOption(Node):
    option: Option


@dataclass(frozen=True, slots=True)
class Field(Node):
    name: str
    number: int
    type_name: QualifiedName | None = None
    scalar_type: str | None = None
    map_key_type: str | None = None  # only for map<k,v>
    map_value: "TypeRef | None" = None
    repeated: bool = False
    options: tuple[FieldOption, ...] = ()


@dataclass(frozen=True, slots=True)
class TypeRef(Node):
    """Represents a non-map type."""

    type_name: QualifiedName | None = None
    scalar_type: str | None = None


@dataclass(frozen=True, slots=True)
class Oneof(Node):
    name: str
    fields: tuple[Field, ...] = ()


@dataclass(frozen=True, slots=True)
class ReservedRange(Node):
    start: int
    end: int | None = None  # inclusive; None means single value
    end_is_max: bool = False


@dataclass(frozen=True, slots=True)
class Reserved(Node):
    ranges: tuple[ReservedRange, ...] = ()
    names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EnumValue(Node):
    name: str
    number: int
    options: tuple[FieldOption, ...] = ()


@dataclass(frozen=True, slots=True)
class Enum(Node):
    name: str
    body: tuple[OptionStmt | Reserved | EnumValue | "Message" | "Enum", ...] = ()


@dataclass(frozen=True, slots=True)
class Message(Node):
    name: str
    body: tuple[OptionStmt | Reserved | Field | Oneof | "Message" | Enum, ...] = ()


@dataclass(frozen=True, slots=True)
class Rpc(Node):
    name: str
    request: TypeRef
    response: TypeRef
    request_stream: bool = False
    response_stream: bool = False
    options: tuple[OptionStmt, ...] = ()


@dataclass(frozen=True, slots=True)
class Service(Node):
    name: str
    body: tuple[OptionStmt | Rpc, ...] = ()


TopLevel = Import | Package | OptionStmt | Message | Enum | Service


@dataclass(frozen=True, slots=True)
class ProtoFile(Node):
    syntax: Syntax | None = None
    items: tuple[TopLevel, ...] = ()

    # convenience indexes; computed by parser/loader
    imports: tuple[Import, ...] = field(default_factory=tuple)
    package: Package | None = None

