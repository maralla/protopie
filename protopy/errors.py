from __future__ import annotations

from dataclasses import dataclass

from .spans import Span


@dataclass(slots=True)
class ParseError(Exception):
    span: Span
    message: str
    hint: str | None = None

    def __str__(self) -> str:
        base = f"{self.span.format()}: {self.message}"
        if self.hint:
            return f"{base}\nhint: {self.hint}"
        return base

