import itertools
from dataclasses import dataclass
from typing import Callable, Union, get_type_hints, get_origin, get_args

from . import ast
from .symbol import TerminalSymbol, NonTerminalSymbol, Symbol, \
    NonTerminalType, Terminal, NonTerminal
from .errors import ParseError
from .spans import Position, Span


@dataclass(frozen=True, slots=True)
class Token:
    kind: TerminalSymbol
    lexeme: str
    span: Span

    def to_constant(self) -> ast.Constant:
        if self.kind == INT:
            value = int(self.lexeme)
        elif self.kind == FLOAT:
            value = float(self.lexeme)
        elif self.kind == STRING:
            value = self.lexeme
        elif self.kind == TRUE:
            value = True
        elif self.kind == FALSE:
            value = False
        else:
            raise ValueError(f"Cannot convert {self.kind} to Constant")

        return ast.Constant(span=self.span, kind=self.kind, value=value)


@dataclass
class Production:
    head: NonTerminalSymbol
    body: tuple[Symbol, ...]
    action: Callable[[tuple], object]

    def __str__(self) -> str:
        body_str = " ".join(str(s) for s in self.body)
        return f"{self.head} -> {body_str}"


@dataclass
class Grammar:
    start: NonTerminalSymbol
    productions: tuple[Production, ...]


# TerminalSymbol, NonTerminalSymbol, and Symbol are imported from symbol.py
Epsilon = tuple[()]

# Constant kind markers (for ast.Constant.kind field)
CONST_IDENT = TerminalSymbol("ident")
CONST_AGGREGATE = TerminalSymbol("aggregate")


def eps() -> Epsilon:
    """
    Marker for epsilon (empty) productions.

    Usage in type annotations:
        # Direct epsilon production:
        def act_empty(values: eps) -> Nt_Foo[list]:
            return []

        # Optional element in union:
        def act_optional(values: tuple[COMMA] | Epsilon) -> Nt_Opt[bool]:
            return len(values) > 0
        # Generates two productions:
        #   Nt_Opt -> COMMA  (receives (token,), len=1, returns True)
        #   Nt_Opt -> ε      (receives (), len=0, returns False)
    """
    return tuple()


# Literal tokens
IDENT = Terminal("IDENT")
INT = Terminal("INT")
FLOAT = Terminal("FLOAT")
STRING = Terminal("STRING")

# Keywords
SYNTAX = Terminal("syntax")
IMPORT = Terminal("import")
WEAK = Terminal("weak")
PUBLIC = Terminal("public")
PACKAGE = Terminal("package")
OPTION = Terminal("option")
REPEATED = Terminal("repeated")
ONEOF = Terminal("oneof")
MAP = Terminal("map")
RESERVED = Terminal("reserved")
TO = Terminal("to")
MAX = Terminal("max")
ENUM = Terminal("enum")
MESSAGE = Terminal("message")
SERVICE = Terminal("service")
RPC = Terminal("rpc")
RETURNS = Terminal("returns")
STREAM = Terminal("stream")

# Punctuation
SEMI = Terminal(";")
COMMA = Terminal(",")
DOT = Terminal(".")
EQ = Terminal("=")
COLON = Terminal(":")
SLASH = Terminal("/")
LPAREN = Terminal("(")
RPAREN = Terminal(")")
LBRACE = Terminal("{")
RBRACE = Terminal("}")
LBRACKET = Terminal("[")
RBRACKET = Terminal("]")
LANGLE = Terminal("<")
RANGLE = Terminal(">")

# Constants / booleans
TRUE = Terminal("true")
FALSE = Terminal("false")

EOF = Terminal("EOF")

# Keyword dictionary
KEYWORDS = {
    s.name: s.symbol for s in {
        SYNTAX, IMPORT, WEAK, PUBLIC, PACKAGE, OPTION, REPEATED, ONEOF,
        MAP, RESERVED, TO, MAX, ENUM, MESSAGE, SERVICE, RPC, RETURNS,
        STREAM, TRUE, FALSE,
    }
}

# Punctuation dictionary
PUNCTUATION = {
    s.name: s.symbol for s in {
        SEMI, COMMA, DOT, EQ, COLON, SLASH, LPAREN, RPAREN,
        LBRACE, RBRACE, LBRACKET, RBRACKET, LANGLE, RANGLE,
    }
}


# NonTerminal symbols
File = NonTerminal("File")
Items = NonTerminal("Items")
Item = NonTerminal("Item")
Decl = NonTerminal("Decl")
Ident = NonTerminal("Ident")
NameTail = NonTerminal("NameTail")
QualifiedName = NonTerminal("QualifiedName")
SyntaxStmt = NonTerminal("SyntaxStmt")
ImportStmt = NonTerminal("ImportStmt")
ImportModOpt = NonTerminal("ImportModOpt")
PackageStmt = NonTerminal("PackageStmt")
OptionStmt = NonTerminal("OptionStmt")
Option = NonTerminal("Option")
OptionName = NonTerminal("OptionName")
OptionSuffix = NonTerminal("OptionSuffix")
Const = NonTerminal("Const")
OptComma = NonTerminal("OptComma")
AggField = NonTerminal("AggField")
AggFields = NonTerminal("AggFields")
AggFieldsTail = NonTerminal("AggFieldsTail")
AggFieldsOpt = NonTerminal("AggFieldsOpt")
Aggregate = NonTerminal("Aggregate")
FieldOption = NonTerminal("FieldOption")
FieldOptionList = NonTerminal("FieldOptionList")
FieldOptionListTail = NonTerminal("FieldOptionListTail")
FieldOptions = NonTerminal("FieldOptions")
MapValueType = NonTerminal("MapValueType")
MapKeyType = NonTerminal("MapKeyType")
MapType = NonTerminal("MapType")
FieldLabel = NonTerminal("FieldLabel")
Field = NonTerminal("Field")
OneofField = NonTerminal("OneofField")
OneofElem = NonTerminal("OneofElem")
OneofBody = NonTerminal("OneofBody")
Oneof = NonTerminal("Oneof")
ReservedRange = NonTerminal("ReservedRange")
ReservedRangesTail = NonTerminal("ReservedRangesTail")
ReservedRanges = NonTerminal("ReservedRanges")
ReservedNamesTail = NonTerminal("ReservedNamesTail")
ReservedNames = NonTerminal("ReservedNames")
ReservedSpec = NonTerminal("ReservedSpec")
ReservedStmt = NonTerminal("ReservedStmt")
EnumValue = NonTerminal("EnumValue")
EnumElem = NonTerminal("EnumElem")
EnumBody = NonTerminal("EnumBody")
Enum = NonTerminal("Enum")
MessageElem = NonTerminal("MessageElem")
MessageBody = NonTerminal("MessageBody")
Message = NonTerminal("Message")
StreamOpt = NonTerminal("StreamOpt")
RpcType = NonTerminal("RpcType")
RpcBodyElem = NonTerminal("RpcBodyElem")
RpcBody = NonTerminal("RpcBody")
RpcBodyOpt = NonTerminal("RpcBodyOpt")
Rpc = NonTerminal("Rpc")
ServiceElem = NonTerminal("ServiceElem")
ServiceBody = NonTerminal("ServiceBody")
Service = NonTerminal("Service")


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

    def __init__(self):
        self.productions: list[Production] = []

    def _extract_from_values_type(
        self,
        values_type,
        head: NonTerminalSymbol,
        func: Callable
    ) -> list[Production]:
        """Recursively extract productions from a values type annotation."""
        # Handle epsilon productions: values: eps
        if values_type is eps:
            return [Production(head=head, body=tuple(), action=func)]

        origin_type = get_origin(values_type)

        # Handle union at top level: tuple[A, B] | eps
        if origin_type is Union:
            productions = []
            for alt in get_args(values_type):
                productions.extend(
                    self._extract_from_values_type(alt, head, func)
                )
            return productions

        # Handle tuple types
        if origin_type is not tuple:
            return []  # We only support tuple

        body_types = get_args(values_type)

        # Empty tuple means epsilon
        if not body_types:
            return [Production(head=head, body=tuple(), action=func)]

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
                types.append([t.symbol for t in get_args(body_type)])
            else:
                # Single type: extract symbol
                types.append([body_type.symbol])

        return [
            Production(head=head, body=tuple(combo), action=func)
            for combo in itertools.product(*types)
        ]

    def extract_from_function(self, func: Callable) -> list[Production]:
        """
        Extract production rule(s) from a function's type annotations.

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
        if not issubclass(raw_return, NonTerminalType):
            return []

        # Extract NonTerminal instance from annotation
        head = raw_return.symbol

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
        end=values[-1].span.end
    )


# ============================================================================
# Grammar builder with semantic actions
# ============================================================================

class GrammarBuilder:
    """
    Proto3 grammar definition using type-annotation-driven productions.

    Each act_* method defines a production rule through its type annotations:
    - Parameter type: tuple of RHS symbols (Terminal/NonTerminal instances)
    - Return type: NonTerminal[ActualType] indicating LHS (e.g., QualifiedName[ast.QualifiedName])
    """

    _cache: Grammar | None = None

    # -----------------------------------------------------------------------
    # Semantic actions: Constants
    # -----------------------------------------------------------------------

    def act_const(
        values: tuple[
            INT | FLOAT | STRING | TRUE | FALSE | QualifiedName | Aggregate
        ]
    ) -> Const[ast.Constant]:
        value = values[0]

        if isinstance(value, Token):
            # Literal constant (int, float, string, bool)
            return value.to_constant()
        elif isinstance(value, ast.QualifiedName):
            # Identifier constant
            return ast.Constant(
                span=value.span, kind=CONST_IDENT, value=value
            )
        else:
            # Aggregate constant (already an ast.Constant)
            return value

    # -----------------------------------------------------------------------
    # Semantic actions: Qualified names
    # -----------------------------------------------------------------------

    def act_ident(values: tuple[IDENT | SYNTAX]) -> Ident[object]:
        return values[0]

    def act_name_tail(values: tuple[DOT, Ident, NameTail] | Epsilon) -> NameTail[list]:
        if len(values) == 0:
            return []

        return [values[1]] + values[2]

    def act_qualified_name_absolute(
        values: tuple[DOT, Ident, NameTail]
    ) -> QualifiedName[ast.QualifiedName]:
        ident_tok: Token = values[1]
        tail: list[Token] = values[2]
        last = tail[-1] if tail else ident_tok
        return ast.QualifiedName(
            span=join_span(values[0], last),
            absolute=True,
            parts=tuple([ident_tok.lexeme] + [tok.lexeme for tok in tail]),
        )

    def act_qualified_name_relative(
        values: tuple[Ident, NameTail]
    ) -> QualifiedName[ast.QualifiedName]:
        ident_tok: Token = values[0]
        tail: list[Token] = values[1]
        last = tail[-1] if tail else ident_tok
        return ast.QualifiedName(
            span=join_span(ident_tok, last),
            absolute=False,
            parts=tuple([ident_tok.lexeme] + [tok.lexeme for tok in tail]),
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Aggregates
    # -----------------------------------------------------------------------

    def act_opt_comma(values: tuple[COMMA] | Epsilon) -> OptComma[bool]:
        return len(values) > 0

    def act_aggregate_field(
        values: tuple[Ident, COLON, Const, OptComma]
    ) -> AggField[tuple]:
        tok: Token = values[0]
        const: ast.Constant = values[2]
        return (tok.lexeme, const)

    def act_aggregate_tail(
        values: tuple[AggField, AggFieldsTail] | Epsilon
    ) -> AggFieldsTail[list]:
        if len(values) == 0:
            return []
        return [values[0]] + values[1]

    def act_aggregate_fields(
        values: tuple[AggField, AggFieldsTail]
    ) -> AggFields[list]:
        return [values[0]] + values[1]

    def act_agg_fields_opt(
        values: tuple[AggFields] | Epsilon
    ) -> AggFieldsOpt[list]:
        return values[0] if len(values) > 0 else []

    def act_aggregate(
        values: tuple[LBRACE, AggFieldsOpt, RBRACE]
    ) -> Aggregate[ast.Constant]:
        fields: list = values[1]
        return ast.Constant(
            span=join_span(values[0], values[2]),
            kind=CONST_AGGREGATE, value=tuple(fields)
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Options
    # -----------------------------------------------------------------------

    def act_option_suffix(
        values: tuple[DOT, Ident, OptionSuffix] | Epsilon
    ) -> OptionSuffix[list]:
        if len(values) == 0:
            return []

        tok: Token = values[1]
        return [tok] + values[2]

    def act_option_name_plain(
        values: tuple[QualifiedName]
    ) -> OptionName[ast.OptionName]:
        qn: ast.QualifiedName = values[0]
        return ast.OptionName(
            span=qn.span, custom=False, base=qn, suffix=tuple()
        )

    def act_option_name_custom(
        values: tuple[LPAREN, QualifiedName, RPAREN, OptionSuffix]
    ) -> OptionName[ast.OptionName]:
        qn: ast.QualifiedName = values[1]
        suffix: list = values[3]
        last = suffix[-1] if suffix else values[2]
        return ast.OptionName(
            span=join_span(values[0], last),
            custom=True,
            base=qn,
            suffix=tuple(tok.lexeme for tok in suffix),
        )

    def act_option(
        values: tuple[OptionName, EQ, Const]
    ) -> Option[ast.Option]:
        name: ast.OptionName = values[0]
        const: ast.Constant = values[2]
        return ast.Option(
            span=join_span(name, const),
            name=name, value=const
        )

    def act_option_statement(
        values: tuple[OPTION, Option, SEMI]
    ) -> OptionStmt[ast.OptionStmt]:
        opt: ast.Option = values[1]
        return ast.OptionStmt(
            span=join_span(values[0], values[2]), option=opt
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Top-level statements
    # -----------------------------------------------------------------------

    def act_syntax_statement(
        values: tuple[SYNTAX, EQ, STRING, SEMI]
    ) -> SyntaxStmt[ast.Syntax]:
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

    def act_import_modifier(
        values: tuple[WEAK] | tuple[PUBLIC] | Epsilon
    ) -> ImportModOpt[str | None]:
        if len(values) == 0:
            return None
        tok: Token = values[0]
        return tok.lexeme

    def act_import_statement(
        values: tuple[IMPORT, ImportModOpt, STRING, SEMI]
    ) -> ImportStmt[ast.Import]:
        modifier: str | None = values[1]
        path_tok: Token = values[2]
        return ast.Import(
            span=join_span(values[0], values[3]),
            path=path_tok.lexeme, modifier=modifier
        )

    def act_package_statement(
        values: tuple[PACKAGE, QualifiedName, SEMI]
    ) -> PackageStmt[ast.Package]:
        qn: ast.QualifiedName = values[1]
        return ast.Package(
            span=join_span(values[0], values[2]), name=qn
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Field options
    # -----------------------------------------------------------------------

    def act_field_option(values: tuple[Option]) -> FieldOption[ast.FieldOption]:
        opt: ast.Option = values[0]
        return ast.FieldOption(span=opt.span, option=opt)

    def act_field_option_tail(
        values: tuple[COMMA, FieldOption, FieldOptionListTail] | Epsilon
    ) -> FieldOptionListTail[list]:
        if len(values) == 0:
            return []
        return [values[1]] + values[2]

    def act_field_option_list(
        values: tuple[FieldOption, FieldOptionListTail]
    ) -> FieldOptionList[list]:
        return [values[0]] + values[1]

    def act_field_options(
        values: tuple[LBRACKET, FieldOptionList, RBRACKET] | Epsilon
    ) -> FieldOptions[tuple]:
        if len(values) == 0:
            return tuple()
        return tuple(values[1])

    # -----------------------------------------------------------------------
    # Semantic actions: Types
    # -----------------------------------------------------------------------

    def act_map_value_type(values: tuple[QualifiedName]) -> MapValueType[ast.QualifiedName]:
        return values[0]

    def act_map_key(values: tuple[Ident]) -> MapKeyType[Token]:
        return values[0]

    def act_map_type(
        values: tuple[MAP, LANGLE, MapKeyType, COMMA, MapValueType, RANGLE]
    ) -> MapType[tuple]:
        key_tok: Token = values[2]
        value_qn: ast.QualifiedName = values[4]
        return (join_span(values[0], values[5]), key_tok, value_qn)

    def act_field_label(values: tuple[REPEATED] | Epsilon) -> FieldLabel[Token | None]:
        if len(values) == 0:
            return None
        return values[0]

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
        return GrammarBuilder._field_from_qualified_name(values)

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
        return GrammarBuilder._field_from_map(values)

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

        return ast.Field(
            span=join_span(qualified_name, semi_token),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            type_name=type_name,
            scalar_type=scalar,
            options=tuple(options),
        )

    def act_oneof_elem(
        values: tuple[OneofField | SEMI]
    ) -> OneofElem[ast.Field | None]:
        if isinstance(values[0], Token):  # SEMI token
            return None
        return values[0]

    def act_oneof_body(
        values: tuple[OneofElem, OneofBody] | Epsilon
    ) -> OneofBody[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + [x for x in values[1] if x is not None]

    def act_oneof(
        values: tuple[ONEOF, IDENT, LBRACE, OneofBody, RBRACE]
    ) -> Oneof[ast.Oneof]:
        name_token: Token = values[1]
        body: list = values[3]
        return ast.Oneof(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            fields=tuple(body)
        )

    # -----------------------------------------------------------------------
    # Semantic actions: Reserved
    # -----------------------------------------------------------------------

    def act_reserved_single(values: tuple[INT]) -> ReservedRange[ast.ReservedRange]:
        tok: Token = values[0]
        return ast.ReservedRange(
            span=join_span(tok), start=int(tok.lexeme)
        )

    def act_reserved_range(
        values: tuple[INT, TO, INT | MAX]
    ) -> ReservedRange[ast.ReservedRange]:
        start_tok: Token = values[0]
        end_tok: Token = values[2]

        is_max = end_tok.kind == MAX.symbol
        return ast.ReservedRange(
            span=join_span(start_tok, end_tok),
            start=int(start_tok.lexeme),
            end_is_max=is_max,
            end=None if is_max else int(end_tok.lexeme)
        )

    def act_reserved_ranges_tail(
        values: tuple[COMMA, ReservedRange, ReservedRangesTail] | Epsilon
    ) -> ReservedRangesTail[list]:
        if len(values) == 0:
            return []
        return [values[1]] + values[2]

    def act_reserved_ranges(
        values: tuple[ReservedRange, ReservedRangesTail]
    ) -> ReservedRanges[list]:
        return [values[0]] + values[1]

    def act_reserved_names_tail(
        values: tuple[COMMA, STRING, ReservedNamesTail] | Epsilon
    ) -> ReservedNamesTail[list]:
        if len(values) == 0:
            return []
        tok: Token = values[1]
        return [tok.lexeme] + values[2]

    def act_reserved_names(
        values: tuple[STRING, ReservedNamesTail]
    ) -> ReservedNames[list]:
        tok: Token = values[0]
        return [tok.lexeme] + values[1]

    def act_reserved_spec_ranges(
        values: tuple[ReservedRanges]
    ) -> ReservedSpec[tuple]:
        return ("ranges", values[0])

    def act_reserved_spec_names(
        values: tuple[ReservedNames]
    ) -> ReservedSpec[tuple]:
        return ("names", values[0])

    def act_reserved_statement(
        values: tuple[RESERVED, ReservedSpec, SEMI]
    ) -> ReservedStmt[ast.Reserved]:
        spec: tuple = values[1]
        return ast.Reserved(
            span=join_span(values[0], values[2]),
            ranges=tuple(spec[1])
            if spec[0] == "ranges" else tuple(),
            names=tuple(spec[1])
            if spec[0] == "names" else tuple(),
        )

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

        return ast.EnumValue(
            span=join_span(name_token, semi_token),
            name=name_token.lexeme,
            number=int(number_token.lexeme),
            options=tuple(options),
        )

    def act_enum_elem(
        values: tuple[EnumValue | OptionStmt | ReservedStmt | SEMI]
    ) -> EnumElem[ast.EnumValue | ast.OptionStmt | ast.Reserved | None]:
        if isinstance(values[0], Token):  # SEMI token
            return None
        return values[0]

    def act_enum_body(
        values: tuple[EnumElem, EnumBody] | Epsilon
    ) -> EnumBody[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + values[1]

    def act_enum(
        values: tuple[ENUM, Ident, LBRACE, EnumBody, RBRACE]
    ) -> Enum[ast.Enum]:
        name_token: Token = values[1]
        body: list = values[3]
        return ast.Enum(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        )

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
            return None
        return values[0]

    def act_message_body(
        values: tuple[MessageElem, MessageBody] | Epsilon
    ) -> MessageBody[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + values[1]

    def act_message(
        values: tuple[MESSAGE, Ident, LBRACE, MessageBody, RBRACE]
    ) -> Message[ast.Message]:
        name_token: Token = values[1]
        body: list = values[3]
        return ast.Message(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        )

    # -----------------------------------------------------------------------
    # Semantic actions: RPC and Service
    # -----------------------------------------------------------------------

    def act_stream_yes(values: tuple[STREAM]) -> StreamOpt[bool]:
        return True

    def act_stream_no(values: eps) -> StreamOpt[bool]:
        return False

    def _make_type_ref(
        span: Span, qualified: ast.QualifiedName
    ) -> ast.TypeRef:
        scalar = None
        type_name = qualified

        if ((not qualified.absolute)
                and len(qualified.parts) == 1
                and qualified.parts[0] in SCALAR_TYPES):
            scalar = qualified.parts[0]
            type_name = None

        return ast.TypeRef(span=span, type_name=type_name, scalar_type=scalar)

    def act_rpc_type(
        values: tuple[QualifiedName]
    ) -> RpcType[ast.QualifiedName]:
        return values[0]

    def act_rpc_body_elem(
        values: tuple[OptionStmt | SEMI]
    ) -> RpcBodyElem[ast.OptionStmt | None]:
        if isinstance(values[0], Token):  # SEMI token
            return None
        return values[0]

    def act_rpc_body(
        values: tuple[RpcBodyElem, RpcBody] | Epsilon
    ) -> RpcBody[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + values[1]

    def act_rpc_body_optional_semi(values: tuple[SEMI]) -> RpcBodyOpt[tuple]:
        return tuple()

    def act_rpc_body_optional_block(
        values: tuple[LBRACE, RpcBody, RBRACE]
    ) -> RpcBodyOpt[tuple]:
        return tuple(values[1])

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
    ) -> Rpc[ast.Rpc]:
        rpc_token: Token = values[0]
        name_token: Token = values[1]
        lparen1: Token = values[2]
        request_stream: bool = values[3]
        request_type: ast.QualifiedName = values[4]
        rparen1: Token = values[5]
        returns_token: Token = values[6]
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

    def act_service_elem(
        values: tuple[Rpc | OptionStmt | SEMI]
    ) -> ServiceElem[ast.Rpc | ast.OptionStmt | None]:
        if isinstance(values[0], Token):  # SEMI token
            return None
        return values[0]

    def act_service_body(
        values: tuple[ServiceElem, ServiceBody] | Epsilon
    ) -> ServiceBody[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + values[1]

    def act_service(
        values: tuple[SERVICE, Ident, LBRACE, ServiceBody, RBRACE]
    ) -> Service[ast.Service]:
        name_token: Token = values[1]
        body: list = values[3]
        return ast.Service(
            span=join_span(values[0], values[4]),
            name=name_token.lexeme,
            body=tuple(body)
        )

    # -----------------------------------------------------------------------
    # Semantic actions: File (top-level)
    # -----------------------------------------------------------------------

    def act_decl(
        values: tuple[Message | Enum | Service]
    ) -> Decl[ast.Enum | ast.Message | ast.Service]:
        return values[0]

    def act_item(
        values: tuple[SyntaxStmt | ImportStmt | PackageStmt | OptionStmt | Decl | SEMI]
    ) -> Item[
        ast.Syntax | ast.Import | ast.Package |
        ast.OptionStmt | ast.Enum | ast.Message |
        ast.Service | None
    ]:
        if isinstance(values[0], Token):  # SEMI token
            return None
        return values[0]

    def act_items(
        values: tuple[Item, Items] | Epsilon
    ) -> Items[list]:
        if len(values) == 0:
            return []
        head = [values[0]] if values[0] is not None else []
        return head + values[1]

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

        return ast.ProtoFile(
            span=file_span, syntax=syntax, items=tuple(items),
            imports=tuple(imports), package=package
        )

    @classmethod
    def build(cls) -> Grammar:
        """Build and cache the proto3 grammar."""
        if cls._cache is not None:
            return cls._cache

        extractor = GrammarExtractor()
        productions = extractor.extract_from_class(cls)

        cls._cache = Grammar(start=File.symbol, productions=tuple(productions))
        return cls._cache

