from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .spans import Span


@dataclass(slots=True)
class ErrorDetail:
    """Details about a single error (not an exception itself)."""

    span: Span
    message: str
    hint: str | None = None

    def __str__(self) -> str:
        base = f"{self.span.format()}: {self.message}"
        if self.hint:
            return f"{base}\nhint: {self.hint}"
        return base


class ParseError(Exception):
    """Exception raised when parsing or validating proto3 files.

    Can contain multiple error details for validation errors, or a single
    error detail for syntax errors.
    """

    def __init__(self, details: list[ErrorDetail]) -> None:
        """Initialize with a list of error details.

        Args:
            details: List of ErrorDetail instances

        """
        self.details = details
        error_count = len(details)
        plural = "s" if error_count != 1 else ""
        super().__init__(f"{error_count} error{plural}")

    @classmethod
    def detail(cls, *, span: Span, message: str, hint: str | None = None) -> ParseError:
        """Create a ParseError with a single error detail.

        Convenience method for creating single-error exceptions.

        Args:
            span: Location of the error in source code
            message: Error message
            hint: Optional hint for fixing the error

        Returns:
            ParseError with one ErrorDetail

        Example:
            raise ParseError.detail(
                span=token.span,
                message="unexpected token",
                hint="expected ';'"
            )

        """
        detail = ErrorDetail(span=span, message=message, hint=hint)
        return cls([detail])

    def __str__(self) -> str:
        """Format all errors as a string."""
        if len(self.details) == 1:
            return str(self.details[0])
        lines = [f"{len(self.details)} errors:"]
        lines.extend(f"  - {detail}" for detail in self.details)
        return "\n".join(lines)

