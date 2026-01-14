from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from typing import TYPE_CHECKING

from .symbol import NonTerminal
from .spans import Span

if TYPE_CHECKING:
    from .symbol import Terminal


@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes."""

    span: Span


@dataclass(frozen=True, slots=True)
class DottedName(Node, NonTerminal):
    """Represents a dot separated name.

    Examples:
      - .foo.bar

    """

    parts: tuple[Ident, ...] = ()

    def format(self) -> str:
        return ".".join(p.format() for p in self.parts)


@dataclass(frozen=True, slots=True)
class QualifiedName(Node, NonTerminal):
    """A dotted name, optionally absolute (leading dot in source).

    Examples:
      - foo.bar.Baz
      - .google.protobuf.Timestamp
      - MyMessage

    """

    absolute: bool
    name: DottedName

    def __str__(self) -> str:
        dot = "." if self.absolute else ""
        return dot + self.name.format()

    def format(self) -> str:
        return str(self)


@dataclass(frozen=True, slots=True)
class Syntax(Node, NonTerminal):
    """Syntax declaration statement.

    Examples:
      - syntax = "proto3";

    """

    value: str  # raw string literal content, not unescaped


@dataclass(frozen=True, slots=True)
class Import(Node, NonTerminal):
    """Import statement.

    Examples:
      - import "google/protobuf/timestamp.proto";
      - import public "other.proto";
      - import weak "deprecated.proto";

    """

    path: Ident
    modifier: Ident | None = None  # "weak" | "public" | None


@dataclass(frozen=True, slots=True)
class Package(Node, NonTerminal):
    """Package declaration statement.

    Examples:
      - package google.protobuf;
      - package com.example.foo;

    """

    name: QualifiedName


@dataclass(frozen=True, slots=True)
class OptionSuffix(Node, NonTerminal):
    """Option suffix is a dot connected identifiers after the closing paren.

    Examples:
      - (my.custom).opt
      - (my.custom).opt.sub

    """

    items: tuple[Ident, ...] = ()

    def format(self) -> str:
        return ("." + ".".join(ident.format() for ident in self.items)) if self.items else ""


@dataclass(frozen=True, slots=True)
class OptionName(Node, NonTerminal):
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
    suffix: OptionSuffix = field(default_factory=lambda: OptionSuffix(span=Span.empty()))

    def format(self) -> str:
        """Format option name, including custom options."""
        if self.custom:
            base = str(self.base)
            if self.base.absolute:
                base = base[1:]

            suffix = self.suffix.format()
            return f"({base}){suffix}"

        return str(self.base)



@dataclass(frozen=True, slots=True)
class Ident(Node, NonTerminal):
    """Represents a literal identifier.

    Examples:
      - foo

    """

    text: str

    def format(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class MessageField(Node, NonTerminal):
    """A key-value constant value.

    Examples:
      - foo: 1

    """

    name: Ident
    value: Constant

    def format(self) -> str:
        return self.name.format() + ": "  + self.value.format()


@dataclass(frozen=True, slots=True)
class MessageFields(Node, NonTerminal):
    """A list of key-value constant value.

    Examples:
      - foo: 1, bar: "baz"

    """

    fields: tuple[MessageField, ...] = ()

    def format(self) -> str:
        return ", ".join(f.format() for f in self.fields)


@dataclass(frozen=True, slots=True)
class MessageConstant(Node, NonTerminal):
    """A message constant value.

    Examples:
      - { foo: 1, bar: "baz" }

    """

    value: MessageFields

    def format(self) -> str:
        return self.value.format()


@dataclass(frozen=True, slots=True)
class PrimitiveConstant(Node, NonTerminal):
    """A primitive literal constant value.

    Examples:
      - 42 (integer)
      - 3.14 (float)
      - "hello" (string)
      - true / false (boolean)

    """

    kind: type[Terminal]
    value: str

    def format(self) -> str:
        # String literals need quotes added back (lexer strips them)
        if self.kind.symbol_name == "STRING":
            # Escape quotes and backslashes in the string
            escaped = self.value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return self.value


@dataclass(frozen=True, slots=True)
class Constant(Node, NonTerminal):
    """A constant value in proto3.

    Examples:
      - MyEnum.VALUE (identifier)
      - { foo: 1, bar: "baz" } (aggregate/message literal)

    """

    value: PrimitiveConstant | QualifiedName | MessageConstant

    def format(self) -> str:
        return self.value.format()


@dataclass(frozen=True, slots=True)
class Option(Node, NonTerminal):
    """An option key-value pair.

    Examples:
      - java_package = "com.example.foo"
      - deprecated = true
      - (my.custom.option) = "value"

    """

    name: OptionName
    value: Constant

    def format(self) -> str:
        """Format an option statement."""
        return f"{self.name.format()} = {self.value.format()}"


@dataclass(frozen=True, slots=True)
class OptionStmt(Node, NonTerminal):
    """Top-level or body-level option statement.

    Examples:
      - option java_package = "com.example";
      - option optimize_for = SPEED;

    """

    option: Option

    def format(self, indent: int = 0) -> str:
        """Format option statement."""
        return _indent(f"option {self.option.format()};", indent)


@dataclass(frozen=True, slots=True)
class FieldOptionItems(Node, NonTerminal):
    """A list of field options (without brackets).

    Examples:
      - deprecated = true, json_name = "userId"

    """

    value: tuple[Option, ...] = ()

    def format(self) -> str:
        return ", ".join(opt.format() for opt in self.value)


@dataclass(frozen=True, slots=True)
class FieldOptions(Node, NonTerminal):
    """Field options wrapped in brackets.

    Examples:
      - [deprecated = true]
      - [deprecated = true, json_name = "userId"]

    """

    items: FieldOptionItems = field(default_factory=lambda: FieldOptionItems(span=Span.empty()))

    def format(self) -> str:
        return self.items.format()

    def is_empty(self) -> bool:
        return len(self.items.value) == 0


@dataclass(frozen=True, slots=True)
class MapKeyType(Node, NonTerminal):
    """Map key type identifier.

    Examples:
      - int32
      - string
      - bool

    """

    ident: Ident

    def format(self) -> str:
        return self.ident.format()


@dataclass(frozen=True, slots=True)
class MapType(Node, NonTerminal):
    """Map type specification.

    Examples:
      - map<string, int32>
      - map<int32, MyMessage>

    """

    key_type: MapKeyType
    value_type: QualifiedName

    def format(self) -> str:
        return f"map<{self.key_type.format()}, {self.value_type.format()}>"


@dataclass(frozen=True, slots=True)
class FieldLabel(Node, NonTerminal):
    """Field label (repeated or nothing).

    Examples:
      - repeated
      - (nothing)

    """

    none: bool = False
    repeated: bool = False

    def format(self) -> str:
        if self.repeated:
            return "repeated "

        return ""


@dataclass(frozen=True, slots=True)
class Field(Node, NonTerminal):
    """A field definition in a message or oneof.

    Examples:
      - string name = 1;
      - repeated int32 values = 2;
      - map<string, int32> scores = 3;
      - MyMessage msg = 4 [deprecated = true];

    """

    name: Ident
    number: PrimitiveConstant
    field_type: QualifiedName | MapType
    label: FieldLabel
    options: FieldOptions

    def format(self) -> str:
        result = self.label.format()
        result += self.field_type.format()
        result += " " + self.name.format() + " = " + self.number.format()

        if not self.options.is_empty():
            result += f" [{self.options.format()}]"

        return result


@dataclass(frozen=True, slots=True)
class TypeRef(Node, NonTerminal):
    """A type reference for scalar or message types.

    This represents individual types like int32 or MyMessage, but not
    the map<K,V> composite syntax (which is represented in Field.map_key_type
    and Field.map_value).

    Examples:
      - int32
      - string
      - MyMessage
      - .google.protobuf.Timestamp

    """

    type_name: QualifiedName | None = None
    scalar_type: str | None = None

    def format(self) -> str:
        """Format a type reference."""
        if self.scalar_type is not None:
            return self.scalar_type

        if self.type_name is None:
            return "/*missing-type*/"

        return str(self.type_name)


@dataclass(frozen=True, slots=True)
class OneofField(Node, NonTerminal):
    """A field in a oneof, or an empty line.

    Examples:
      - string name = 1;
      - (empty line with semicolon)

    """

    field: Field | None = None

    def format(self) -> str:
        if self.field is None:
            return ""
        return self.field.format()


@dataclass(frozen=True, slots=True)
class OneofBody(Node, NonTerminal):
    """Body of a oneof definition.

    Examples:
      - (list of oneof fields)

    """

    fields: tuple[OneofField, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        return [
            _indent(oneof_field.format() + ";", indent)
            for oneof_field in self.fields
            if oneof_field.field is not None
        ]


@dataclass(frozen=True, slots=True)
class Oneof(Node, NonTerminal):
    """A oneof group in a message.

    Examples:
      - oneof test_oneof {
          string name = 1;
          int32 value = 2;
        }

    """

    name: Ident
    body: OneofBody

    def format(self, indent: int = 0) -> list[str]:
        output = [_indent(f"oneof {self.name.format()} {{", indent)]
        output.extend(self.body.format(indent + 2))
        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class ReservedRange(Node, NonTerminal):
    """A reserved field number range.

    Examples:
      - 2 (single field number)
      - 9 to 11 (range)
      - 15 to max (open-ended range)

    """

    start: PrimitiveConstant
    end: PrimitiveConstant | Ident | None = None  # inclusive; None means single value

    def format(self) -> str:
        if self.end is None:
            return self.start.format()
        return f"{self.start.format()} to {self.end.format()}"


@dataclass(frozen=True, slots=True)
class RangeCollector(Node, NonTerminal):
    ranges: tuple[ReservedRange, ...] = ()


@dataclass(frozen=True, slots=True)
class NameCollector(Node, NonTerminal):
    names: tuple[Ident, ...] = ()


@dataclass(frozen=True, slots=True)
class ReservedRanges(Node, NonTerminal):
    """A list of reserved ranges.

    Examples:
      - 2, 15, 9 to 11

    """

    ranges: tuple[ReservedRange, ...] = ()

    def format(self) -> str:
        return ", ".join(r.format() for r in self.ranges)


@dataclass(frozen=True, slots=True)
class ReservedNames(Node, NonTerminal):
    """A list of reserved names.

    Examples:
      - "foo", "bar"

    """

    names: tuple[Ident, ...] = ()

    def format(self) -> str:
        return ", ".join(f'"{n.format()}"' for n in self.names)


@dataclass(frozen=True, slots=True)
class ReservedSpec(Node, NonTerminal):
    """Reserved specification (either ranges or names).

    Examples:
      - 2, 15, 9 to 11
      - "foo", "bar"

    """

    ranges: ReservedRanges = field(default_factory=lambda: ReservedRanges(span=Span.empty()))
    names: ReservedNames = field(default_factory=lambda: ReservedNames(span=Span.empty()))

    def format(self) -> str:
        if self.ranges.ranges:
            return self.ranges.format()
        return self.names.format()


@dataclass(frozen=True, slots=True)
class Reserved(Node, NonTerminal):
    """Reserved field numbers or field names.

    Examples:
      - reserved 2, 15, 9 to 11;
      - reserved "foo", "bar";
      - reserved 1 to max;

    """

    spec: ReservedSpec

    def format(self) -> str:
        return f"reserved {self.spec.format()}"


@dataclass(frozen=True, slots=True)
class EnumValue(Node, NonTerminal):
    """An enum value definition.

    Examples:
      - UNKNOWN = 0;
      - STARTED = 1 [deprecated = true];
      - COMPLETED = 2;

    """

    name: Ident
    number: PrimitiveConstant
    options: FieldOptions

    def format(self, indent: int = 0) -> str:
        value_str = f"{self.name.format()} = {self.number.format()}"
        if not self.options.is_empty():
            value_str += f" [{self.options.format()}]"
        return _indent(value_str + ";", indent)


@dataclass(frozen=True, slots=True)
class EnumElem(Node, NonTerminal):
    """An element in an enum body.

    Examples:
      - enum value
      - option statement
      - reserved statement
      - (empty line)

    """

    element: EnumValue | OptionStmt | Reserved | None = None

    def format(self, indent: int = 0) -> str:
        if self.element is None:
            return ""
        if isinstance(self.element, EnumValue):
            return self.element.format(indent)
        if isinstance(self.element, OptionStmt):
            return self.element.format(indent)
        return _indent(self.element.format() + ";", indent)


@dataclass(frozen=True, slots=True)
class EnumBody(Node, NonTerminal):
    """Body of an enum definition.

    Examples:
      - (list of enum values, options, and reserved statements)

    """

    elements: tuple[EnumElem, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        output = []
        for elem in self.elements:
            formatted = elem.format(indent)
            if formatted:
                output.append(formatted)
        return output


@dataclass(frozen=True, slots=True)
class Enum(Node, NonTerminal):
    """An enum definition.

    Examples:
      - enum Status {
          UNKNOWN = 0;
          STARTED = 1;
          COMPLETED = 2;
        }

    """

    name: Ident
    body: EnumBody

    def format(self, indent: int = 0) -> list[str]:
        output = [_indent(f"enum {self.name.format()} {{", indent)]
        output.extend(self.body.format(indent + 2))
        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class MessageElem(Node, NonTerminal):
    """An element in a message body.

    Examples:
      - field
      - oneof
      - nested message
      - enum
      - option statement
      - reserved statement
      - (empty line)

    """

    element: Field | Oneof | Enum | Message | OptionStmt | Reserved | None = None

    def format(self, indent: int = 0) -> list[str]:
        if self.element is None:
            return []
        if isinstance(self.element, OptionStmt):
            return [self.element.format(indent)]
        if isinstance(self.element, Reserved):
            return [_indent(self.element.format() + ";", indent)]
        if isinstance(self.element, Field):
            return [_indent(self.element.format() + ";", indent)]
        # Oneof, Enum, Message return list[str]
        return self.element.format(indent)


@dataclass(frozen=True, slots=True)
class MessageBody(Node, NonTerminal):
    """Body of a message definition.

    Examples:
      - (list of fields, oneofs, nested messages, enums, options, and reserved statements)

    """

    elements: tuple[MessageElem, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        output = []
        for elem in self.elements:
            output.extend(elem.format(indent))
        return output


@dataclass(frozen=True, slots=True)
class Message(Node, NonTerminal):
    """A message definition.

    Examples:
      - message Person {
          string name = 1;
          int32 age = 2;
          repeated string emails = 3;
        }

    """

    name: Ident
    body: MessageBody

    def format(self, indent: int = 0) -> list[str]:
        output = [_indent(f"message {self.name.format()} {{", indent)]
        output.extend(self.body.format(indent + 2))
        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class StreamOption(Node, NonTerminal):
    """Stream option for RPC parameters.

    Examples:
      - stream
      - (nothing)

    """

    stream: bool = False

    def format(self) -> str:
        return "stream " if self.stream else ""


@dataclass(frozen=True, slots=True)
class RpcBodyElem(Node, NonTerminal):
    """An element in an RPC body.

    Examples:
      - option statement
      - (empty line)

    """

    option: OptionStmt | None = None

    def format(self, indent: int = 0) -> str:
        if self.option is None:
            return ""
        return self.option.format(indent)


@dataclass(frozen=True, slots=True)
class RpcBody(Node, NonTerminal):
    """Body of an RPC method.

    Examples:
      - (list of options)

    """

    options: tuple[RpcBodyElem, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        output = []
        for elem in self.options:
            formatted = elem.format(indent)
            if formatted:
                output.append(formatted)
        return output


@dataclass(frozen=True, slots=True)
class Rpc(Node, NonTerminal):
    """An RPC method definition in a service.

    Examples:
      - rpc GetUser (UserId) returns (User);
      - rpc ListItems (stream Request) returns (stream Response);
      - rpc UpdateUser (User) returns (User) {
          option (google.api.http) = { post: "/v1/user" };
        }

    """

    name: Ident
    request: QualifiedName
    response: QualifiedName
    request_stream: StreamOption
    response_stream: StreamOption
    options: RpcBody

    def format(self, indent: int = 0) -> list[str]:
        request_type = f"{self.request_stream.format()}{self.request.format()}"
        response_type = f"{self.response_stream.format()}{self.response.format()}"
        header = _indent(
            f"rpc {self.name.format()} ({request_type}) returns ({response_type})",
            indent
        )

        body_lines = self.options.format(indent + 2)
        if not body_lines:
            return [header + ";"]

        output = [header + " {"]
        output.extend(body_lines)
        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class ServiceElem(Node, NonTerminal):
    """An element in a service body.

    Examples:
      - RPC
      - option statement
      - (empty line)

    """

    element: Rpc | OptionStmt | None = None

    def format(self, indent: int = 0) -> list[str]:
        if self.element is None:
            return []
        if isinstance(self.element, OptionStmt):
            return [self.element.format(indent)]
        return self.element.format(indent)


@dataclass(frozen=True, slots=True)
class ServiceBody(Node, NonTerminal):
    """Body of a service definition.

    Examples:
      - (list of RPCs and options)

    """

    elements: tuple[ServiceElem, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        output = []
        for elem in self.elements:
            output.extend(elem.format(indent))
        return output


@dataclass(frozen=True, slots=True)
class Service(Node, NonTerminal):
    """A service definition.

    Examples:
      - service UserService {
          rpc GetUser (UserId) returns (User);
          rpc ListUsers (ListRequest) returns (ListResponse);
        }

    """

    name: Ident
    body: ServiceBody

    def format(self, indent: int = 0) -> list[str]:
        output = [_indent(f"service {self.name.format()} {{", indent)]
        output.extend(self.body.format(indent + 2))
        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class ProtoItem(Node, NonTerminal):
    """A top-level item in a proto file.

    Examples:
      - syntax statement
      - import statement
      - package statement
      - option statement
      - message
      - enum
      - service
      - (empty line)

    """

    item: Syntax | Import | Package | OptionStmt | Message | Enum | Service | None = None

    def format(self, indent: int = 0) -> list[str]:
        if self.item is None:
            return []
        if isinstance(self.item, (Syntax, Import, Package, OptionStmt)):
            if isinstance(self.item, Syntax):
                return [f'syntax = "{self.item.value}";']
            if isinstance(self.item, Import):
                modifier = f"{self.item.modifier.format()} " if self.item.modifier else ""
                return [f'import {modifier}"{self.item.path.format()}";']
            if isinstance(self.item, Package):
                return [f"package {self.item.name.format()};"]
            return [self.item.format(indent)]
        # Message, Enum, Service return list[str]
        return self.item.format(indent)


@dataclass(frozen=True, slots=True)
class ProtoFile(Node, NonTerminal):
    """A complete proto3 file.

    Examples:
      - syntax = "proto3";

        package com.example;

        import "google/protobuf/timestamp.proto";

        message User {
          string name = 1;
          int32 age = 2;
        }

    """

    items: tuple[ProtoItem, ...] = ()

    @cached_property
    def syntax(self) -> Syntax | None:
        """Extract the syntax declaration from items."""
        for item in self.items:
            if item.item is not None and isinstance(item.item, Syntax):
                return item.item
        return None

    @cached_property
    def imports(self) -> tuple[Import, ...]:
        """Extract all import statements from items."""
        return tuple(
            item.item
            for item in self.items
            if item.item is not None and isinstance(item.item, Import)
        )

    @cached_property
    def package(self) -> Package | None:
        """Extract the package declaration from items."""
        for item in self.items:
            if item.item is not None and isinstance(item.item, Package):
                return item.item
        return None

    def _group_items(self) -> tuple[
        list[ProtoItem], list[ProtoItem], list[ProtoItem], list[ProtoItem]
    ]:
        """Group items by type: syntax, imports, package, and others."""
        syntax_items = []
        import_items = []
        package_items = []
        other_items = []

        for item in self.items:
            if item.item is None:
                continue
            if isinstance(item.item, Syntax):
                syntax_items.append(item)
            elif isinstance(item.item, Import):
                import_items.append(item)
            elif isinstance(item.item, Package):
                package_items.append(item)
            else:
                other_items.append(item)

        return syntax_items, import_items, package_items, other_items

    def _format_item_group(self, items: list[ProtoItem]) -> list[str]:
        """Format a group of items with trailing blank line."""
        output: list[str] = []
        for item in items:
            output.extend(item.format())
        if items:
            output.append("")
        return output

    def format(self) -> str:
        syntax_items, import_items, package_items, other_items = (
            self._group_items()
        )

        output: list[str] = []
        output.extend(self._format_item_group(syntax_items))
        output.extend(self._format_item_group(import_items))
        output.extend(self._format_item_group(package_items))

        # Format other declarations with blank lines between
        for item in other_items:
            output.extend(item.format())
            output.append("")

        # Remove trailing blank lines
        while output and output[-1] == "":
            output.pop()

        return "\n".join(output) + "\n" if output else ""


def _indent(line: str, indent: int) -> str:
    return (" " * indent) + line
