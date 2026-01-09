from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """A concrete source position.

    Offsets are 0-based; line/column are 1-based for user-facing messages.
    """

    offset: int
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Span:
    """Half-open span [start, end) in a single file."""

    file: str
    start: Position
    end: Position

    def format(self) -> str:
        return f"{self.file}:{self.start.line}:{self.start.column}"

