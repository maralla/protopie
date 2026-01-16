# ruff: noqa: D103, S101

from protopy.symbol import Terminal, NonTerminal


def test_symbol_classes() -> None:
    class A(Terminal):
        name = "a"

    class B(Terminal):
        name = "b"

    class C(Terminal):
        name = "a"

    assert A.name == "a"
    assert B.name == "b"
    assert C.name == "a"

    assert A.name != B.name
    assert A.name == C.name


def test_symbol_init_subclass() -> None:
    class MyTerminal(Terminal):
        pass

    class MyNonTerminal(NonTerminal):
        pass

    assert MyTerminal.name == "MyTerminal"
    assert MyNonTerminal.symbol_name == "MyNonTerminal"
