import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, get_type_hints, get_origin, get_args

if TYPE_CHECKING:
    from collections.abc import Iterator

from . import ast
from .symbol import Terminal, NonTerminal, Symbol
from .errors import ParseError
from .spans import Span


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class Token(ast.Node, Terminal):
    kind: type[Terminal] = Terminal
    lexeme: str = ""


@dataclass
class Production:
    head: type[NonTerminal]
    body: tuple[Symbol, ...]
    action: Callable[[tuple[Symbol, ...]], NonTerminal]

    def __str__(self) -> str:
        body_str = " ".join(s.symbol_name for s in self.body)
        return f"{self.head.symbol_name} -> {body_str}"


@dataclass
class Grammar:
    start: type[NonTerminal]
    productions: tuple[Production, ...]



class Epsilon:
    """Sentinel representing epsilon (empty production).

    Epsilon represents "nothing" or "empty" in grammar productions.
    It is used both as a type marker in grammar definitions and as a
    sentinel value in FIRST set computations.
    """

    def __repr__(self) -> str:
        return "ε"

    def __bool__(self) -> bool:
        return False  # Epsilon is "empty", acts like False

    def __len__(self) -> int:
        return 0  # Epsilon has no length

    def __getitem__(self, index: object) -> None:
        raise TypeError("Epsilon (ε) cannot be indexed")

    def __iter__(self) -> Iterator[None]:
        return iter(())

# Sentinel instance - use this everywhere
EPSILON = Epsilon()

# Constant kind markers (for ast.Constant.kind field)
class CONST_IDENT(Token, name="ident"): pass
class CONST_AGGREGATE(Token, name="aggregate"): pass

# Literal tokens
class IDENT(Token, name="IDENT"): pass
class INT(Token, name="INT"): pass
class FLOAT(Token, name="FLOAT"): pass
class STRING(Token, name="STRING"): pass

# Keywords
class SYNTAX(Token, name="syntax"): pass
class IMPORT(Token, name="import"): pass
class WEAK(Token, name="weak"): pass
class PUBLIC(Token, name="public"): pass
class PACKAGE(Token, name="package"): pass
class OPTION(Token, name="option"): pass
class REPEATED(Token, name="repeated"): pass
class ONEOF(Token, name="oneof"): pass
class MAP(Token, name="map"): pass
class RESERVED(Token, name="reserved"): pass
class TO(Token, name="to"): pass
class MAX(Token, name="max"): pass
class ENUM(Token, name="enum"): pass
class MESSAGE(Token, name="message"): pass
class SERVICE(Token, name="service"): pass
class RPC(Token, name="rpc"): pass
class RETURNS(Token, name="returns"): pass
class STREAM(Token, name="stream"): pass

# Punctuation
class SEMI(Token, name=";"): pass
class COMMA(Token, name=","): pass
class DOT(Token, name="."): pass
class EQ(Token, name="="): pass
class COLON(Token, name=":"): pass
class SLASH(Token, name="/"): pass
class LPAREN(Token, name="("): pass
class RPAREN(Token, name=")"): pass
class LBRACE(Token, name="{"): pass
class RBRACE(Token, name="}"): pass
class LBRACKET(Token, name="["): pass
class RBRACKET(Token, name="]"): pass
class LANGLE(Token, name="<"): pass
class RANGLE(Token, name=">"): pass

# Constants / booleans
class TRUE(Token, name="true"): pass
class FALSE(Token, name="false"): pass
class EOF(Token, name="EOF"): pass

# Keyword dictionary
KEYWORDS = {
    s.name: s for s in {
        SYNTAX, IMPORT, WEAK, PUBLIC, PACKAGE, OPTION, REPEATED, ONEOF,
        MAP, RESERVED, TO, MAX, ENUM, MESSAGE, SERVICE, RPC, RETURNS,
        STREAM, TRUE, FALSE,
    }
}

# Punctuation dictionary
PUNCTUATION = {
    s.name: s for s in {
        SEMI, COMMA, DOT, EQ, COLON, SLASH, LPAREN, RPAREN,
        LBRACE, RBRACE, LBRACKET, RBRACKET, LANGLE, RANGLE,
    }
}


# Scalar type constants
SCALAR_DOUBLE = "double"
SCALAR_FLOAT = "float"
SCALAR_INT32 = "int32"
SCALAR_INT64 = "int64"
SCALAR_UINT32 = "uint32"
SCALAR_UINT64 = "uint64"
SCALAR_SINT32 = "sint32"
SCALAR_SINT64 = "sint64"
SCALAR_FIXED32 = "fixed32"
SCALAR_FIXED64 = "fixed64"
SCALAR_SFIXED32 = "sfixed32"
SCALAR_SFIXED64 = "sfixed64"
SCALAR_BOOL = "bool"
SCALAR_STRING = "string"
SCALAR_BYTES = "bytes"

SCALAR_TYPES = frozenset([
    SCALAR_DOUBLE,
    SCALAR_FLOAT,
    SCALAR_INT32,
    SCALAR_INT64,
    SCALAR_UINT32,
    SCALAR_UINT64,
    SCALAR_SINT32,
    SCALAR_SINT64,
    SCALAR_FIXED32,
    SCALAR_FIXED64,
    SCALAR_SFIXED32,
    SCALAR_SFIXED64,
    SCALAR_BOOL,
    SCALAR_STRING,
    SCALAR_BYTES,
])

MAP_KEY_TYPES = frozenset([
    SCALAR_INT32,
    SCALAR_INT64,
    SCALAR_UINT32,
    SCALAR_UINT64,
    SCALAR_SINT32,
    SCALAR_SINT64,
    SCALAR_FIXED32,
    SCALAR_FIXED64,
    SCALAR_SFIXED32,
    SCALAR_SFIXED64,
    SCALAR_BOOL,
    SCALAR_STRING,
])


class GrammarExtractor:
    """Extracts grammar productions from annotated methods."""

    def __init__(self) -> None:
        self.productions: list[Production] = []

    def _extract_from_values_type(
        self,
        values_type: object,
        head: type[NonTerminal],
        func: Callable[[tuple[Symbol, ...]], NonTerminal],
    ) -> list[Production]:
        """Recursively extract productions from a values type annotation."""
        # Handle epsilon productions: values: Epsilon
        if values_type is Epsilon:
            return [Production(head=head, body=(), action=func)]

        origin_type = get_origin(values_type)

        # Handle union at top level: tuple[A, B] | Epsilon
        if origin_type is Union:
            productions = []
            for alt in get_args(values_type):
                productions.extend(
                    self._extract_from_values_type(alt, head, func),
                )
            return productions

        # Handle tuple types
        if origin_type is not tuple:
            return []  # We only support tuple

        body_types = get_args(values_type)

        # Empty tuple means epsilon
        if not body_types:
            return [Production(head=head, body=(), action=func)]

        # Convert body_types to list of alternatives
        # tuple[NT, T | NT | NT, T]
        #   body_types -> [NT1, T1 | NT2 | NT3, T2]
        #   H: NT1 T1 T2
        #   H: NT1 NT2 T2
        #   H: NT1 NT3 T2
        # Now converts to types = [[sym1], [sym1, sym2, sym3], [sym2]].
        # Then we get all productions by itertools.product(*types)
        types: list[list[Symbol]] = []
        for body_type in body_types:
            origin = get_origin(body_type)
            if origin is Union:
                # Union: extract symbols from all alternatives
                types.append(list(get_args(body_type)))
            else:
                # Single type: extract symbol
                types.append([body_type])

        return [
            Production(head=head, body=tuple(combo), action=func)
            for combo in itertools.product(*types)
        ]

    def extract_from_function(self, func: Callable[[tuple[Symbol, ...]], NonTerminal]) -> list[Production]:
        """Extract production rule(s) from a function's type annotations.

        Can return multiple productions if values contains a union type.
        Returns empty list if the function doesn't have the right annotations.
        """
        try:
            hints = get_type_hints(
                func, globalns=globals(), include_extras=True)
        except Exception:
            return []

        if 'return' not in hints or 'values' not in hints:
            return []

        # Extract head from return type
        raw_return = func.__annotations__.get('return')
        if not raw_return or not raw_return.is_nonterminal():
            return []

        # The symbol class itself is the head
        head = raw_return

        # Extract body from values parameter
        values_type = hints['values']

        return self._extract_from_values_type(values_type, head, func)

    def extract_from_class(self, cls: type) -> list[Production]:
        """Extract all productions from a class with annotated methods."""
        for name in dir(cls):
            if name.startswith('act_'):
                attr = getattr(cls, name)
                if callable(attr):
                    prods = self.extract_from_function(attr)
                    self.productions.extend(prods)

        return self.productions


# ============================================================================
# Helper functions (for semantic actions)
# ============================================================================

def join_span(*values: ast.Node) -> Span:
    """Join the spans of multiple values into a single span."""
    if not values:
        raise ValueError("join_span requires at least one value")
    return Span(
        file=values[0].span.file,
        start=values[0].span.start,
        end=values[-1].span.end,
    )


# ============================================================================
# Grammar builder with semantic actions
# ============================================================================
# ruff: noqa: E501
class GrammarBuilder:
    """Proto3 grammar definition using type-annotation-driven productions.

    Each act_* method defines a production rule through its type annotations:
    - Parameter type: tuple of RHS symbols (Terminal/NonTerminal instances)
    - Return type: NonTerminal[ActualType] indicating LHS (e.g., QualifiedName[ast.QualifiedName])
    """

    _cache: Grammar | None = None

    # -----------------------------------------------------------------------
    # Semantic actions: Constants
    # -----------------------------------------------------------------------

    @staticmethod
    def act_primitive_const(values: tuple[INT | FLOAT | STRING | TRUE | FALSE]) -> ast.PrimitiveConstant:
        value = values[0]
        return ast.PrimitiveConstant(span=value.span, kind=value.kind, value=value.lexeme)

    @staticmethod
    def act_const(values: tuple[ast.PrimitiveConstant | ast.QualifiedName | ast.MessageConstant]) -> ast.Constant:
        value = values[0]
        return ast.Constant(span=value.span, value=value)

    # -----------------------------------------------------------------------
    # Semantic actions: Qualified names
    # -----------------------------------------------------------------------

    @staticmethod
    def act_ident(values: tuple[IDENT | SYNTAX]) -> ast.Ident:
        value = values[0]
        return ast.Ident(span=value.span, text=values[0].lexeme)

    @staticmethod
    def act_dotted_name_eps(values: Epsilon) -> ast.DottedName:
        _ = values
        return ast.DottedName(span=Span.empty())

    @staticmethod
    def act_dotted_name(values: tuple[DOT, ast.Ident, ast.DottedName]) -> ast.DottedName:
        ident = values[1]
        name = values[2]
        return ast.DottedName(span=join_span(values[0], name), parts=(ident, *name.parts))

    @staticmethod
    def act_qualified_name_absolute(values: tuple[DOT, ast.Ident, ast.DottedName]) -> ast.QualifiedName:
        ident = values[1]
        name = values[2]

        dotted_span = join_span(ident, name) if name.parts else ident.span
        return ast.QualifiedName(
            span=join_span(values[0], name if name.parts else ident),
            absolute=True,
            name=ast.DottedName(span=dotted_span, parts=(ident, *name.parts))
        )

    @staticmethod
    def act_qualified_name_relative(values: tuple[ast.Ident, ast.DottedName]) -> ast.QualifiedName:
        ident = values[0]
        name = values[1]

        span = join_span(ident, name) if name.parts else ident.span
        return ast.QualifiedName(
            span=span,
            absolute=False,
            name=ast.DottedName(span=span, parts=(ident, *name.parts))
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Message constant
    # -----------------------------------------------------------------------

    @staticmethod
    def act_message_field_literal(values: tuple[ast.Ident, COLON, ast.Constant]) -> ast.MessageField:
        name: ast.Ident = values[0]
        const: ast.Constant = values[2]
        return ast.MessageField(span=join_span(name, const), name=name, value=const)

    @staticmethod
    def act_message_field_literal_eps(values: Epsilon) -> ast.MessageFields:
        _ = values
        return ast.MessageFields(span=Span.empty())

    @staticmethod
    def act_message_field_literal_single(values: tuple[ast.MessageField]) -> ast.MessageFields:
        field = values[0]
        return ast.MessageFields(span=field.span, fields=(field,))

    @staticmethod
    def act_message_field_literals(values: tuple[ast.MessageField, COMMA, ast.MessageFields]) -> ast.MessageFields:
        field = values[0]
        value = values[2]

        return ast.MessageFields(span=join_span(field, value), fields=(field, *value.fields))

    @staticmethod
    def act_message_constant(values: tuple[LBRACE, ast.MessageFields, RBRACE]) -> ast.MessageConstant:
        return ast.MessageConstant(span=join_span(values[0], values[2]), value=values[1])

    # -----------------------------------------------------------------------
    # Semantic actions: Options
    # -----------------------------------------------------------------------

    @staticmethod
    def act_option_suffix_eps(values: Epsilon) -> ast.OptionSuffix:
        _ = values
        return ast.OptionSuffix(span=Span.empty())

    @staticmethod
    def act_option_suffix(values: tuple[DOT, ast.Ident, ast.OptionSuffix]) -> ast.OptionSuffix:
        ident = values[1]
        suffix = values[2]
        return ast.OptionSuffix(span=join_span(values[0], suffix), items=(ident, *suffix.items))

    @staticmethod
    def act_option_name_custom(values: tuple[LPAREN, ast.QualifiedName, RPAREN, ast.OptionSuffix]) -> ast.OptionName:
        qname = values[1]
        suffix = values[3]
        span_end = suffix if suffix.items else values[2]
        return ast.OptionName(
            span=join_span(values[0], span_end),
            custom=True,
            base=qname,
            suffix=suffix,
        )

    @staticmethod
    def act_option_name_plain(values: tuple[ast.QualifiedName]) -> ast.OptionName:
        value = values[0]
        return ast.OptionName(
            span=value.span,
            custom=False,
            base=value,
        )

    @staticmethod
    def act_option(values: tuple[ast.OptionName, EQ, ast.Constant]) -> ast.Option:
        name: ast.OptionName = values[0]
        const: ast.Constant = values[2]

        return ast.Option(
            span=join_span(name, const),
            name=name, value=const
        )

    @staticmethod
    def act_option_statement(values: tuple[OPTION, ast.Option, SEMI]) -> ast.OptionStmt:
        return ast.OptionStmt(span=join_span(values[0], values[2]), option=values[1])

    # -----------------------------------------------------------------------
    # Semantic actions: Top-level statements
    # -----------------------------------------------------------------------

    @staticmethod
    def act_syntax_statement(values: tuple[SYNTAX, EQ, STRING, SEMI]) -> ast.Syntax:
        literal = values[2].lexeme
        if literal != "proto3":
            raise ParseError(
                span=values[2].span,
                message="only proto3 syntax is supported",
                hint='use: syntax = "proto3";'
            )

        return ast.Syntax(
            span=join_span(values[0], values[3]), value=literal
        )

    @staticmethod
    def act_import_simple(values: tuple[IMPORT, STRING, SEMI]) -> ast.Import:
        value = values[1]
        path = ast.Ident(span=value.span, text=value.lexeme)
        return ast.Import(span=join_span(values[0], values[2]), path=path)

    @staticmethod
    def act_import_statement(values: tuple[IMPORT, WEAK | PUBLIC, STRING, SEMI]) -> ast.Import:
        value = values[2]
        path = ast.Ident(span=value.span, text=value.lexeme)

        modifier_value = values[1]
        modifier = ast.Ident(span=modifier_value.span, text=modifier_value.name)

        return ast.Import(
            span=join_span(values[0], values[3]),
            path=path, modifier=modifier
        )

    @staticmethod
    def act_package_statement(values: tuple[PACKAGE, ast.QualifiedName, SEMI]) -> ast.Package:
        return ast.Package(
            span=join_span(values[0], values[2]), name=values[1]
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Field options
    # -----------------------------------------------------------------------

    @staticmethod
    def act_field_option_eps(values: Epsilon) -> ast.FieldOptionItems:
        _ = values
        return  ast.FieldOptionItems(span=Span.empty())

    @staticmethod
    def act_field_option_single(values: tuple[ast.Option]) -> ast.FieldOptionItems:
        option = values[0]
        return ast.FieldOptionItems(span=option.span, value=(option,))

    @staticmethod
    def act_field_option_items(values: tuple[ast.Option, COMMA, ast.FieldOptionItems]) -> ast.FieldOptionItems:
        option = values[0]
        options = values[2]

        last = options if options.value else values[1]
        return ast.FieldOptionItems(span=join_span(option, last), value=(option, *options.value))

    @staticmethod
    def act_field_options_eps(values: Epsilon) -> ast.FieldOptions:
        _ = values
        return ast.FieldOptions(span=Span.empty())

    @staticmethod
    def act_field_options(values: tuple[LBRACKET, ast.FieldOptionItems, RBRACKET]) -> ast.FieldOptions:
        return ast.FieldOptions(span=join_span(values[0], values[2]), items=values[1])

    # -----------------------------------------------------------------------
    # Semantic actions: Types
    # -----------------------------------------------------------------------

    @staticmethod
    def act_map_key(values: tuple[ast.Ident]) -> ast.MapKeyType:
        ident = values[0]
        return ast.MapKeyType(span=ident.span, ident=ident)

    @staticmethod
    def act_map_type(values: tuple[MAP, LANGLE, ast.MapKeyType, COMMA, ast.QualifiedName, RANGLE]) -> ast.MapType:
        key_type: ast.MapKeyType = values[2]
        value_type: ast.QualifiedName = values[4]
        return ast.MapType(span=join_span(values[0], values[5]), key_type=key_type, value_type=value_type)

    @staticmethod
    def act_field_label_eps(values: Epsilon) -> ast.FieldLabel:
        _ = values
        return ast.FieldLabel(span=Span.empty(), repeated=False)

    @staticmethod
    def act_field_label(values: tuple[REPEATED]) -> ast.FieldLabel:
        return ast.FieldLabel(span=values[0].span, repeated=True)

    # -----------------------------------------------------------------------
    # Semantic actions: Message field
    # -----------------------------------------------------------------------

    @staticmethod
    def act_message_field(
        values: tuple[
            ast.FieldLabel,
            ast.QualifiedName | ast.MapType,
            ast.Ident,
            EQ,
            INT,
            ast.FieldOptions,
            SEMI,
        ]
    ) -> ast.Field:
        number = ast.PrimitiveConstant(span=values[4].span, kind=INT, value=values[4].lexeme)

        field_label = values[0]
        field_type = values[1]
        start = field_label if field_label.none else field_type

        return ast.Field(
            span=join_span(start, values[6]),
            name=values[2],
            number=number,
            field_type=field_type,
            label=field_label,
            options=values[5],
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Oneof
    # -----------------------------------------------------------------------

    @staticmethod
    def act_oneof_field(
        values: tuple[ast.QualifiedName, ast.Ident, EQ, INT, ast.FieldOptions, SEMI]
    ) -> ast.OneofField:
        field = ast.Field(
            span=join_span(values[0], values[5]),
            name=values[1],
            number=ast.PrimitiveConstant(span=values[3].span, kind=INT, value=values[3].lexeme),
            field_type=values[0],
            label=ast.FieldLabel(span=Span.empty(), none=True),
            options=values[4]
        )

        return ast.OneofField(span=field.span, field=field)

    @staticmethod
    def act_oneof_field_empty(values: tuple[SEMI]) -> ast.OneofField:
        return ast.OneofField(span=values[0].span)

    @staticmethod
    def act_oneof_body_eps(values: Epsilon) -> ast.OneofBody:
        _ = values
        return ast.OneofBody(span=Span.empty())

    @staticmethod
    def act_oneof_body(values: tuple[ast.OneofField, ast.OneofBody]) -> ast.OneofBody:
        field = values[0]
        body = values[1]

        last = body if body.fields else field

        return ast.OneofBody(span=join_span(field, last), fields=(field, *body.fields))

    @staticmethod
    def act_oneof(values: tuple[ONEOF, IDENT, LBRACE, ast.OneofBody, RBRACE]) -> ast.Oneof:
        return ast.Oneof(
            span=join_span(values[0], values[4]),
            name=ast.Ident(span=values[1].span, text=values[1].lexeme),
            body=values[3],
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Reserved
    # -----------------------------------------------------------------------

    @staticmethod
    def act_reserved_single(values: tuple[INT]) -> ast.ReservedRange:
        tok: Token = values[0]
        return ast.ReservedRange(
            span=tok.span,
            start=ast.PrimitiveConstant(span=tok.span, kind=INT, value=tok.lexeme)
        )

    @staticmethod
    def act_reserved_range(values: tuple[INT, TO, INT]) -> ast.ReservedRange:
        start: Token = values[0]
        end: Token = values[2]

        return ast.ReservedRange(
            span=join_span(start, end),
            start=ast.PrimitiveConstant(span=start.span, kind=INT, value=start.lexeme),
            end=ast.PrimitiveConstant(span=end.span, kind=INT, value=end.lexeme)
        )

    @staticmethod
    def act_reserved_range_max(values: tuple[INT, TO, MAX]) -> ast.ReservedRange:
        start = values[0]
        end = values[2]
        return ast.ReservedRange(
            span=join_span(start, end),
            start=ast.PrimitiveConstant(span=start.span, kind=INT, value=start.lexeme),
            end=ast.Ident(span=end.span, text=end.name)
        )

    @staticmethod
    def act_reserved_ranges_eps(values: Epsilon) -> ast.RangeCollector:
        _ = values
        return ast.RangeCollector(span=Span.empty())

    @staticmethod
    def act_reserved_ranges_tail(values: tuple[COMMA, ast.ReservedRange, ast.RangeCollector]) -> ast.RangeCollector:
        collected = values[2]
        last = collected if collected.ranges else values[1]
        return ast.RangeCollector(span=join_span(values[0], last), ranges=(values[1], *values[2].ranges))

    @staticmethod
    def act_reserved_ranges(values: tuple[ast.ReservedRange, ast.RangeCollector]) -> ast.ReservedRanges:
        range_item = values[0]
        collected = values[1]

        last = collected if collected.ranges else range_item
        return ast.ReservedRanges(span=join_span(range_item, last), ranges=(range_item, *collected.ranges))

    @staticmethod
    def act_reserved_names_eps(values: Epsilon) -> ast.NameCollector:
        _ = values
        return ast.NameCollector(span=Span.empty())

    @staticmethod
    def act_reserved_names_tail(values: tuple[COMMA, STRING, ast.NameCollector]) -> ast.NameCollector:
        token = values[1]
        collected = values[2]
        last = collected if collected.names else token
        return ast.NameCollector(
            span=join_span(values[0], last),
            names=(ast.Ident(span=token.span, text=token.lexeme), *values[2].names)
        )

    @staticmethod
    def act_reserved_names(values: tuple[STRING, ast.NameCollector]) -> ast.ReservedNames:
        token = values[0]
        collected = values[1]

        last = collected if collected.names else token
        return ast.ReservedNames(
            span=join_span(token, last),
            names=(ast.Ident(span=token.span, text=token.lexeme), *collected.names)
        )

    @staticmethod
    def act_reserved_spec_ranges(values: tuple[ast.ReservedRanges]) -> ast.ReservedSpec:
        ranges = values[0]
        return ast.ReservedSpec(span=ranges.span, ranges=ranges)

    @staticmethod
    def act_reserved_spec_names(values: tuple[ast.ReservedNames]) -> ast.ReservedSpec:
        names = values[0]
        return ast.ReservedSpec(span=names.span, names=names)

    @staticmethod
    def act_reserved_statement(values: tuple[RESERVED, ast.ReservedSpec, SEMI]) -> ast.Reserved:
        return ast.Reserved(
            span=join_span(values[0], values[2]),
            spec=values[1]
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Enum
    # -----------------------------------------------------------------------

    @staticmethod
    def act_enum_value(values: tuple[ast.Ident, EQ, INT, ast.FieldOptions, SEMI]) -> ast.EnumValue:
        name: ast.Ident = values[0]
        number: Token = values[2]

        return ast.EnumValue(
            span=join_span(name, values[4]),
            name=name,
            number=ast.PrimitiveConstant(span=number.span, kind=INT, value=number.lexeme),
            options=values[3],
        )

    @staticmethod
    def act_enum_elem_empty(values: tuple[SEMI]) -> ast.EnumElem:
        return ast.EnumElem(span=values[0].span)

    @staticmethod
    def act_enum_elem(values: tuple[ast.EnumValue | ast.OptionStmt | ast.Reserved]) -> ast.EnumElem:
        element = values[0]
        return ast.EnumElem(span=element.span, element=element)

    @staticmethod
    def act_enum_body_eps(values: Epsilon) -> ast.EnumBody:
        _ = values
        return ast.EnumBody(span=Span.empty())

    @staticmethod
    def act_enum_body(values: tuple[ast.EnumElem, ast.EnumBody]) -> ast.EnumBody:
        elem = values[0]
        body = values[1]

        last = body if body.elements else elem
        return ast.EnumBody(span=join_span(elem, last), elements=(elem, *body.elements))

    @staticmethod
    def act_enum(values: tuple[ENUM, ast.Ident, LBRACE, ast.EnumBody, RBRACE]) -> ast.Enum:
        return ast.Enum(span=join_span(values[0], values[4]), name=values[1], body=values[3])

    # -----------------------------------------------------------------------
    # Semantic actions: Message
    # -----------------------------------------------------------------------

    @staticmethod
    def act_message_elem_empty(values: tuple[SEMI]) -> ast.MessageElem:
        return ast.MessageElem(span=values[0].span)

    @staticmethod
    def act_message_elem(
        values: tuple[ast.Field | ast.Oneof | ast.Enum | ast.Message | ast.OptionStmt | ast.Reserved]
    ) -> ast.MessageElem:
        element = values[0]
        return ast.MessageElem(span=element.span, element=element)

    @staticmethod
    def act_message_body_eps(values: Epsilon) -> ast.MessageBody:
        _ = values
        return ast.MessageBody(span=Span.empty())

    @staticmethod
    def act_message_body(values: tuple[ast.MessageElem, ast.MessageBody]) -> ast.MessageBody:
        elem = values[0]
        body = values[1]

        last = body if body.elements else elem
        return ast.MessageBody(span=join_span(elem, last), elements=(elem, *body.elements))


    @staticmethod
    def act_message(values: tuple[MESSAGE, ast.Ident, LBRACE, ast.MessageBody, RBRACE]) -> ast.Message:
        return ast.Message(span=join_span(values[0], values[4]), name=values[1], body=values[3])

    # -----------------------------------------------------------------------
    # Semantic actions: RPC and Service
    # -----------------------------------------------------------------------

    @staticmethod
    def act_is_stream_eps(values: Epsilon) -> ast.StreamOption:
        _ = values
        return ast.StreamOption(span=Span.empty())

    @staticmethod
    def act_is_stream(values: tuple[STREAM]) -> ast.StreamOption:
        return ast.StreamOption(span=values[0].span, stream=True)

    @staticmethod
    def act_rpc_body_elem_empty(values: tuple[SEMI]) -> ast.RpcBodyElem:
        return ast.RpcBodyElem(span=values[0].span)

    @staticmethod
    def act_rpc_body_elem(values: tuple[ast.OptionStmt]) -> ast.RpcBodyElem:
        option = values[0]
        return ast.RpcBodyElem(span=option.span, option=option)

    @staticmethod
    def act_rpc_body_empty(values: tuple[SEMI]) -> ast.RpcBody:
        return ast.RpcBody(span=values[0].span)

    @staticmethod
    def act_rpc_body_eps(values: Epsilon) -> ast.RpcBody:
        _ = values
        return ast.RpcBody(span=Span.empty())

    @staticmethod
    def act_rpc_body(values: tuple[ast.RpcBodyElem, ast.RpcBody]) -> ast.RpcBody:
        elem = values[0]
        body = values[1]

        last = body if body.options else elem
        return ast.RpcBody(span=join_span(elem, last), options=(elem, *body.options))

    @staticmethod
    def act_rpc_body_block(values: tuple[LBRACE, ast.RpcBody, RBRACE]) -> ast.RpcBody:
        body = values[1]
        return ast.RpcBody(span=join_span(values[0], values[-1]), options=tuple(body.options))

    @staticmethod
    def act_rpc(
        values: tuple[
            RPC,
            ast.Ident,
            LPAREN,
            ast.StreamOption,
            ast.QualifiedName,
            RPAREN,
            RETURNS,
            LPAREN,
            ast.StreamOption,
            ast.QualifiedName,
            RPAREN,
            ast.RpcBody,
        ]
    ) -> ast.Rpc:
        body: ast.RpcBody = values[11]
        last = body if body.options else values[10]

        return ast.Rpc(
            span=join_span(values[0], last),
            name=values[1],
            request=values[4],
            response=values[9],
            request_stream=values[3],
            response_stream=values[8],
            options=body
        )

    @staticmethod
    def act_service_elem_empty(values: tuple[SEMI]) -> ast.ServiceElem:
        return ast.ServiceElem(span=values[0].span)

    @staticmethod
    def act_service_elem(values: tuple[ast.Rpc | ast.OptionStmt]) -> ast.ServiceElem:
        element = values[0]
        return ast.ServiceElem(span=element.span, element=element)

    @staticmethod
    def act_service_body_eps(values: Epsilon) -> ast.ServiceBody:
        _ = values
        return ast.ServiceBody(span=Span.empty())

    @staticmethod
    def act_service_body(values: tuple[ast.ServiceElem, ast.ServiceBody]) -> ast.ServiceBody:
        elem = values[0]
        body = values[1]

        last = body if body.elements else elem
        return ast.ServiceBody(span=join_span(elem, last), elements=(elem, *body.elements))

    @staticmethod
    def act_service(values: tuple[SERVICE, ast.Ident, LBRACE, ast.ServiceBody, RBRACE]) -> ast.Service:
        return ast.Service(span=join_span(values[0], values[4]), name=values[1], body=values[3])

    # -----------------------------------------------------------------------
    # Semantic actions: File (top-level)
    # -----------------------------------------------------------------------

    @staticmethod
    def act_item_empty(values: tuple[SEMI]) -> ast.ProtoItem:
        return ast.ProtoItem(span=values[0].span)

    @staticmethod
    def act_item(
        values: tuple[ast.Syntax | ast.Import | ast.Package | ast.OptionStmt | ast.Message | ast.Enum | ast.Service]
    ) -> ast.ProtoItem:
        item = values[0]
        return ast.ProtoItem(span=item.span, item=item)

    @staticmethod
    def act_file_eps(values: Epsilon) -> ast.ProtoFile:
        _ = values
        return ast.ProtoFile(span=Span.empty())

    @staticmethod
    def act_file(values: tuple[ast.ProtoItem, ast.ProtoFile]) -> ast.ProtoFile:
        elem = values[0]
        body = values[1]

        last = body if body.items else elem
        return ast.ProtoFile(span=join_span(elem, last), items=(elem, *body.items))

    @classmethod
    def build(cls) -> Grammar:
        """Build and cache the proto3 grammar."""
        if cls._cache is not None:
            return cls._cache

        extractor = GrammarExtractor()
        productions = extractor.extract_from_class(cls)

        cls._cache = Grammar(start=ast.ProtoFile, productions=tuple(productions))
        return cls._cache
