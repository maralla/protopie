from __future__ import annotations

import random
import string


_KEYWORDS = {
    "import",
    "package",
    "option",
    "message",
    "enum",
    "service",
    "rpc",
    "returns",
    "stream",
    "oneof",
    "map",
    "repeated",
    "reserved",
    "to",
    "max",
    "weak",
    "public",
    "true",
    "false",
}

_SCALARS = ["int32", "int64", "uint32", "uint64", "bool", "string", "bytes"]
_MAP_KEYS = ["int32", "int64", "uint32", "uint64", "bool", "string"]


def _ident(r: random.Random, *, allow_keyword_syntax: bool = False) -> str:
    head = r.choice(string.ascii_letters + "_")
    tail = "".join(
        r.choice(string.ascii_letters + string.digits + "_") for _ in range(r.randint(0, 10))
    )
    s = head + tail
    if allow_keyword_syntax and r.random() < 0.02:
        return "syntax"
    if s in _KEYWORDS:
        return s + "_"
    return s


def generate_proto_sources(*, seed: int, count: int) -> list[str]:
    r = random.Random(seed)
    return [_gen_one(r) for _ in range(count)]

def generate_corpus_files(*, seed: int, count: int) -> list[tuple[str, str]]:
    """Generate a deterministic corpus as a *file set*.

    Returns a list of (relative_path, source).

    - File names are stable: `case_000000.proto`, ...
    - Imports (when present) reference other files within the same corpus.
    """
    r = random.Random(seed)
    names = [f"case_{i:06d}.proto" for i in range(count)]
    srcs: list[str] = []
    # First generate without worrying about import existence.
    for _ in range(count):
        srcs.append(_gen_one(r))

    # Rewrite imports to point at existing corpus files (deterministic).
    fixed: list[tuple[str, str]] = []
    for i, src in enumerate(srcs):
        lines = src.splitlines()
        out: list[str] = []
        for line in lines:
            if line.startswith('import "') and line.endswith('";'):
                # Import an earlier file to avoid cycles; if none exist, drop import.
                if i == 0:
                    continue
                target = names[r.randrange(0, i)]
                out.append(f'import "{target}";')
            else:
                out.append(line)
        fixed.append((names[i], "\n".join(out) + ("\n" if not out or out[-1] != "" else "")))
    return fixed


def _gen_one(r: random.Random) -> str:
    parts: list[str] = ['syntax = "proto3";', ""]

    if r.random() < 0.6:
        pkg_parts = [_ident(r) for _ in range(r.randint(1, 4))]
        parts.append("package " + ".".join(pkg_parts) + ";")
        parts.append("")

    for _ in range(r.randint(0, 3)):
        p = _ident(r) + ".proto"
        parts.append(f'import "{p}";')
    if parts[-1].startswith("import "):
        parts.append("")

    for _ in range(r.randint(0, 2)):
        name = _ident(r)
        val = _string_lit(r)
        parts.append(f"option {name} = {val};")
    if parts[-1].startswith("option "):
        parts.append("")

    decls: list[str] = []
    for _ in range(r.randint(1, 4)):
        k = r.random()
        if k < 0.65:
            decls.append(_gen_message(r))
        elif k < 0.85:
            decls.append(_gen_enum(r))
        else:
            decls.append(_gen_service(r))
    parts.extend(decls)
    parts.append("")
    return "\n".join(parts)


def _string_lit(r: random.Random) -> str:
    alphabet = string.ascii_letters + string.digits + "_-/"
    s = "".join(r.choice(alphabet) for _ in range(r.randint(0, 24)))
    return '"' + s + '"'


def _gen_enum(r: random.Random) -> str:
    name = _ident(r)
    lines = [f"enum {name} {{"]
    n = r.randint(1, 8)
    # Proto3 requires the first enum value to be 0
    vname = _ident(r)
    lines.append(f"  {vname} = 0;")
    value = 1
    for _ in range(n - 1):
        vname = _ident(r)
        value += r.randint(0, 3)
        lines.append(f"  {vname} = {value};")
        value += 1
    lines.append("}")
    return "\n".join(lines)


def _gen_message(r: random.Random) -> str:
    name = _ident(r)
    lines = [f"message {name} {{"]

    # Track reserved field number ranges to avoid conflicts
    reserved_end = 0
    if r.random() < 0.25:
        a = r.randint(1, 10)
        b = a + r.randint(0, 5)
        lines.append(f"  reserved {a} to {b};")
        reserved_end = b
    if r.random() < 0.15:
        lines.append(f'  reserved "{_ident(r)}";')

    # Start field numbering after any reserved ranges
    field_no = max(1, reserved_end + 1)
    for _ in range(r.randint(0, 10)):
        fname = _ident(r, allow_keyword_syntax=True)
        if r.random() < 0.15:
            key = r.choice(_MAP_KEYS)
            val = r.choice(_SCALARS)
            lines.append(f"  map<{key}, {val}> {fname} = {field_no};")
        else:
            rep = "repeated " if (r.random() < 0.25) else ""
            typ = r.choice(_SCALARS)
            lines.append(f"  {rep}{typ} {fname} = {field_no};")
        field_no += 1

    if r.random() < 0.2:
        oname = _ident(r)
        lines.append(f"  oneof {oname} {{")
        for _ in range(r.randint(1, 4)):
            typ = r.choice(_SCALARS)
            fname = _ident(r, allow_keyword_syntax=True)
            lines.append(f"    {typ} {fname} = {field_no};")
            field_no += 1
        lines.append("  }")

    if r.random() < 0.2:
        lines.append(_indent(_gen_enum(r), 2))
    if r.random() < 0.15:
        nested = _ident(r)
        lines.append(f"  message {nested} {{")
        lines.append(f"    string {_ident(r)} = 1;")
        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)


def _gen_service(r: random.Random) -> str:
    name = _ident(r)
    lines = [f"service {name} {{"]
    for _ in range(r.randint(1, 5)):
        m = _ident(r)
        req = r.choice(["google.protobuf.Empty", "string", "bytes", "int32"])
        resp = r.choice(["google.protobuf.Empty", "string", "bytes", "int32"])
        req_s = ("stream " if r.random() < 0.15 else "") + req
        resp_s = ("stream " if r.random() < 0.15 else "") + resp
        lines.append(f"  rpc {m} ({req_s}) returns ({resp_s});")
    lines.append("}")
    return "\n".join(lines)


def _indent(s: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line if line else line for line in s.splitlines())

