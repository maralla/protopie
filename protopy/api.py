from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ast import Import, ProtoFile
from .errors import ParseError
from .lexer import tokenize
from .parser import Parser
from .grammar import GrammarBuilder
from .spans import Position, Span


_PARSER: Parser | None = None


def _get_parser() -> Parser:
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser.for_grammar(GrammarBuilder.build())
    return _PARSER


@dataclass(frozen=True, slots=True)
class ParseResult:
    entrypoints: tuple[str, ...]
    files: dict[str, ProtoFile]  # absolute path -> AST


def parse_source(src: str, *, file: str = "<memory>") -> ProtoFile:
    toks = tokenize(src, file=file)
    out = _get_parser().parse(toks)
    if not isinstance(out, ProtoFile):
        raise RuntimeError(f"parser returned unexpected value: {type(out)!r}")

    # Patch placeholder span if needed.
    if out.span.file == "<unknown>":
        pos0 = Position(offset=0, line=1, column=1)
        out = ProtoFile(
            span=Span(file=file, start=pos0, end=pos0),
            syntax=out.syntax,
            items=out.items,
            imports=out.imports,
            package=out.package,
        )

    # Proto3 requires syntax, enforce here so error spans are good (we have EOF token).
    if out.syntax is None:
        raise ParseError(
            span=toks[0].span,
            message="missing syntax declaration",
            hint='add: syntax = "proto3"; at the top of the file',
        )
    return out


def parse_file(path: str | Path) -> ProtoFile:
    p = Path(path).expanduser().resolve()
    src = p.read_text(encoding="utf-8")
    return parse_source(src, file=str(p))


def parse_files(
    *,
    entrypoints: list[str | Path],
    import_paths: list[str | Path] | None = None,
) -> ParseResult:
    roots = [Path(p).expanduser().resolve() for p in (import_paths or [])]
    files: dict[str, ProtoFile] = {}

    def resolve_import(imp: Import, importer: Path) -> Path:
        rel = Path(imp.path)
        candidates = [importer.parent / rel] + [r / rel for r in roots]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()
        raise ParseError(
            span=imp.span,
            message=f"import not found: {imp.path!r}",
            hint="add the directory containing that file to import_paths",
        )

    def load(p: Path) -> None:
        ap = str(p.resolve())
        if ap in files:
            return
        ast = parse_file(p)
        files[ap] = ast
        for imp in ast.imports:
            load(resolve_import(imp, p))

    eps = [Path(p).expanduser().resolve() for p in entrypoints]
    for e in eps:
        load(e)

    return ParseResult(entrypoints=tuple(str(p) for p in eps), files=files)

