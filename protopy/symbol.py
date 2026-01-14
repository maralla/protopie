class _Meta(type):
    def __repr__(cls) -> str:
        return cls.__name__

    def is_terminal(cls) -> bool:
        return issubclass(cls, Terminal)

    def is_nonterminal(cls) -> bool:
        return issubclass(cls, NonTerminal)


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

        super().__init_subclass__(**kwargs)


class NonTerminal(metaclass=_Meta):
    """Base class for non-terminal symbols in the grammar."""

    symbol_name: str

    def __init__(self, value: object = None) -> None:
        self.value = value

    def __init_subclass__(cls) -> None:
        """Automatically set name from class name if not provided."""
        if not hasattr(cls, 'name'):
            cls.symbol_name = cls.__name__

    def __class_getitem__(cls, item: object) -> type:
        """Support generic syntax for type hints: QualifiedName[ast.QualifiedName]."""
        # For non-terminals, this is mainly for type hint support, just return cls
        return cls


# Type alias for any symbol
Symbol = type[Terminal] | type[NonTerminal]
