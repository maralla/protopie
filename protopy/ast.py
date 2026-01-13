from dataclasses import dataclass, field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .spans import Span
    from .symbol import Terminal


@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes."""

    span: Span


@dataclass(frozen=True, slots=True)
class QualifiedName(Node):
    """A dotted name, optionally absolute (leading dot in source).

    Examples:
      - foo.bar.Baz
      - .google.protobuf.Timestamp
      - MyMessage

    """

    absolute: bool
    parts: tuple[str, ...]

    def __str__(self) -> str:
        dot = "." if self.absolute else ""
        return dot + ".".join(self.parts)


@dataclass(frozen=True, slots=True)
class Syntax(Node):
    """Syntax declaration statement.

    Examples:
      - syntax = "proto3";

    """

    value: str  # raw string literal content, not unescaped


@dataclass(frozen=True, slots=True)
class Import(Node):
    """Import statement.

    Examples:
      - import "google/protobuf/timestamp.proto";
      - import public "other.proto";
      - import weak "deprecated.proto";

    """

    path: str  # raw string literal content, not unescaped
    modifier: str | None = None  # "weak" | "public" | None


@dataclass(frozen=True, slots=True)
class Package(Node):
    """Package declaration statement.

    Examples:
      - package google.protobuf;
      - package com.example.foo;

    """

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

    def format(self) -> str:
        """Format option name, including custom options."""
        if self.custom:
            base = str(self.base)
            if self.base.absolute:
                base = base[1:]
            suffix = ("." + ".".join(self.suffix)) if self.suffix else ""
            return f"({base}){suffix}"
        return str(self.base)


@dataclass(frozen=True, slots=True)
class Constant(Node):
    """A constant value in proto3.

    Examples:
      - 42 (integer)
      - 3.14 (float)
      - "hello" (string)
      - true / false (boolean)
      - MyEnum.VALUE (identifier)
      - { foo: 1, bar: "baz" } (aggregate/message literal)

    """

    kind: type[Terminal]  # Terminal symbol representing the constant type
    value: int | float | str | bool | QualifiedName

    def format(self) -> str:
        """Format a constant value."""
        kind_name = self.kind.name

        value = "/*unknown-const*/"

        if kind_name == "INT":
            value = str(self.value)

        if kind_name == "FLOAT":
            value = str(self.value)

        if kind_name == "STRING":
            value = '"' + str(self.value).replace('"', '\\"') + '"'

        if kind_name in ("true", "false"):
            value = "true" if self.value else "false"

        if kind_name == "ident":
            value = str(self.value)

        if kind_name == "aggregate":
            fields = []
            for key, value in self.value:
                fields.append(f"{key}: {value.format()}")
            value = "{ " + ", ".join(fields) + " }"

        return value


@dataclass(frozen=True, slots=True)
class Option(Node):
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
class OptionStmt(Node):
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
class FieldOption(Node):
    """A field-level option (used in field definitions).

    Examples:
      - string name = 1 [deprecated = true];
      - int32 id = 2 [json_name = "userId"];

    """

    option: Option


@dataclass(frozen=True, slots=True)
class Field(Node):
    """A field definition in a message or oneof.

    Examples:
      - string name = 1;
      - repeated int32 values = 2;
      - map<string, int32> scores = 3;
      - MyMessage msg = 4 [deprecated = true];

    """

    name: str
    number: int
    type_name: QualifiedName | None = None
    scalar_type: str | None = None
    map_key_type: str | None = None  # only for map<k,v>
    map_value: TypeRef | None = None
    repeated: bool = False
    options: tuple[FieldOption, ...] = ()

    def format(self) -> str:
        """Format a field definition."""
        if self.map_key_type is not None and self.map_value is not None:
            value_type = self.map_value.format()
            type_str = f"map<{self.map_key_type}, {value_type}>"
            label = ""
        else:
            type_str = self._format_type()
            label = "repeated " if self.repeated else ""

        result = f"{label}{type_str} {self.name} = {self.number}"

        if self.options:
            options_str = ", ".join(opt.option.format() for opt in self.options)
            result += f" [{options_str}]"

        return result

    def _format_type(self) -> str:
        """Format the type name of a field."""
        if self.scalar_type is not None:
            return self.scalar_type

        if self.type_name is None:
            return "/*missing-type*/"

        return str(self.type_name)


@dataclass(frozen=True, slots=True)
class TypeRef(Node):
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
class Oneof(Node):
    """A oneof group in a message.

    Examples:
      - oneof test_oneof {
          string name = 1;
          int32 value = 2;
        }

    """

    name: str
    fields: tuple[Field, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        """Format a oneof definition."""
        output = [_indent(f"oneof {self.name} {{", indent)]
        output.extend(_indent(e.format() + ";", indent + 2) for e in self.fields)
        output.append(_indent("}", indent))

        return output


@dataclass(frozen=True, slots=True)
class ReservedRange(Node):
    """A reserved field number range.

    Examples:
      - 2 (single field number)
      - 9 to 11 (range)
      - 15 to max (open-ended range)

    """

    start: int
    end: int | None = None  # inclusive; None means single value
    end_is_max: bool = False

    def format(self) -> str:
        """Format a reserved range."""
        if self.end_is_max:
            return f"{self.start} to max"
        if self.end is None:
            return str(self.start)
        return f"{self.start} to {self.end}"


@dataclass(frozen=True, slots=True)
class Reserved(Node):
    """Reserved field numbers or field names.

    Examples:
      - reserved 2, 15, 9 to 11;
      - reserved "foo", "bar";
      - reserved 1 to max;

    """

    ranges: tuple[ReservedRange, ...] = ()
    names: tuple[str, ...] = ()

    def format(self) -> str:
        """Format a reserved statement."""
        parts = ["reserved"]

        if self.ranges:
            range_strings = [r.format() for r in self.ranges]
            parts.append(", ".join(range_strings))
        else:
            parts.append(", ".join(f'"{name}"' for name in self.names))

        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class EnumValue(Node):
    """An enum value definition.

    Examples:
      - UNKNOWN = 0;
      - STARTED = 1 [deprecated = true];
      - COMPLETED = 2;

    """

    name: str
    number: int
    options: tuple[FieldOption, ...] = ()

    def format(self, indent: int = 0) -> str:
        """Format an enum value."""
        value_str = f"{self.name} = {self.number}"

        if self.options:
            options_str = ", ".join(opt.option.format() for opt in self.options)
            value_str += f" [{options_str}]"

        return _indent(value_str + ";", indent)


@dataclass(frozen=True, slots=True)
class Enum(Node):
    """An enum definition.

    Examples:
      - enum Status {
          UNKNOWN = 0;
          STARTED = 1;
          COMPLETED = 2;
        }

    """

    name: str
    body: tuple[OptionStmt | Reserved | EnumValue | Message | Enum, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        """Format an enum definition."""
        output = [_indent(f"enum {self.name} {{", indent)]

        for element in self.body:
            if isinstance(element, OptionStmt):
                output.append(element.format(indent + 2))

            elif isinstance(element, Reserved):
                output.append(_indent(element.format() + ";", indent + 2))

            elif isinstance(element, EnumValue):
                output.append(element.format(indent + 2))

            elif isinstance(element, (Message, Enum)):
                output.extend(element.format(indent + 2))

            else:
                msg = f"/* unsupported enum element: {type(element).__name__} */"
                output.append(_indent(msg, indent + 2))

        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class Message(Node):
    """A message definition.

    Examples:
      - message Person {
          string name = 1;
          int32 age = 2;
          repeated string emails = 3;
        }

    """

    name: str
    body: tuple[OptionStmt | Reserved | Field | Oneof | Message | Enum, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        """Format a message definition."""
        output = [_indent(f"message {self.name} {{", indent)]

        for element in self.body:
            if isinstance(element, OptionStmt):
                output.append(element.format(indent + 2))

            elif isinstance(element, (Reserved, Field)):
                output.append(_indent(element.format() + ";", indent + 2))

            elif isinstance(element, (Oneof, Enum, Message)):
                output.extend(element.format(indent + 2))

            else:
                msg = f"/* unsupported message element: {type(element).__name__} */"
                output.append(_indent(msg, indent + 2))

        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class Rpc(Node):
    """An RPC method definition in a service.

    Examples:
      - rpc GetUser (UserId) returns (User);
      - rpc ListItems (stream Request) returns (stream Response);
      - rpc UpdateUser (User) returns (User) {
          option (google.api.http) = { post: "/v1/user" };
        }

    """

    name: str
    request: TypeRef
    response: TypeRef
    request_stream: bool = False
    response_stream: bool = False
    options: tuple[OptionStmt, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        """Format an RPC method definition."""
        request_type = self.request.format()
        response_type = self.response.format()

        if self.request_stream:
            request_type = "stream " + request_type

        if self.response_stream:
            response_type = "stream " + response_type

        header = _indent(f"rpc {self.name} ({request_type}) returns ({response_type})", indent)

        if not self.options:
            return [header + ";"]

        output = [header + " {"]
        output.extend(option.format(indent + 2) for option in self.options)

        output.append(_indent("}", indent))
        return output


@dataclass(frozen=True, slots=True)
class Service(Node):
    """A service definition.

    Examples:
      - service UserService {
          rpc GetUser (UserId) returns (User);
          rpc ListUsers (ListRequest) returns (ListResponse);
        }

    """

    name: str
    body: tuple[OptionStmt | Rpc, ...] = ()

    def format(self, indent: int = 0) -> list[str]:
        """Format a service definition."""
        output = [_indent(f"service {self.name} {{", indent)]

        for element in self.body:
            if isinstance(element, OptionStmt):
                output.append(element.format(indent + 2))

            elif isinstance(element, Rpc):
                output.extend(element.format(indent + 2))

            else:
                msg = f"/* unsupported service element: {type(element).__name__} */"
                output.append(_indent(msg, indent + 2))

        output.append(_indent("}", indent))
        return output


TopLevel = Import | Package | OptionStmt | Message | Enum | Service


@dataclass(frozen=True, slots=True)
class ProtoFile(Node):
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

    syntax: Syntax | None = None
    items: tuple[TopLevel, ...] = ()

    # convenience indexes; computed by parser/loader
    imports: tuple[Import, ...] = field(default_factory=tuple)
    package: Package | None = None

    def format(self) -> str:
        """Format the entire proto file."""
        output: list[str] = []

        # Format syntax declaration
        if self.syntax is not None:
            output.append(f'syntax = "{self.syntax.value}";')
            output.append("")

        # Separate items by type
        imports = [item for item in self.items if isinstance(item, Import)]
        package = next((item for item in self.items if isinstance(item, Package)), None)
        declarations = [
            item for item in self.items
            if not isinstance(item, (Import, Package, Syntax))
        ]

        # Format imports
        for import_stmt in imports:
            if import_stmt.modifier:
                output.append(f'import {import_stmt.modifier} "{import_stmt.path}";')
            else:
                output.append(f'import "{import_stmt.path}";')

        if imports:
            output.append("")

        # Format package declaration
        if package is not None:
            output.append(f"package {package.name};")
            output.append("")

        # Format top-level declarations
        for declaration in declarations:
            if isinstance(declaration, OptionStmt):
                output.append(declaration.format(0))

            elif isinstance(declaration, (Message, Enum, Service)):
                output.extend(declaration.format(0))

            else:
                output.append(f"/* unsupported top-level node: {type(declaration).__name__} */")

            output.append("")

        # Remove trailing blank lines
        while output and output[-1] == "":
            output.pop()

        return "\n".join(output) + "\n"


def _indent(line: str, indent: int) -> str:
    return (" " * indent) + line
