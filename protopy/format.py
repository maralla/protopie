from __future__ import annotations

from . import ast as A


def format_proto_file(pf: A.ProtoFile) -> str:
    out: list[str] = []

    if pf.syntax is not None:
        out.append(f'syntax = "{pf.syntax.value}";')
        out.append("")

    # Print imports, package, then the rest preserving relative order otherwise.
    # We keep simple, canonical formatting; spans are not preserved by formatting.
    imports = [it for it in pf.items if isinstance(it, A.Import)]
    package = next((it for it in pf.items if isinstance(it, A.Package)), None)
    others = [it for it in pf.items if not isinstance(it, (A.Import, A.Package, A.Syntax))]

    for imp in imports:
        if imp.modifier:
            out.append(f'import {imp.modifier} "{imp.path}";')
        else:
            out.append(f'import "{imp.path}";')
    if imports:
        out.append("")

    if package is not None:
        out.append(f"package {package.name};")
        out.append("")

    for it in others:
        out.extend(_format_top(it, indent=0))
        out.append("")

    # Trim trailing blank lines
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def _format_top(it: A.TopLevel, *, indent: int) -> list[str]:
    if isinstance(it, A.OptionStmt):
        return [_indent(f"option {_format_option(it.option)};", indent)]
    if isinstance(it, A.Message):
        return _format_message(it, indent=indent)
    if isinstance(it, A.Enum):
        return _format_enum(it, indent=indent)
    if isinstance(it, A.Service):
        return _format_service(it, indent=indent)
    # Imports/package/syntax handled in format_proto_file
    return [_indent(f"/* unsupported top-level node in formatter: {type(it).__name__} */", indent)]


def _format_message(msg: A.Message, *, indent: int) -> list[str]:
    out = [_indent(f"message {msg.name} {{", indent)]
    for elem in msg.body:
        out.extend(_format_message_elem(elem, indent=indent + 2))
    out.append(_indent("}", indent))
    return out


def _format_message_elem(elem: object, *, indent: int) -> list[str]:
    if isinstance(elem, A.OptionStmt):
        return [_indent(f"option {_format_option(elem.option)};", indent)]
    if isinstance(elem, A.Reserved):
        return [_indent(_format_reserved(elem) + ";", indent)]
    if isinstance(elem, A.Field):
        return [_indent(_format_field(elem) + ";", indent)]
    if isinstance(elem, A.Oneof):
        return _format_oneof(elem, indent=indent)
    if isinstance(elem, A.Enum):
        return _format_enum(elem, indent=indent)
    if isinstance(elem, A.Message):
        return _format_message(elem, indent=indent)
    return [_indent(f"/* unsupported message elem: {type(elem).__name__} */", indent)]


def _format_oneof(o: A.Oneof, *, indent: int) -> list[str]:
    out = [_indent(f"oneof {o.name} {{", indent)]
    for f in o.fields:
        out.append(_indent(_format_field(f) + ";", indent + 2))
    out.append(_indent("}", indent))
    return out


def _format_enum(en: A.Enum, *, indent: int) -> list[str]:
    out = [_indent(f"enum {en.name} {{", indent)]
    for elem in en.body:
        if isinstance(elem, A.OptionStmt):
            out.append(_indent(f"option {_format_option(elem.option)};", indent + 2))
        elif isinstance(elem, A.Reserved):
            out.append(_indent(_format_reserved(elem) + ";", indent + 2))
        elif isinstance(elem, A.EnumValue):
            s = f"{elem.name} = {elem.number}"
            if elem.options:
                s += " " + _format_field_options(elem.options)
            out.append(_indent(s + ";", indent + 2))
        elif isinstance(elem, (A.Enum, A.Message)):
            out.extend(_format_message(elem, indent=indent + 2) if isinstance(elem, A.Message) else _format_enum(elem, indent=indent + 2))
        else:
            out.append(_indent(f"/* unsupported enum elem: {type(elem).__name__} */", indent + 2))
    out.append(_indent("}", indent))
    return out


def _format_service(svc: A.Service, *, indent: int) -> list[str]:
    out = [_indent(f"service {svc.name} {{", indent)]
    for elem in svc.body:
        if isinstance(elem, A.OptionStmt):
            out.append(_indent(f"option {_format_option(elem.option)};", indent + 2))
        elif isinstance(elem, A.Rpc):
            out.extend(_format_rpc(elem, indent=indent + 2))
        else:
            out.append(_indent(f"/* unsupported service elem: {type(elem).__name__} */", indent + 2))
    out.append(_indent("}", indent))
    return out


def _format_rpc(r: A.Rpc, *, indent: int) -> list[str]:
    req = _format_type_ref(r.request)
    resp = _format_type_ref(r.response)
    if r.request_stream:
        req = "stream " + req
    if r.response_stream:
        resp = "stream " + resp
    head = _indent(f"rpc {r.name} ({req}) returns ({resp})", indent)
    if not r.options:
        return [head + ";"]
    out = [head + " {"]  # formatter prints RPC body if options exist
    for opt in r.options:
        out.append(_indent(f"option {_format_option(opt.option)};", indent + 2))
    out.append(_indent("}", indent))
    return out


def _format_field(f: A.Field) -> str:
    if f.map_key_type is not None and f.map_value is not None:
        val = _format_type_ref(f.map_value)
        typ = f"map<{f.map_key_type}, {val}>"
        label = ""
    else:
        typ = _format_type_name(f)
        label = "repeated " if f.repeated else ""
    s = f"{label}{typ} {f.name} = {f.number}"
    if f.options:
        s += " " + _format_field_options(f.options)
    return s


def _format_type_name(f: A.Field) -> str:
    if f.scalar_type is not None:
        return f.scalar_type
    if f.type_name is None:
        return "/*missing-type*/"
    return str(f.type_name)


def _format_type_ref(tref: A.TypeRef) -> str:
    if tref.scalar_type is not None:
        return tref.scalar_type
    if tref.type_name is None:
        return "/*missing-type*/"
    return str(tref.type_name)


def _format_field_options(opts: tuple[A.FieldOption, ...]) -> str:
    inner = ", ".join(_format_option(o.option) for o in opts)
    return f"[{inner}]"


def _format_option(o: A.Option) -> str:
    return f"{_format_option_name(o.name)} = {_format_const(o.value)}"


def _format_option_name(nm: A.OptionName) -> str:
    if nm.custom:
        base = str(nm.base)
        if nm.base.absolute:
            base = base[1:]
        suf = ("." + ".".join(nm.suffix)) if nm.suffix else ""
        return f"({base}){suf}"
    return str(nm.base)


def _format_reserved(r: A.Reserved) -> str:
    parts: list[str] = ["reserved"]
    if r.ranges:
        rs: list[str] = []
        for rr in r.ranges:
            if rr.end_is_max:
                rs.append(f"{rr.start} to max")
            elif rr.end is None:
                rs.append(str(rr.start))
            else:
                rs.append(f"{rr.start} to {rr.end}")
        parts.append(", ".join(rs))
    else:
        parts.append(", ".join(f'"{n}"' for n in r.names))
    return " ".join(parts)


def _format_const(c: A.Constant) -> str:
    kind_name = c.kind.name
    if kind_name == "INT":
        return str(c.value)
    if kind_name == "FLOAT":
        return str(c.value)
    if kind_name == "STRING":
        return '"' + str(c.value).replace('"', '\\"') + '"'
    if kind_name in ("true", "false"):
        return "true" if c.value else "false"
    if kind_name == "ident":
        return str(c.value)
    if kind_name == "aggregate":
        fields = []
        for k, v in c.value:  # type: ignore[assignment]
            fields.append(f"{k}: {_format_const(v)}")
        return "{ " + ", ".join(fields) + " }"
    return "/*unknown-const*/"


def _indent(s: str, n: int) -> str:
    return (" " * n) + s

