"""
Shared symbol definitions for grammar and AST.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerminalSymbol:
    """A terminal symbol in the grammar."""
    name: str
    
    def __str__(self) -> str:
        return f"T({self.name})"
    
    def __repr__(self) -> str:
        return f"Terminal({self.name!r})"


@dataclass(frozen=True, slots=True)
class NonTerminalSymbol:
    """A non-terminal symbol in the grammar."""
    name: str
    
    def __str__(self) -> str:
        return f"N({self.name})"
    
    def __repr__(self) -> str:
        return f"NonTerminal({self.name!r})"


# Type alias for any symbol
Symbol = TerminalSymbol | NonTerminalSymbol

