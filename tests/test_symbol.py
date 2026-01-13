from protopy.symbol import Terminal, NonTerminal


def test_symbol_classes():
    """Test that symbol classes have correct name attributes."""
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


def test_symbol_init_subclass():
    """Test that __init_subclass__ sets name from class name if not provided."""
    class MyTerminal(Terminal):
        pass

    class MyNonTerminal(NonTerminal):
        pass

    assert MyTerminal.name == "MyTerminal"
    assert MyNonTerminal.name == "MyNonTerminal"
