from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerminalSymbol:
    """A terminal symbol in the grammar."""
    name: str

    def __str__(self) -> str:
        return f"T({self.name})"

    def __repr__(self) -> str:
        return f"Terminal({self.name!r})"

    def __eq__(self, other: Symbol | TerminalType | NonTerminalType):
        if isinstance(other, Symbol):
            return self.name == other.name

        return self.name == other.symbol.name


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


class TerminalType:
    symbol: TerminalSymbol


class NonTerminalType:
    symbol: NonTerminalSymbol


def Terminal(name: str) -> type[TerminalType]:
    """
    Create a terminal type that can be used in annotations.

    Returns a type class with:
    - symbol attribute containing the runtime symbol instance
    - name attribute for convenient access
    """
    instance = TerminalSymbol(name)

    class _T(TerminalType):
        symbol = instance
        name = instance.name

    _T.__name__ = name
    _T.__qualname__ = name
    return _T


def NonTerminal(name: str) -> type[NonTerminalType]:
    """
    Create a nonterminal type that can be used in annotations.

    Returns a type class with:
    - symbol attribute containing the runtime symbol instance
    - name attribute for convenient access
    - __getitem__ to support generic return types like NonTerminal[ast.Node]
    """
    instance = NonTerminalSymbol(name)

    class _NT(NonTerminalType):
        symbol = instance
        name = instance.name

        def __class_getitem__(cls, item):
            """Support generic syntax: ServiceElem[ast.Service]"""
            return cls

    _NT.__name__ = name
    _NT.__qualname__ = name
    return _NT
