from __future__ import annotations

from typing import cast


class _Meta(type):
    symbol_name: str

    def __repr__(cls) -> str:
        return cls.__name__

    def is_terminal(cls) -> bool:
        return issubclass(cls, Terminal)

    def is_nonterminal(cls) -> bool:
        return issubclass(cls, NonTerminal)

    def as_terminal(cls) -> type[Terminal]:
        """Return self as Terminal type, raising TypeError if not one.

        Uses cast() because after the runtime check, cls is guaranteed to be
        a Terminal type, but mypy cannot infer this from the is_terminal() check.
        """
        if not cls.is_terminal():
            msg = f"{cls} is not a Terminal"
            raise TypeError(msg)
        return cast("type[Terminal]", cls)

    def as_nonterminal(cls) -> type[NonTerminal]:
        """Return self as NonTerminal type, raising TypeError if not one.

        Uses cast() because after the runtime check, cls is guaranteed to be
        a NonTerminal type, but mypy cannot infer this from the is_nonterminal() check.
        """
        if not cls.is_nonterminal():
            msg = f"{cls} is not a NonTerminal"
            raise TypeError(msg)
        return cast("type[NonTerminal]", cls)


class Terminal(metaclass=_Meta):
    """Base class for terminal symbols in the grammar.

    Examples:
        class ENUM(Terminal, name="enum"): pass
        class IDENT(Terminal): pass  # name defaults to "IDENT"

    """

    name: str

    def __init_subclass__(cls, name: str | None = None, **kwargs: object) -> None:
        """Automatically set name from class name if not provided."""
        if name is not None:
            cls.name = name
        elif not hasattr(cls, 'name'):
            cls.name = cls.__name__

        cls.symbol_name = cls.name

        super().__init_subclass__(**kwargs)


class NonTerminal(metaclass=_Meta):
    """Base class for non-terminal symbols in the grammar."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Automatically set symbol_name from class name."""
        super().__init_subclass__(**kwargs)
        cls.symbol_name = cls.__name__
        # Note: Do not set cls.name here as it conflicts with dataclass fields


# Type alias for symbols: Terminal and NonTerminal types (classes)
Symbol = type[Terminal] | type[NonTerminal]
