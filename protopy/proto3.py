from __future__ import annotations

"""
Proto3 "spec" in one place:

- **Token policy**: keyword mapping and identifier-compatibility policy
- **Grammar**: `build_proto3_grammar()` producing the LALR(1) grammar used by the parser

This module is meant to be *human scannable*.
"""

from collections.abc import Callable

from . import ast as A
from .errors import ParseError
from .grammar import Grammar, NonTerminal, Production, Symbol, n, t
from .parser import join_span
from .production_dsl import ProductionSink, RuleNt, Sym, eps
from .spans import Position, Span
from .tokens import Token, TokenKind


# ---------------------------------------------------------------------------
# Tokens / keyword policy
# ---------------------------------------------------------------------------

# Lexer keyword mapping (proto3 keywords + booleans).
KEYWORDS: dict[str, TokenKind] = {
    "syntax": TokenKind.SYNTAX,
    "import": TokenKind.IMPORT,
    "package": TokenKind.PACKAGE,
    "option": TokenKind.OPTION,
    "message": TokenKind.MESSAGE,
    "enum": TokenKind.ENUM,
    "service": TokenKind.SERVICE,
    "rpc": TokenKind.RPC,
    "returns": TokenKind.RETURNS,
    "stream": TokenKind.STREAM,
    "oneof": TokenKind.ONEOF,
    "map": TokenKind.MAP,
    "repeated": TokenKind.REPEATED,
    "reserved": TokenKind.RESERVED,
    "to": TokenKind.TO,
    "max": TokenKind.MAX,
    "weak": TokenKind.WEAK,
    "public": TokenKind.PUBLIC,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}

# Some upstream proto3 fixtures use a keyword as an identifier (notably "syntax" as a field name).
# Allowing *too many* keywords here introduces grammar ambiguities (e.g. `stream` in RPC types).
IDENTIFIER_TOKEN_KINDS: tuple[TokenKind, ...] = (TokenKind.IDENT, TokenKind.SYNTAX)

SCALAR_TYPES: set[str] = {
    "double",
    "float",
    "int32",
    "int64",
    "uint32",
    "uint64",
    "sint32",
    "sint64",
    "fixed32",
    "fixed64",
    "sfixed32",
    "sfixed64",
    "bool",
    "string",
    "bytes",
}

# ---------------------------------------------------------------------------
# Grammar (semantic, symbolic)
# ---------------------------------------------------------------------------


def _tok(v: object) -> Token:
    if not isinstance(v, Token):
        raise TypeError(f"expected Token, got {type(v)!r}")
    return v


def _node(tp: type, v: object) -> object:
    if not isinstance(v, tp):
        raise TypeError(f"expected {tp.__name__}, got {type(v)!r}")
    return v


def _as_list(v: object) -> list[object]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    raise TypeError(f"expected list, got {type(v)!r}")


def build_proto3_grammar() -> Grammar[object]:
    # -----------------------------------------------------------------------
    # Symbols (single definition; directly DSL-concatenatable)
    # -----------------------------------------------------------------------
    sink = ProductionSink([])

    def NT(name: str) -> RuleNt:
        return RuleNt(sym=n(name), _sink=sink)

    def T(kind: TokenKind) -> Sym:
        return Sym(sym=t(kind))

    # Terminals
    DOT = T(TokenKind.DOT)
    COMMA = T(TokenKind.COMMA)
    COLON = T(TokenKind.COLON)
    EQ = T(TokenKind.EQ)
    SEMI = T(TokenKind.SEMI)
    LBRACE = T(TokenKind.LBRACE)
    RBRACE = T(TokenKind.RBRACE)
    LBRACKET = T(TokenKind.LBRACKET)
    RBRACKET = T(TokenKind.RBRACKET)
    LPAREN = T(TokenKind.LPAREN)
    RPAREN = T(TokenKind.RPAREN)
    LANGLE = T(TokenKind.LANGLE)
    RANGLE = T(TokenKind.RANGLE)
    INT = T(TokenKind.INT)
    FLOAT = T(TokenKind.FLOAT)
    STRING = T(TokenKind.STRING)
    IDENT = T(TokenKind.IDENT)

    # Keywords
    SYNTAX = T(TokenKind.SYNTAX)
    IMPORT = T(TokenKind.IMPORT)
    PACKAGE = T(TokenKind.PACKAGE)
    OPTION = T(TokenKind.OPTION)
    MESSAGE = T(TokenKind.MESSAGE)
    ENUM = T(TokenKind.ENUM)
    SERVICE = T(TokenKind.SERVICE)
    RPC = T(TokenKind.RPC)
    RETURNS = T(TokenKind.RETURNS)
    STREAM = T(TokenKind.STREAM)
    ONEOF_KW = T(TokenKind.ONEOF)
    MAP = T(TokenKind.MAP)
    REPEATED = T(TokenKind.REPEATED)
    RESERVED = T(TokenKind.RESERVED)
    TO = T(TokenKind.TO)
    MAX = T(TokenKind.MAX)
    WEAK = T(TokenKind.WEAK)
    PUBLIC = T(TokenKind.PUBLIC)
    TRUE = T(TokenKind.TRUE)
    FALSE = T(TokenKind.FALSE)

    # Nonterminals
    File = NT("File")
    Items = NT("Items")
    Item = NT("Item")
    Decl = NT("Decl")
    IdentTok = NT("IdentTok")
    NameTail = NT("NameTail")
    QualifiedName = NT("QualifiedName")
    SyntaxStmt = NT("SyntaxStmt")
    ImportStmt = NT("ImportStmt")
    ImportModOpt = NT("ImportModOpt")
    PackageStmt = NT("PackageStmt")
    OptionStmt = NT("OptionStmt")
    Option = NT("Option")
    OptionName = NT("OptionName")
    OptionSuffix = NT("OptionSuffix")
    Const = NT("Const")
    OptComma = NT("OptComma")
    AggField = NT("AggField")
    AggFields = NT("AggFields")
    AggFieldsTail = NT("AggFieldsTail")
    AggFieldsOpt = NT("AggFieldsOpt")
    Aggregate = NT("Aggregate")
    FieldOption = NT("FieldOption")
    FieldOptionList = NT("FieldOptionList")
    FieldOptionListTail = NT("FieldOptionListTail")
    FieldOptions = NT("FieldOptions")
    FieldOptionsOpt = NT("FieldOptionsOpt")
    TypeNoMap = NT("TypeNoMap")
    MapKeyType = NT("MapKeyType")
    MapType = NT("MapType")
    FieldLabelOpt = NT("FieldLabelOpt")
    Field = NT("Field")
    OneofField = NT("OneofField")
    OneofElem = NT("OneofElem")
    OneofBody = NT("OneofBody")
    Oneof = NT("Oneof")
    ReservedRange = NT("ReservedRange")
    ReservedRangesTail = NT("ReservedRangesTail")
    ReservedRanges = NT("ReservedRanges")
    ReservedNamesTail = NT("ReservedNamesTail")
    ReservedNames = NT("ReservedNames")
    ReservedSpec = NT("ReservedSpec")
    ReservedStmt = NT("ReservedStmt")
    EnumValue = NT("EnumValue")
    EnumElem = NT("EnumElem")
    EnumBody = NT("EnumBody")
    Enum = NT("Enum")
    MessageElem = NT("MessageElem")
    MessageBody = NT("MessageBody")
    Message = NT("Message")
    StreamOpt = NT("StreamOpt")
    RpcType = NT("RpcType")
    RpcBodyElem = NT("RpcBodyElem")
    RpcBody = NT("RpcBody")
    RpcBodyOpt = NT("RpcBodyOpt")
    Rpc = NT("Rpc")
    ServiceElem = NT("ServiceElem")
    ServiceBody = NT("ServiceBody")
    Service = NT("Service")

    # -----------------------------------------------------------------------
    # Semantic actions (named, reusable, wrapped with Act for bracket syntax)
    # -----------------------------------------------------------------------
    def act_passthrough(xs: list[object]) -> object:
        return xs[0]

    def act_none(xs: list[object]) -> object:
        return None

    def act_empty_list(xs: list[object]) -> object:
        return []

    def act_list_cons(xs: list[object]) -> object:
        # [head] + tail
        return [xs[0]] + _as_list(xs[1])

    def act_bool_true(xs: list[object]) -> object:
        return True

    def act_bool_false(xs: list[object]) -> object:
        return False

    def act_const_int(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0]), kind="int", value=int(_tok(xs[0]).lexeme))

    def act_const_float(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0]), kind="float", value=float(_tok(xs[0]).lexeme))

    def act_const_string(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0]), kind="string", value=_tok(xs[0]).lexeme)

    def act_const_true(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0]), kind="bool", value=True)

    def act_const_false(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0]), kind="bool", value=False)

    def act_const_ident(xs: list[object]) -> object:
        return A.Constant(span=_node(A.QualifiedName, xs[0]).span, kind="ident", value=xs[0])

    def act_name_tail(xs: list[object]) -> object:
        return [_tok(xs[1])] + _as_list(xs[2])

    def act_qname_abs(xs: list[object]) -> object:
        tail = _as_list(xs[2])
        last = tail[-1] if tail else xs[1]
        return A.QualifiedName(
            span=join_span(xs[0], last),
            absolute=True,
            parts=tuple([_tok(xs[1]).lexeme] + [_tok(tk).lexeme for tk in tail]),
        )

    def act_qname_rel(xs: list[object]) -> object:
        tail = _as_list(xs[1])
        last = tail[-1] if tail else xs[0]
        return A.QualifiedName(
            span=join_span(xs[0], last),
            absolute=False,
            parts=tuple([_tok(xs[0]).lexeme] + [_tok(tk).lexeme for tk in tail]),
        )

    def act_agg_field(xs: list[object]) -> object:
        return (_tok(xs[0]).lexeme, xs[2])

    def act_agg_tail(xs: list[object]) -> object:
        return [xs[0]] + _as_list(xs[1])

    def act_agg_fields(xs: list[object]) -> object:
        return [xs[0]] + _as_list(xs[1])

    def act_aggregate(xs: list[object]) -> object:
        return A.Constant(span=join_span(xs[0], xs[2]), kind="aggregate", value=tuple(xs[1]))

    def act_opt_suffix(xs: list[object]) -> object:
        return [_tok(xs[1])] + _as_list(xs[2])

    def act_opt_name_plain(xs: list[object]) -> object:
        return A.OptionName(span=_node(A.QualifiedName, xs[0]).span, custom=False, base=xs[0], suffix=tuple())

    def act_opt_name_custom(xs: list[object]) -> object:
        suf = _as_list(xs[3])
        last = suf[-1] if suf else xs[2]
        return A.OptionName(
            span=join_span(xs[0], last),
            custom=True,
            base=xs[1],
            suffix=tuple(_tok(tk).lexeme for tk in suf),
        )

    def act_option(xs: list[object]) -> object:
        return A.Option(span=join_span(xs[0], xs[2]), name=xs[0], value=xs[2])

    def act_option_stmt(xs: list[object]) -> object:
        return A.OptionStmt(span=join_span(xs[0], xs[2]), option=xs[1])

    def act_import_mod_weak(xs: list[object]) -> object:
        return "weak"

    def act_import_mod_public(xs: list[object]) -> object:
        return "public"

    def act_import_mod_none(xs: list[object]) -> object:
        return None

    def act_syntax_stmt(xs: list[object]) -> object:
        lit = _tok(xs[2]).lexeme
        if lit != "proto3":
            raise ParseError(span=_tok(xs[2]).span, message="only proto3 syntax is supported", hint='use: syntax = "proto3";')
        return A.Syntax(span=join_span(xs[0], xs[3]), value=lit)

    def act_import_stmt(xs: list[object]) -> object:
        return A.Import(span=join_span(xs[0], xs[3]), path=_tok(xs[2]).lexeme, modifier=xs[1])

    def act_package_stmt(xs: list[object]) -> object:
        return A.Package(span=join_span(xs[0], xs[2]), name=xs[1])

    def act_field_option(xs: list[object]) -> object:
        return A.FieldOption(span=_node(A.Option, xs[0]).span, option=xs[0])

    def act_field_opt_tail(xs: list[object]) -> object:
        return [xs[1]] + _as_list(xs[2])

    def act_field_opt_list(xs: list[object]) -> object:
        return [xs[0]] + _as_list(xs[1])

    def act_field_options(xs: list[object]) -> object:
        return tuple(xs[1])

    def act_field_options_opt(xs: list[object]) -> object:
        return xs[0]

    def act_field_options_opt_empty(xs: list[object]) -> object:
        return tuple()

    def act_type_no_map(xs: list[object]) -> object:
        return xs[0]

    def act_map_key(xs: list[object]) -> object:
        return _tok(xs[0])

    def act_map_type(xs: list[object]) -> object:
        return (join_span(xs[0], xs[5]), xs[2], xs[4])

    def act_field_label_rep(xs: list[object]) -> object:
        return True

    def act_field_label_none(xs: list[object]) -> object:
        return False

    def _field_from_qname(xs: list[object]) -> A.Field:
        repeated = bool(xs[0])
        type_q: A.QualifiedName = xs[1]
        name = _tok(xs[2]).lexeme
        number = int(_tok(xs[4]).lexeme)
        options = xs[5]
        scalar = None
        type_name = type_q
        if (not type_q.absolute) and len(type_q.parts) == 1 and type_q.parts[0] in SCALAR_TYPES:
            scalar = type_q.parts[0]
            type_name = None
        return A.Field(
            span=join_span(xs[0] if isinstance(xs[0], Token) else xs[1], xs[6]),
            name=name,
            number=number,
            type_name=type_name,
            scalar_type=scalar,
            repeated=repeated,
            options=tuple(options),
        )

    def _field_from_map(xs: list[object]) -> A.Field:
        repeated = bool(xs[0])
        (sp, key_tok, val_q) = xs[1]
        key_t = _tok(key_tok).lexeme
        name = _tok(xs[2]).lexeme
        number = int(_tok(xs[4]).lexeme)
        options = xs[5]
        if repeated:
            raise ParseError(span=join_span(xs[0], xs[0]), message="map fields cannot be repeated", hint="remove 'repeated' (map fields are implicitly repeated)")
        if key_t not in {"int32","int64","uint32","uint64","sint32","sint64","fixed32","fixed64","sfixed32","sfixed64","bool","string"}:
            raise ParseError(span=_tok(key_tok).span, message=f"invalid map key type: {key_t}", hint="map keys must be an integral type, bool, or string")
        scalar = None
        type_name = val_q
        if (not val_q.absolute) and len(val_q.parts) == 1 and val_q.parts[0] in SCALAR_TYPES:
            scalar = val_q.parts[0]
            type_name = None
        full_span = Span(file=sp.file, start=sp.start, end=_tok(xs[6]).span.end)
        return A.Field(
            span=full_span,
            name=name,
            number=number,
            map_key_type=key_t,
            map_value=A.TypeRef(span=sp, type_name=type_name, scalar_type=scalar),
            options=tuple(options),
        )

    def act_field_qname(xs: list[object]) -> object:
        return _field_from_qname([xs[0], xs[1], xs[2], xs[3], xs[4], xs[5], xs[6]])

    def act_field_map(xs: list[object]) -> object:
        return _field_from_map([xs[0], xs[1], xs[2], xs[3], xs[4], xs[5], xs[6]])

    def act_oneof_field(xs: list[object]) -> object:
        qn = _node(A.QualifiedName, xs[0])
        scalar = None
        type_name = qn
        if (not qn.absolute) and len(qn.parts) == 1 and qn.parts[0] in SCALAR_TYPES:
            scalar = qn.parts[0]
            type_name = None
        return A.Field(
            span=join_span(xs[0], xs[5]),
            name=_tok(xs[1]).lexeme,
            number=int(_tok(xs[3]).lexeme),
            type_name=type_name,
            scalar_type=scalar,
            options=tuple(xs[4]),
        )

    def act_oneof_body(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + [x for x in _as_list(xs[1]) if x is not None]

    def act_oneof(xs: list[object]) -> object:
        return A.Oneof(span=join_span(xs[0], xs[4]), name=_tok(xs[1]).lexeme, fields=tuple(xs[3]))

    def act_reserved_single(xs: list[object]) -> object:
        return A.ReservedRange(span=join_span(xs[0]), start=int(_tok(xs[0]).lexeme))

    def act_reserved_range(xs: list[object]) -> object:
        return A.ReservedRange(span=join_span(xs[0], xs[2]), start=int(_tok(xs[0]).lexeme), end=int(_tok(xs[2]).lexeme))

    def act_reserved_max(xs: list[object]) -> object:
        return A.ReservedRange(span=join_span(xs[0], xs[2]), start=int(_tok(xs[0]).lexeme), end_is_max=True, end=None)

    def act_rr_tail(xs: list[object]) -> object:
        return [xs[1]] + _as_list(xs[2])

    def act_rr(xs: list[object]) -> object:
        return [xs[0]] + _as_list(xs[1])

    def act_rn_tail(xs: list[object]) -> object:
        return [_tok(xs[1]).lexeme] + _as_list(xs[2])

    def act_rn(xs: list[object]) -> object:
        return [_tok(xs[0]).lexeme] + _as_list(xs[1])

    def act_rs_ranges(xs: list[object]) -> object:
        return ("ranges", xs[0])

    def act_rs_names(xs: list[object]) -> object:
        return ("names", xs[0])

    def act_reserved_stmt(xs: list[object]) -> object:
        return A.Reserved(
            span=join_span(xs[0], xs[2]),
            ranges=tuple(xs[1][1]) if xs[1][0] == "ranges" else tuple(),
            names=tuple(xs[1][1]) if xs[1][0] == "names" else tuple(),
        )

    def act_enum_value(xs: list[object]) -> object:
        return A.EnumValue(
            span=join_span(xs[0], xs[4]),
            name=_tok(xs[0]).lexeme,
            number=int(_tok(xs[2]).lexeme),
            options=tuple(xs[3]),
        )

    def act_enum_body(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + _as_list(xs[1])

    def act_enum(xs: list[object]) -> object:
        return A.Enum(span=join_span(xs[0], xs[4]), name=_tok(xs[1]).lexeme, body=tuple(xs[3]))

    def act_msg_body(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + _as_list(xs[1])

    def act_message(xs: list[object]) -> object:
        return A.Message(span=join_span(xs[0], xs[4]), name=_tok(xs[1]).lexeme, body=tuple(xs[3]))

    def act_stream_yes(xs: list[object]) -> object:
        return True

    def act_stream_no(xs: list[object]) -> object:
        return False

    def act_type_ref(span: object, q: A.QualifiedName) -> A.TypeRef:
        scalar = None
        type_name = q
        if (not q.absolute) and len(q.parts) == 1 and q.parts[0] in SCALAR_TYPES:
            scalar = q.parts[0]
            type_name = None
        return A.TypeRef(span=span, type_name=type_name, scalar_type=scalar)

    def act_rpc_body(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + _as_list(xs[1])

    def act_rpc_bodyopt_semi(xs: list[object]) -> object:
        return tuple()

    def act_rpc_bodyopt_block(xs: list[object]) -> object:
        return tuple(xs[1])

    def act_rpc(xs: list[object]) -> object:
        return A.Rpc(
            span=join_span(xs[0], xs[-1] if isinstance(xs[-1], Token) else _tok(xs[10])),
            name=_tok(xs[1]).lexeme,
            request=act_type_ref(join_span(xs[2], xs[5]), xs[4]),
            response=act_type_ref(join_span(xs[7], xs[10]), xs[9]),
            request_stream=bool(xs[3]),
            response_stream=bool(xs[8]),
            options=tuple([x for x in xs[11] if isinstance(x, A.OptionStmt)]),
        )

    def act_svc_body(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + _as_list(xs[1])

    def act_service(xs: list[object]) -> object:
        return A.Service(span=join_span(xs[0], xs[4]), name=_tok(xs[1]).lexeme, body=tuple(xs[3]))

    def act_items(xs: list[object]) -> object:
        head = [xs[0]] if xs[0] is not None else []
        return head + _as_list(xs[1])

    def act_file(xs: list[object]) -> object:
        items = [x for x in xs[0] if x is not None]
        syntax: A.Syntax | None = None
        imports: list[A.Import] = []
        package: A.Package | None = None
        for it in items:
            if isinstance(it, A.Syntax):
                if syntax is not None:
                    raise ParseError(span=it.span, message="duplicate syntax declaration")
                syntax = it
            elif isinstance(it, A.Import):
                imports.append(it)
            elif isinstance(it, A.Package):
                if package is not None:
                    raise ParseError(span=it.span, message="duplicate package declaration")
                package = it
        if items:
            sp = join_span(items[0], items[-1])
        else:
            sp = Span(file="<unknown>", start=Position(0, 1, 1), end=Position(0, 1, 1))
        return A.ProtoFile(span=sp, syntax=syntax, items=tuple(items), imports=tuple(imports), package=package)

    # -----------------------------------------------------------------------
    # Productions (single explicit block; "semantic grammar" style)
    # -----------------------------------------------------------------------

    # IdentTok
    IdentTok |= IDENT | SYNTAX @ act_passthrough

    # QualifiedName
    NameTail |= DOT & IdentTok & NameTail @ act_name_tail
    NameTail |= eps() @ act_empty_list
    QualifiedName |= DOT & IdentTok & NameTail @ act_qname_abs
    QualifiedName |= IdentTok & NameTail @ act_qname_rel

    # Const / aggregate
    Const |= INT @ act_const_int
    Const |= FLOAT @ act_const_float
    Const |= STRING @ act_const_string
    Const |= TRUE @ act_const_true
    Const |= FALSE @ act_const_false
    Const |= QualifiedName @ act_const_ident
    Const |= Aggregate @ act_passthrough

    OptComma |= COMMA @ act_bool_true
    OptComma |= eps() @ act_bool_false

    AggField |= IdentTok & COLON & Const & OptComma @ act_agg_field
    AggFieldsTail |= AggField & AggFieldsTail @ act_agg_tail
    AggFieldsTail |= eps() @ act_empty_list
    AggFields |= AggField & AggFieldsTail @ act_agg_fields
    AggFieldsOpt |= AggFields @ act_passthrough
    AggFieldsOpt |= eps() @ act_empty_list
    Aggregate |= LBRACE & AggFieldsOpt & RBRACE @ act_aggregate

    # Options
    OptionSuffix |= DOT & IdentTok & OptionSuffix @ act_opt_suffix
    OptionSuffix |= eps() @ act_empty_list
    OptionName |= QualifiedName @ act_opt_name_plain
    OptionName |= LPAREN & QualifiedName & RPAREN & OptionSuffix @ act_opt_name_custom
    Option |= OptionName & EQ & Const @ act_option
    OptionStmt |= OPTION & Option & SEMI @ act_option_stmt

    # Syntax / import / package
    SyntaxStmt |= SYNTAX & EQ & STRING & SEMI @ act_syntax_stmt
    ImportModOpt |= WEAK @ act_import_mod_weak
    ImportModOpt |= PUBLIC @ act_import_mod_public
    ImportModOpt |= eps() @ act_import_mod_none
    ImportStmt |= IMPORT & ImportModOpt & STRING & SEMI @ act_import_stmt
    PackageStmt |= PACKAGE & QualifiedName & SEMI @ act_package_stmt

    # Field options
    FieldOption |= Option @ act_field_option
    FieldOptionListTail |= COMMA & FieldOption & FieldOptionListTail @ act_field_opt_tail
    FieldOptionListTail |= eps() @ act_empty_list
    FieldOptionList |= FieldOption & FieldOptionListTail @ act_field_opt_list
    FieldOptions |= LBRACKET & FieldOptionList & RBRACKET @ act_field_options
    FieldOptionsOpt |= FieldOptions @ act_field_options_opt
    FieldOptionsOpt |= eps() @ act_field_options_opt_empty

    # Types / fields
    TypeNoMap |= QualifiedName @ act_type_no_map
    MapKeyType |= IdentTok @ act_map_key
    MapType |= MAP & LANGLE & MapKeyType & COMMA & TypeNoMap & RANGLE @ act_map_type
    FieldLabelOpt |= REPEATED @ act_field_label_rep
    FieldLabelOpt |= eps() @ act_field_label_none
    Field |= FieldLabelOpt & QualifiedName & IdentTok & EQ & INT & FieldOptionsOpt & SEMI @ act_field_qname
    Field |= FieldLabelOpt & MapType & IdentTok & EQ & INT & FieldOptionsOpt & SEMI @ act_field_map

    # Oneof
    OneofField |= QualifiedName & IdentTok & EQ & INT & FieldOptionsOpt & SEMI @ act_oneof_field
    OneofElem |= OneofField @ act_passthrough
    OneofElem |= SEMI @ act_none
    OneofBody |= OneofElem & OneofBody @ act_oneof_body
    OneofBody |= eps() @ act_empty_list
    Oneof |= ONEOF_KW & IDENT & LBRACE & OneofBody & RBRACE @ act_oneof

    # Reserved
    ReservedRange |= INT @ act_reserved_single
    ReservedRange |= INT & TO & INT @ act_reserved_range
    ReservedRange |= INT & TO & MAX @ act_reserved_max
    ReservedRangesTail |= COMMA & ReservedRange & ReservedRangesTail @ act_rr_tail
    ReservedRangesTail |= eps() @ act_empty_list
    ReservedRanges |= ReservedRange & ReservedRangesTail @ act_rr
    ReservedNamesTail |= COMMA & STRING & ReservedNamesTail @ act_rn_tail
    ReservedNamesTail |= eps() @ act_empty_list
    ReservedNames |= STRING & ReservedNamesTail @ act_rn
    ReservedSpec |= ReservedRanges @ act_rs_ranges
    ReservedSpec |= ReservedNames @ act_rs_names
    ReservedStmt |= RESERVED & ReservedSpec & SEMI @ act_reserved_stmt

    # Enum
    EnumValue |= IdentTok & EQ & INT & FieldOptionsOpt & SEMI @ act_enum_value
    EnumElem |= EnumValue | OptionStmt | ReservedStmt @ act_passthrough
    EnumElem |= SEMI @ act_none
    EnumBody |= EnumElem & EnumBody @ act_enum_body
    EnumBody |= eps() @ act_empty_list
    Enum |= ENUM & IdentTok & LBRACE & EnumBody & RBRACE @ act_enum

    # Message
    MessageElem |= Field | Oneof | Enum | Message | OptionStmt | ReservedStmt @ act_passthrough
    MessageElem |= SEMI @ act_none
    MessageBody |= MessageElem & MessageBody @ act_msg_body
    MessageBody |= eps() @ act_empty_list
    Message |= MESSAGE & IdentTok & LBRACE & MessageBody & RBRACE @ act_message

    # Service / RPC
    StreamOpt |= STREAM @ act_stream_yes
    StreamOpt |= eps() @ act_stream_no
    RpcType |= QualifiedName @ act_passthrough
    RpcBodyElem |= OptionStmt @ act_passthrough
    RpcBodyElem |= SEMI @ act_none
    RpcBody |= RpcBodyElem & RpcBody @ act_rpc_body
    RpcBody |= eps() @ act_empty_list
    RpcBodyOpt |= SEMI @ act_rpc_bodyopt_semi
    RpcBodyOpt |= LBRACE & RpcBody & RBRACE @ act_rpc_bodyopt_block
    Rpc |= (RPC & IdentTok
            & LPAREN & StreamOpt & RpcType & RPAREN
            & RETURNS
            & LPAREN & StreamOpt & RpcType & RPAREN
            & RpcBodyOpt) @ act_rpc
    ServiceElem |= Rpc | OptionStmt @ act_passthrough
    ServiceElem |= SEMI @ act_none
    ServiceBody |= ServiceElem & ServiceBody @ act_svc_body
    ServiceBody |= eps() @ act_empty_list
    Service |= SERVICE & IdentTok & LBRACE & ServiceBody & RBRACE @ act_service

    # Top-level
    Decl |= Message | Enum | Service @ act_passthrough
    Item |= SyntaxStmt | ImportStmt | PackageStmt | OptionStmt | Decl @ act_passthrough
    Item |= SEMI @ act_none
    Items |= Item & Items @ act_items
    Items |= eps() @ act_empty_list
    File |= Items @ act_file

    return Grammar(start=File.sym, productions=tuple(sink.productions))

