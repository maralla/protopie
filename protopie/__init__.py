"""Protopy: LALR(1) parser for Protocol Buffers (proto3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ast import Import, ProtoFile
from .errors import ErrorDetail, ParseError
from .lexer import tokenize
from .parser import Parser
from .spans import Position, Span


__all__ = [
    "ErrorDetail",
    "ParseError",
    "ParseResult",
    "parse_file",
    "parse_files",
    "parse_source",
]


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Result of parsing multiple files with import resolution."""

    entrypoints: tuple[str, ...]
    files: dict[str, ProtoFile]  # absolute path -> AST


def parse_source(src: str, *, file: str = "<memory>") -> ProtoFile:
    """Parse proto3 source code into an AST.

    Args:
        src: Proto3 source code as a string
        file: Filename for error messages (default: "<memory>")

    Returns:
        ProtoFile: The parsed AST

    Raises:
        ParseError: For syntax or validation errors (holds list of ErrorDetail)

    Examples:
        # Simple usage
        proto_file = parse_source(src)

        # Handle errors
        try:
            proto_file = parse_source(src)
        except ParseError as e:
            print(f"Found {len(e.details)} error(s):")
            for detail in e.details:
                print(f"  - {detail}")

    """
    tokens = tokenize(src, file=file)
    result = Parser.instance().parse(tokens)

    if not isinstance(result, ProtoFile):
        raise TypeError(f"parser returned unexpected value: {type(result)!r}")

    # Patch placeholder span if needed
    if result.span.file == "<unknown>":
        pos_zero = Position(offset=0, line=1, column=1)
        result = ProtoFile(
            span=Span(file=file, start=pos_zero, end=pos_zero),
            items=result.items,
        )

    # Proto3 requires syntax declaration
    if result.syntax is None:
        raise ParseError.detail(
            span=tokens[0].span,
            message="missing syntax declaration",
            hint='add: syntax = "proto3"; at the top of the file',
        )

    # Validate and raise if errors found
    errors = result.validate()
    if errors:
        raise ParseError(errors)
    return result


def parse_file(path: str | Path) -> ProtoFile:
    """Parse a proto3 file into an AST.

    Args:
        path: Path to the .proto file

    Returns:
        ProtoFile: The parsed AST

    Raises:
        ParseError: For syntax or validation errors

    """
    file_path = Path(path).expanduser().resolve()
    source = file_path.read_text(encoding="utf-8")
    return parse_source(source, file=str(file_path))


def _resolve_import(imp: Import, importer: Path, import_roots: list[Path]) -> Path:
    relative_path = Path(imp.path.text)
    candidates = [importer.parent / relative_path] + [root / relative_path for root in import_roots]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    raise ParseError.detail(
        span=imp.span,
        message=f"import not found: {imp.path.text!r}",
        hint="add the directory containing that file to import_paths",
    )


def _load_file_recursive(path: Path, import_roots: list[Path], files: dict[str, ProtoFile]) -> None:
    absolute_path = str(path.resolve())
    if absolute_path in files:
        return

    ast = parse_file(path)
    files[absolute_path] = ast

    for imp in ast.imports:
        resolved = _resolve_import(imp, path, import_roots)
        _load_file_recursive(resolved, import_roots, files)


def parse_files(
    *,
    entrypoints: list[str | Path],
    import_paths: list[str | Path] | None = None,
) -> ParseResult:
    """Parse multiple proto3 files with import resolution.

    Args:
        entrypoints: List of main .proto files to parse
        import_paths: Additional directories to search for imports

    Returns:
        ParseResult containing all parsed files

    Raises:
        ParseError: If any file is invalid or imports cannot be resolved

    """
    import_roots = [Path(p).expanduser().resolve() for p in (import_paths or [])]
    files: dict[str, ProtoFile] = {}

    entry_paths = [Path(p).expanduser().resolve() for p in entrypoints]
    for entry in entry_paths:
        _load_file_recursive(entry, import_roots, files)

    return ParseResult(entrypoints=tuple(str(p) for p in entry_paths), files=files)
