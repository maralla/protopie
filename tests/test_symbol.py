from protopy.symbol import TerminalSymbol, TerminalType, Terminal, NonTerminal


def test_symbol_eq():
    a = TerminalSymbol('a')
    b = TerminalSymbol('b')
    c = TerminalSymbol('a')

    assert a != b
    assert a == c
    assert a == Terminal("a")
    assert a == NonTerminal("a")
    assert a != NonTerminal("b")
