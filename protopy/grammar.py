import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, get_type_hints, get_origin, get_args, Generic, TypeVar

T = TypeVar('T')

if TYPE_CHECKING:
    from collections.abc import Iterator

from . import ast
from .symbol import Terminal, NonTerminal, Symbol
from .errors import ParseError
from .spans import Position, Span


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class Token:
    kind: type[Terminal]
    lexeme: str
    span: Span

    def to_constant(self) -> ast.Constant:
        value: int | float | str | bool

        if self.kind is INT:
            value = int(self.lexeme)
        elif self.kind is FLOAT:
            value = float(self.lexeme)
        elif self.kind is STRING:
            value = self.lexeme
        elif self.kind is TRUE:
            value = True
        elif self.kind is FALSE:
            value = False
        else:
            raise ValueError(f"Cannot convert {self.kind} to Constant")

        return ast.Constant(span=self.span, kind=self.kind, value=value)


@dataclass
class Production:
    head: type[NonTerminal]
    body: tuple[Symbol, ...]
    action: Callable[[tuple[object, ...]], object]

    def __str__(self) -> str:
        body_str = " ".join(s.name for s in self.body)
        return f"{self.head.name} -> {body_str}"


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
class CONST_IDENT(Terminal, name="ident"): pass
class CONST_AGGREGATE(Terminal, name="aggregate"): pass

# Literal tokens
class IDENT(Terminal, name="IDENT"): pass
class INT(Terminal, name="INT"): pass
class FLOAT(Terminal, name="FLOAT"): pass
class STRING(Terminal, name="STRING"): pass

# Keywords
class SYNTAX(Terminal, name="syntax"): pass
class IMPORT(Terminal, name="import"): pass
class WEAK(Terminal, name="weak"): pass
class PUBLIC(Terminal, name="public"): pass
class PACKAGE(Terminal, name="package"): pass
class OPTION(Terminal, name="option"): pass
class REPEATED(Terminal, name="repeated"): pass
class ONEOF(Terminal, name="oneof"): pass
class MAP(Terminal, name="map"): pass
class RESERVED(Terminal, name="reserved"): pass
class TO(Terminal, name="to"): pass
class MAX(Terminal, name="max"): pass
class ENUM(Terminal, name="enum"): pass
class MESSAGE(Terminal, name="message"): pass
class SERVICE(Terminal, name="service"): pass
class RPC(Terminal, name="rpc"): pass
class RETURNS(Terminal, name="returns"): pass
class STREAM(Terminal, name="stream"): pass

# Punctuation
class SEMI(Terminal, name=";"): pass
class COMMA(Terminal, name=","): pass
class DOT(Terminal, name="."): pass
class EQ(Terminal, name="="): pass
class COLON(Terminal, name=":"): pass
class SLASH(Terminal, name="/"): pass
class LPAREN(Terminal, name="("): pass
class RPAREN(Terminal, name=")"): pass
class LBRACE(Terminal, name="{"): pass
class RBRACE(Terminal, name="}"): pass
class LBRACKET(Terminal, name="["): pass
class RBRACKET(Terminal, name="]"): pass
class LANGLE(Terminal, name="<"): pass
class RANGLE(Terminal, name=">"): pass

# Constants / booleans
class TRUE(Terminal, name="true"): pass
class FALSE(Terminal, name="false"): pass
class EOF(Terminal, name="EOF"): pass

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


T = TypeVar('T')


# NonTerminal symbols
class File(NonTerminal, Generic[T]): pass
class Items(NonTerminal, Generic[T]): pass
class Item(NonTerminal, Generic[T]): pass
class Decl(NonTerminal, Generic[T]): pass
class Ident(NonTerminal, Generic[T]): pass
class NameTail(NonTerminal, Generic[T]): pass
class QualifiedName(NonTerminal, Generic[T]): pass
class SyntaxStmt(NonTerminal, Generic[T]): pass
class ImportStmt(NonTerminal, Generic[T]): pass
class ImportModOpt(NonTerminal, Generic[T]): pass
class PackageStmt(NonTerminal, Generic[T]): pass
class OptionStmt(NonTerminal, Generic[T]): pass
class Option(NonTerminal, Generic[T]): pass
class OptionName(NonTerminal, Generic[T]): pass
class OptionSuffix(NonTerminal, Generic[T]): pass
class Const(NonTerminal, Generic[T]): pass
class OptComma(NonTerminal, Generic[T]): pass
class AggField(NonTerminal, Generic[T]): pass
class AggFields(NonTerminal, Generic[T]): pass
class AggFieldsTail(NonTerminal, Generic[T]): pass
class AggFieldsOpt(NonTerminal, Generic[T]): pass
class Aggregate(NonTerminal, Generic[T]): pass
class FieldOption(NonTerminal, Generic[T]): pass
class FieldOptionList(NonTerminal, Generic[T]): pass
class FieldOptionListTail(NonTerminal, Generic[T]): pass
class FieldOptions(NonTerminal, Generic[T]): pass
class MapValueType(NonTerminal, Generic[T]): pass
class MapKeyType(NonTerminal, Generic[T]): pass
class MapType(NonTerminal, Generic[T]): pass
class FieldLabel(NonTerminal, Generic[T]): pass
class Field(NonTerminal, Generic[T]): pass
class OneofField(NonTerminal, Generic[T]): pass
class OneofElem(NonTerminal, Generic[T]): pass
class OneofBody(NonTerminal, Generic[T]): pass
class Oneof(NonTerminal, Generic[T]): pass
class ReservedRange(NonTerminal, Generic[T]): pass
class ReservedRangesTail(NonTerminal, Generic[T]): pass
class ReservedRanges(NonTerminal, Generic[T]): pass
class ReservedNamesTail(NonTerminal, Generic[T]): pass
class ReservedNames(NonTerminal, Generic[T]): pass
class ReservedSpec(NonTerminal, Generic[T]): pass
class ReservedStmt(NonTerminal, Generic[T]): pass
class EnumValue(NonTerminal, Generic[T]): pass
class EnumElem(NonTerminal, Generic[T]): pass
class EnumBody(NonTerminal, Generic[T]): pass
class Enum(NonTerminal, Generic[T]): pass
class MessageElem(NonTerminal, Generic[T]): pass
class MessageBody(NonTerminal, Generic[T]): pass
class Message(NonTerminal, Generic[T]): pass
class StreamOpt(NonTerminal, Generic[T]): pass
class RpcType(NonTerminal, Generic[T]): pass
class RpcBodyElem(NonTerminal, Generic[T]): pass
class RpcBody(NonTerminal, Generic[T]): pass
class RpcBodyOpt(NonTerminal, Generic[T]): pass
class Rpc(NonTerminal, Generic[T]): pass
class ServiceElem(NonTerminal, Generic[T]): pass
class ServiceBody(NonTerminal, Generic[T]): pass
class Service(NonTerminal, Generic[T]): pass


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
        func: Callable,
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

    def extract_from_function(self, func: Callable) -> list[Production]:
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

def join_span(*values: Token | ast.Node) -> Span:
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
# ruff: noqa: N805, E501
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
    def act_const(
        values: tuple[INT | FLOAT | STRING | TRUE | FALSE | QualifiedName | Aggregate]
    ) -> ast.Constant:
        value = values[0]

        if isinstance(value, ast.QualifiedName):
            # Identifier constant
            return ast.Constant(
                span=value.span, kind=CONST_IDENT, value=value
            )

        return ast.Constant(span: value.span, value=value)
        # Aggregate constant (already an ast.Constant)
        return Const(value)

    # -----------------------------------------------------------------------
    # Semantic actions: Qualified names
    # -----------------------------------------------------------------------

    def act_ident(values: tuple[IDENT | SYNTAX]) -> ast.Ident:
        value = values[0]
        return ast.Ident(span=value.span, text=values[0].lexeme)

    def act_name_tail(values: tuple[DOT, Ident, NameTail] | Epsilon) -> NameTail[list]:
        if len(values) == 0:
            return NameTail([])

        return NameTail([values[1]] + values[2])

    def act_qualified_name_absolute(values: tuple[DOT, Ident, NameTail]) -> QualifiedName[ast.QualifiedName]:
        ident_tok: Token = values[1]
        tail: list[Token] = values[2]
        last = tail[-1] if tail else ident_tok

        return QualifiedName(ast.QualifiedName(
            span=join_span(values[0], last),
            absolute=True,
            parts=tuple([ident_tok.lexeme] + [tok.lexeme for tok in tail]),
        ))

    def act_qualified_name_relative(values: tuple[Ident, NameTail]) -> QualifiedName[ast.QualifiedName]:
        ident_tok: Token = values[0].value
        tail: list[Token] = values[1].value
        last = tail[-1] if tail else ident_tok

        return QualifiedName(ast.QualifiedName(
            span=join_span(ident_tok, last),
            absolute=False,
            parts=tuple([ident_tok.lexeme] + [tok.lexeme for tok in tail]),
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Aggregates
    # -----------------------------------------------------------------------

    # def act_opt_comma(values: tuple[COMMA] | Epsilon) -> OptComma[bool]:
    #    return OptComma(len(values) > 0)

    def act_aggregate_field(values: tuple[ast.Ident, COLON, ast.Constant]) -> ast.MessageField:
        name: Token = values[0]
        const: ast.Constant = values[2]
        return ast.MessageField(span=join_span(name, const), name=name, value=const)

    def act_aggregate_fields(values: tuple[ast.MessageField, COMMA, ast.MessageFields | Epsilon]) -> ast.MessageFields:
        return AggFields([values[0]] + values[1])

    def act_aggregate(values: tuple[LBRACE, ast.MessageField | ast.MessageFields | Epsilon, RBRACE]) -> ast.MessageConstant:
        fields: list = values[1]

        return Aggregate(ast.Constant(
            span=join_span(values[0], values[2]),
            kind=CONST_AGGREGATE, value=tuple(fields)
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Options
    # -----------------------------------------------------------------------

    def act_option_suffix(values: tuple[DOT, Ident, ast.OptionSuffix] | Epsilon) -> ast.OptionSuffix:
        if len(values) == 0:
            return ast.OptionSuffix()

        tok: Token = values[1]
        option_suffix = values[2]
        return ast.OptionSuffix(span=join_span(tok, suffix), suffix=[tok] + option_suffix.suffix)

    def act_option_name_plain(values: tuple[ast.QualifiedName]) -> OptionName[ast.OptionName]:
        return OptionName(ast.OptionName(span=qn.span, custom=False, base=values[0])

    def act_option_name_custom(values: tuple[LPAREN, ast.QualifiedName, RPAREN, ast.OptionSuffix]) -> ast.OptionName:
        suffix = values[3]
        return ast.OptionName(
            span=join_span(values[0], suffix),
            custom=True,
            base=values[1],
            suffix=suffix,
        )

    def act_option(values: tuple[OptionName, EQ, Const]) -> ast.Option:
        name: ast.OptionName = values[0]
        const: ast.Constant = values[2]
        return ast.Option(
            span=join_span(name, const),
            name=name, value=const
        )

    def act_option_statement(values: tuple[OPTION, Option, SEMI]) -> ast.OptionStmt:
        opt: ast.Option = values[1]
        return ast.OptionStmt(
            span=join_span(values[0], values[2]), option=opt
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Top-level statements
    # -----------------------------------------------------------------------

    def act_syntax_statement(values: tuple[SYNTAX, EQ, STRING, SEMI]) -> SyntaxStmt[ast.Syntax]:
        literal = values[2].lexeme
        if literal != "proto3":
            raise ParseError(
                span=values[2].span,
                message="only proto3 syntax is supported",
                hint='use: syntax = "proto3";'
            )

        return SyntaxStmt(ast.Syntax(
            span=join_span(values[0], values[3]), value=literal
        ))

    def act_import_modifier(values: tuple[WEAK] | tuple[PUBLIC] | Epsilon) -> ImportModOpt[str | None]:
        if len(values) == 0:
            return ImportModOpt(None)
        tok: Token = values[0]
        return ImportModOpt(tok.lexeme)

    def act_import_statement(values: tuple[IMPORT, ImportModOpt, STRING, SEMI]) -> ImportStmt[ast.Import]:
        modifier: str | None = values[1]
        path_tok: Token = values[2]
        return ImportStmt(ast.Import(
            span=join_span(values[0], values[3]),
            path=path_tok.lexeme, modifier=modifier
        ))

    def act_package_statement(values: tuple[PACKAGE, QualifiedName, SEMI]) -> PackageStmt[ast.Package]:
        qn: ast.QualifiedName = values[1]
        return PackageStmt(ast.Package(
            span=join_span(values[0], values[2]), name=qn
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Field options
    # -----------------------------------------------------------------------

    def act_field_option(values: tuple[Option]) -> FieldOption[ast.FieldOption]:
        opt: ast.Option = values[0]
        return FieldOption(ast.FieldOption(span=opt.span, option=opt))

    def act_field_option_tail(values: tuple[COMMA, FieldOption, FieldOptionListTail] | Epsilon) -> FieldOptionListTail[list]:
        if len(values) == 0:
            return FieldOptionListTail([])
        return FieldOptionListTail([values[1]] + values[2])

    def act_field_option_list(values: tuple[FieldOption, FieldOptionListTail]) -> FieldOptionList[list]:
        return FieldOptionList([values[0]] + values[1])

    def act_field_options(values: tuple[LBRACKET, FieldOptionList, RBRACKET] | Epsilon) -> FieldOptions[tuple]:
        if len(values) == 0:
            return FieldOptions(())
        return FieldOptions(tuple(values[1]))

    # -----------------------------------------------------------------------
    # Semantic actions: Types
    # -----------------------------------------------------------------------

    def act_map_value_type(values: tuple[QualifiedName]) -> MapValueType[ast.QualifiedName]:
        return MapValueType(values[0])

    def act_map_key(values: tuple[Ident]) -> MapKeyType[Token]:
        return MapKeyType(values[0])

    def act_map_type(values: tuple[MAP, LANGLE, MapKeyType, COMMA, MapValueType, RANGLE]) -> MapType[tuple]:
        key_tok: Token = values[2]
        value_qn: ast.QualifiedName = values[4]
        return MapType((join_span(values[0], values[5]), key_tok, value_qn))

    def act_field_label(values: tuple[REPEATED] | Epsilon) -> FieldLabel[Token | None]:
        if len(values) == 0:
            return FieldLabel(None)
        return FieldLabel(values[0])

    # -----------------------------------------------------------------------
    # Semantic actions: Fields
    # -----------------------------------------------------------------------

    def _field_from_qualified_name(
        values: tuple[
            FieldLabel,
            QualifiedName,
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> Field[ast.Field]:
        repeated_token: Token | None = values[0]
        type_qualified: ast.QualifiedName = values[1]
        name_token: Token = values[2]
        number_token: Token = values[4]
        options = values[5]
        semi_token: Token = values[6]

        repeated = repeated_token is not None

        scalar = None
        type_name = type_qualified
        if ((not type_qualified.absolute)
                and len(type_qualified.parts) == 1
                and type_qualified.parts[0] in SCALAR_TYPES):
            scalar = type_qualified.parts[0]
            type_name = None

        return ast.Field(
            span=join_span(
                repeated_token if repeated_token else type_qualified,
                semi_token
            ),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            type_name=type_name,
            scalar_type=scalar,
            repeated=repeated,
            options=tuple(options),
        )

    def _field_from_map(
        values: tuple[
            FieldLabel,
            MapType,
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> Field[ast.Field]:
        repeated_token: Token | None = values[0]
        map_span, key_token, value_qualified = values[1]
        key_type = key_token.lexeme
        name_token: Token = values[2]
        number_token: Token = values[4]
        semicolon_token: Token = values[6]
        options = values[5]

        if repeated_token:
            raise ParseError(
                span=repeated_token.span,
                message="map fields cannot be repeated",
                hint="remove 'repeated' (map fields are implicitly repeated)",
            )
        if key_type not in MAP_KEY_TYPES:
            raise ParseError(
                span=key_token.span,
                message=f"invalid map key type: {key_type}",
                hint="map keys must be an integral type, bool, or string",
            )

        scalar = None
        type_name = value_qualified
        if (not value_qualified.absolute
                and len(value_qualified.parts) == 1
                and value_qualified.parts[0] in SCALAR_TYPES):
            scalar = value_qualified.parts[0]
            type_name = None

        return ast.Field(
            span=Span(
                file=map_span.file,
                start=map_span.start, end=semicolon_token.span.end
            ),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            map_key_type=key_type,
            map_value=ast.TypeRef(
                span=map_span, type_name=type_name, scalar_type=scalar
            ),
            options=tuple(options),
        )

    def act_field_qualified_name(
        values: tuple[
            FieldLabel,
            QualifiedName,
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> Field[ast.Field]:
        return Field(GrammarBuilder._field_from_qualified_name(values))

    def act_field_map(
        values: tuple[
            FieldLabel,
            MapType,
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> Field[ast.Field]:
        return Field(GrammarBuilder._field_from_map(values))

    # -----------------------------------------------------------------------
    # Semantic actions: Oneof
    # -----------------------------------------------------------------------

    def act_oneof_field(
        values: tuple[
            QualifiedName,
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> OneofField[ast.Field]:
        qualified_name: ast.QualifiedName = values[0]
        name_token: Token = values[1]
        number_token: Token = values[3]
        options = values[4]
        semi_token: Token = values[5]

        scalar = None
        type_name = qualified_name

        if ((not qualified_name.absolute)
                and len(qualified_name.parts) == 1
                and qualified_name.parts[0] in SCALAR_TYPES):
            scalar = qualified_name.parts[0]
            type_name = None

        return OneofField(ast.Field(
            span=join_span(qualified_name, semi_token),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            type_name=type_name,
            scalar_type=scalar,
            options=tuple(options),
        ))

    def act_oneof_elem(values: tuple[OneofField | SEMI]) -> OneofElem[ast.Field | None]:
        if isinstance(values[0], Token):  # SEMI token
            return OneofElem(None)
        return OneofElem(values[0])

    def act_oneof_body(values: tuple[OneofElem, OneofBody] | Epsilon) -> OneofBody[list]:
        if len(values) == 0:
            return OneofBody([])
        head = [values[0]] if values[0] is not None else []
        return OneofBody(head + [x for x in values[1] if x is not None])

    def act_oneof(values: tuple[ONEOF, IDENT, LBRACE, OneofBody, RBRACE]) -> Oneof[ast.Oneof]:
        name_token: Token = values[1]
        body: list = values[3]
        return Oneof(ast.Oneof(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            fields=tuple(body)
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Reserved
    # -----------------------------------------------------------------------

    def act_reserved_single(values: tuple[INT]) -> ReservedRange[ast.ReservedRange]:
        tok: Token = values[0]
        return ReservedRange(ast.ReservedRange(
            span=join_span(tok), start=int(tok.lexeme)
        ))

    def act_reserved_range(values: tuple[INT, TO, INT | MAX]) -> ReservedRange[ast.ReservedRange]:
        start_tok: Token = values[0]
        end_tok: Token = values[2]

        is_max = end_tok.kind is MAX
        return ReservedRange(ast.ReservedRange(
            span=join_span(start_tok, end_tok),
            start=int(start_tok.lexeme),
            end_is_max=is_max,
            end=None if is_max else int(end_tok.lexeme)
        ))

    def act_reserved_ranges_tail(values: tuple[COMMA, ReservedRange, ReservedRangesTail] | Epsilon) -> ReservedRangesTail[list]:
        if len(values) == 0:
            return ReservedRangesTail([])
        return ReservedRangesTail([values[1]] + values[2])

    def act_reserved_ranges(values: tuple[ReservedRange, ReservedRangesTail]) -> ReservedRanges[list]:
        return ReservedRanges([values[0]] + values[1])

    def act_reserved_names_tail(values: tuple[COMMA, STRING, ReservedNamesTail] | Epsilon) -> ReservedNamesTail[list]:
        if len(values) == 0:
            return ReservedNamesTail([])
        tok: Token = values[1]
        return ReservedNamesTail([tok.lexeme] + values[2])

    def act_reserved_names(values: tuple[STRING, ReservedNamesTail]) -> ReservedNames[list]:
        tok: Token = values[0]
        return ReservedNames([tok.lexeme] + values[1])

    def act_reserved_spec_ranges(values: tuple[ReservedRanges]) -> ReservedSpec[tuple]:
        return ReservedSpec(("ranges", values[0]))

    def act_reserved_spec_names(values: tuple[ReservedNames]) -> ReservedSpec[tuple]:
        return ReservedSpec(("names", values[0]))

    def act_reserved_statement(values: tuple[RESERVED, ReservedSpec, SEMI]) -> ReservedStmt[ast.Reserved]:
        spec: tuple = values[1]
        return ReservedStmt(ast.Reserved(
            span=join_span(values[0], values[2]),
            ranges=tuple(spec[1])
            if spec[0] == "ranges" else (),
            names=tuple(spec[1])
            if spec[0] == "names" else (),
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Enum
    # -----------------------------------------------------------------------

    def act_enum_value(
        values: tuple[
            Ident,
            EQ,
            INT,
            FieldOptions,
            SEMI,
        ]
    ) -> EnumValue[ast.EnumValue]:
        name_token: Token = values[0]
        number_token: Token = values[2]
        options = values[3]
        semi_token: Token = values[4]

        return EnumValue(ast.EnumValue(
            span=join_span(name_token, semi_token),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            options=tuple(options),
        ))

    def act_enum_elem(
        values: tuple[EnumValue | OptionStmt | ReservedStmt | SEMI]
    ) -> EnumElem[ast.EnumValue | ast.OptionStmt | ast.Reserved | None]:
        if isinstance(values[0], Token):  # SEMI token
            return EnumElem(None)
        return EnumElem(values[0])

    def act_enum_body(values: tuple[EnumElem, EnumBody] | Epsilon) -> EnumBody[list]:
        if len(values) == 0:
            return EnumBody([])
        head = [values[0]] if values[0] is not None else []
        return EnumBody(head + values[1])

    def act_enum(values: tuple[ENUM, Ident, LBRACE, EnumBody, RBRACE]) -> Enum[ast.Enum]:
        name_token: Token = values[1]
        body: list = values[3]
        return Enum(ast.Enum(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: Message
    # -----------------------------------------------------------------------

    def act_message_elem(
        values: tuple[Field | Oneof | Enum | Message | OptionStmt | ReservedStmt | SEMI]
    ) -> MessageElem[
        ast.Field | ast.Oneof | ast.Enum |
        ast.Message | ast.OptionStmt | ast.Reserved | None
    ]:
        if isinstance(values[0], Token):  # SEMI token
            return MessageElem(None)
        return MessageElem(values[0])

    def act_message_body(values: tuple[MessageElem, MessageBody] | Epsilon) -> MessageBody[list]:
        if len(values) == 0:
            return MessageBody([])
        head = [values[0]] if values[0] is not None else []
        return MessageBody(head + values[1])

    def act_message(values: tuple[MESSAGE, Ident, LBRACE, MessageBody, RBRACE]) -> Message[ast.Message]:
        name_token: Token = values[1]
        body: list = values[3]
        return Message(ast.Message(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: RPC and Service
    # -----------------------------------------------------------------------

    def act_is_stream(values: tuple[STREAM] | Epsilon) -> StreamOpt[bool]:
        return StreamOpt(len(values) > 0)

    def _make_type_ref(span: Span, qualified: ast.QualifiedName) -> ast.TypeRef:
        scalar = None
        type_name = qualified

        if ((not qualified.absolute)
                and len(qualified.parts) == 1
                and qualified.parts[0] in SCALAR_TYPES):
            scalar = qualified.parts[0]
            type_name = None

        return ast.TypeRef(span=span, type_name=type_name, scalar_type=scalar)

    def act_rpc_type(values: tuple[QualifiedName]) -> RpcType[ast.QualifiedName]:
        return RpcType(values[0])

    def act_rpc_body_elem(values: tuple[OptionStmt | SEMI]) -> RpcBodyElem[ast.OptionStmt | None]:
        if isinstance(values[0], Token):  # SEMI token
            return RpcBodyElem(None)

        return RpcBodyElem(values[0])

    def act_rpc_body(values: tuple[RpcBodyElem, RpcBody] | Epsilon) -> RpcBody[list]:
        if len(values) == 0:
            return RpcBody([])
        head = [values[0]] if values[0] is not None else []
        return RpcBody(head + values[1])

    def act_rpc_body_optional_semi(values: tuple[SEMI]) -> RpcBodyOpt[tuple]:
        return RpcBodyOpt(())

    def act_rpc_body_optional_block(values: tuple[LBRACE, RpcBody, RBRACE]) -> RpcBodyOpt[tuple]:
        return RpcBodyOpt(tuple(values[1]))

    def act_rpc(
        values: tuple[
            RPC,
            Ident,
            LPAREN,
            StreamOpt,
            RpcType,
            RPAREN,
            RETURNS,
            LPAREN,
            StreamOpt,
            RpcType,
            RPAREN,
            RpcBodyOpt,
        ]
    ) -> ast.Rpc:
        rpc_token: Token = values[0]
        name_token: Token = values[1]
        lparen1: Token = values[2]
        request_stream: bool = values[3]
        request_type: ast.QualifiedName = values[4]
        rparen1: Token = values[5]
        lparen2: Token = values[7]
        response_stream: bool = values[8]
        response_type: ast.QualifiedName = values[9]
        rparen2: Token = values[10]
        body_opt: tuple = values[11]

        return ast.Rpc(
            span=join_span(
                rpc_token,
                body_opt[-1] if body_opt else rparen2
            ),
            name=name_token.lexeme,
            request=GrammarBuilder._make_type_ref(
                join_span(lparen1, rparen1), request_type
            ),
            response=GrammarBuilder._make_type_ref(
                join_span(lparen2, rparen2), response_type
            ),
            request_stream=request_stream,
            response_stream=response_stream,
            options=tuple([x for x in body_opt if isinstance(x, ast.OptionStmt)]),
        )

    def act_service_elem(values: tuple[Rpc | OptionStmt | SEMI]) -> ServiceElem[ast.Rpc | ast.OptionStmt | None]:
        if isinstance(values[0], Token):  # SEMI token
            return ServiceElem(None)

        return ServiceElem(values[0])

    def act_service_body(values: tuple[ServiceElem, ServiceBody] | Epsilon) -> ServiceBody[list]:
        if len(values) == 0:
            return ServiceBody([])

        head = [values[0]] if values[0] is not None else []
        return ServiceBody(head + values[1])

    def act_service(values: tuple[SERVICE, Ident, LBRACE, ServiceBody, RBRACE]) -> Service[ast.Service]:
        name_token: Token = values[1]
        body: list = values[3]
        return Service(ast.Service(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        ))

    # -----------------------------------------------------------------------
    # Semantic actions: File (top-level)
    # -----------------------------------------------------------------------

    def act_decl(values: tuple[Message | Enum | Service]) -> Decl[ast.Enum | ast.Message | ast.Service]:
        return Decl(values[0])

    def act_item(
        values: tuple[SyntaxStmt | ImportStmt | PackageStmt | OptionStmt | Decl | SEMI]
    ) -> Item[
        ast.Syntax | ast.Import | ast.Package |
        ast.OptionStmt | ast.Enum | ast.Message |
        ast.Service | None
    ]:
        if isinstance(values[0], Token):  # SEMI token
            return Item(None)
        return Item(values[0])

    def act_items(values: tuple[Item, Items] | Epsilon) -> Items[list]:
        if len(values) == 0:
            return Items([])

        head = [values[0]] if values[0] is not None else []
        return Items(head + values[1])

    def act_file(values: tuple[Items]) -> File[ast.ProtoFile]:
        items = [x for x in values[0] if x is not None]
        syntax: ast.Syntax | None = None
        imports: list[ast.Import] = []
        package: ast.Package | None = None

        for item in items:
            if isinstance(item, ast.Syntax):
                if syntax is not None:
                    raise ParseError(
                        span=item.span,
                        message="duplicate syntax declaration"
                    )
                syntax = item
            elif isinstance(item, ast.Import):
                imports.append(item)
            elif isinstance(item, ast.Package):
                if package is not None:
                    raise ParseError(
                        span=item.span,
                        message="duplicate package declaration"
                    )
                package = item

        if items:
            file_span = join_span(items[0], items[-1])
        else:
            file_span = Span(
                file="<unknown>",
                start=Position(0, 1, 1), end=Position(0, 1, 1)
            )

        return File(ast.ProtoFile(
            span=file_span, syntax=syntax, items=tuple(items),
            imports=tuple(imports), package=package
        ))

    @classmethod
    def build(cls) -> Grammar:
        """Build and cache the proto3 grammar."""
        if cls._cache is not None:
            return cls._cache

        extractor = GrammarExtractor()
        productions = extractor.extract_from_class(cls)

        cls._cache = Grammar(start=File, productions=tuple(productions))
        return cls._cache
