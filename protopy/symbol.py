from __future__ import annotations

from typing import cast


# Proto3 scalar type constants
SCALAR_DOUBLE = "double"
SCALAR_FLOAT = "float"
SCALAR_INT32 = "int32"
SCALAR_INT64 = "int64"
SCALAR_UINT32 = "uint32"
SCALAR_UINT64 = "uint64"
SCALAR_SINT32 = "sint32"
SCALAR_SINT64 = "sint64"
SCALAR_FIXED32 = "fixed32"
SCALAR_FIXED64 = "fixed64"
SCALAR_SFIXED32 = "sfixed32"
SCALAR_SFIXED64 = "sfixed64"
SCALAR_BOOL = "bool"
SCALAR_STRING = "string"
SCALAR_BYTES = "bytes"

# All valid scalar types in proto3
SCALAR_TYPES = frozenset([
    SCALAR_DOUBLE,
    SCALAR_FLOAT,
    SCALAR_INT32,
    SCALAR_INT64,
    SCALAR_UINT32,
    SCALAR_UINT64,
    SCALAR_SINT32,
    SCALAR_SINT64,
    SCALAR_FIXED32,
    SCALAR_FIXED64,
    SCALAR_SFIXED32,
    SCALAR_SFIXED64,
    SCALAR_BOOL,
    SCALAR_STRING,
    SCALAR_BYTES,
])

# Valid map key types in proto3 (subset of scalar types)
MAP_KEY_TYPES = frozenset([
    SCALAR_INT32,
    SCALAR_INT64,
    SCALAR_UINT32,
    SCALAR_UINT64,
    SCALAR_SINT32,
    SCALAR_SINT64,
    SCALAR_FIXED32,
    SCALAR_FIXED64,
    SCALAR_SFIXED32,
    SCALAR_SFIXED64,
    SCALAR_BOOL,
    SCALAR_STRING,
])


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
        if name is not None:
            cls.name = name
        elif not hasattr(cls, 'name'):
            cls.name = cls.__name__

        cls.symbol_name = cls.name

        super().__init_subclass__(**kwargs)


class NonTerminal(metaclass=_Meta):
    """Base class for non-terminal symbols in the grammar."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.symbol_name = cls.__name__


# Type alias for symbols: Terminal and NonTerminal types (classes)
Symbol = type[Terminal] | type[NonTerminal]
