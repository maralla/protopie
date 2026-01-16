from __future__ import annotations

import hashlib
import random
import string
from pathlib import Path

from protopie import parse_file, parse_files


# ruff: noqa: PLR2004, S311, TC003, PERF401, D103, S101
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


def generate_corpus_files(*, seed: int, count: int) -> list[tuple[str, str]]:
    """Generate a deterministic corpus as a file set.

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


def test_generated_corpus_on_disk_parse_and_hash(tmp_path: Path) -> None:
    # Large enough to be meaningful, small enough to keep CI fast.
    seed = 1
    count = 300

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    files = generate_corpus_files(seed=seed, count=count)
    for rel, src in files:
        (corpus_dir / rel).write_text(src, encoding="utf-8")

    # parse_file across the whole corpus (exercises file IO)
    h = hashlib.sha256()
    entrypoints: list[Path] = []
    for rel, _ in files:
        p = corpus_dir / rel
        ast = parse_file(p)
        formatted = ast.format()
        h.update(formatted.encode("utf-8"))
        h.update(b"\n---\n")
        # also check format->parse stability
        ast2 = parse_file(_write_tmp(corpus_dir, rel + ".fmt", formatted))
        assert ast2.format() == formatted
        entrypoints.append(p)

    # parse_files import resolution (imports reference earlier corpus files)
    res = parse_files(entrypoints=[entrypoints[-1]], import_paths=[corpus_dir])
    assert len(res.files) >= 1

    # Snapshot the corpus behavior by hash (update intentionally only).
    # If this changes unexpectedly, something changed in parsing/formatting semantics.
    assert h.hexdigest() == "ee1b6cdea9fd6b4444980f4e5b3b263501b580435b2e27e874614bfdb7159422"


def _write_tmp(root: Path, name: str, content: str) -> Path:
    p = root / name
    p.write_text(content, encoding="utf-8")
    return p
