from __future__ import annotations

from dataclasses import dataclass

from .errors import ParseError
from .grammar import Grammar, NonTerminal, Production, Terminal
from .lalr import ParseTable, build_lalr_table, expected_terminals
from .spans import Span
from .tokens import Token, TokenKind


def _span_of(v: object) -> Span:
    # Token and AST nodes both carry .span.
    sp = getattr(v, "span", None)
    if sp is None:
        raise TypeError(f"semantic value has no span: {type(v)!r}")
    return sp


def join_span(*vals: object) -> Span:
    """Join spans of tokens/nodes into a single span (from first to last)."""
    real = [v for v in vals if v is not None]
    if not real:
        raise ValueError("join_span() requires at least one value")
    first = _span_of(real[0])
    last = _span_of(real[-1])
    return Span(file=first.file, start=first.start, end=last.end)


def _token_display(kind: TokenKind) -> str:
    # Prefer printable punctuation and keywords as-is, fall back to enum name.
    v = kind.value
    if len(v) == 1 and v in "{}[]()<>,.;=:":
        return v
    return v


@dataclass(slots=True)
class Parser:
    grammar: Grammar[object]
    table: ParseTable

    @classmethod
    def for_grammar(cls, grammar: Grammar[object]) -> "Parser":
        return cls(grammar=grammar, table=build_lalr_table(grammar))

    def parse(self, tokens: list[Token]) -> object:
        # State stack + semantic value stack
        states: list[int] = [0]
        values: list[object] = []
        i = 0

        while True:
            state = states[-1]
            tok = tokens[i]
            act = self.table.action.get(state, {}).get(tok.kind)
            if act is None:
                exp = sorted(expected_terminals(self.table, state), key=lambda k: k.value)
                exp_s = ", ".join(_token_display(k) for k in exp[:12])
                hint = None
                if exp:
                    hint = f"expected one of: {exp_s}"
                raise ParseError(span=tok.span, message=f"unexpected {tok.kind.value}", hint=hint)

            kind, arg = act
            if kind == "shift":
                states.append(arg)
                values.append(tok)
                i += 1
                continue

            if kind == "reduce":
                prod: Production = self.grammar.productions[arg]
                k = len(prod.body)
                if k > len(values) or k > (len(states) - 1):
                    raise RuntimeError(
                        "invalid reduce: stack underflow "
                        f"(state={state}, prod={arg}='{prod}', k={k}, "
                        f"values={len(values)}, states={len(states)}, lookahead={tok.kind.value})"
                    )
                rhs_vals = values[-k:] if k else []
                if k:
                    del values[-k:]
                    del states[-k:]
                out = prod.action(rhs_vals)
                values.append(out)
                goto_state = self.table.goto.get(states[-1], {}).get(prod.head)
                if goto_state is None:
                    raise RuntimeError(f"no goto from state {states[-1]} on {prod.head.name}")
                states.append(goto_state)
                continue

            if kind == "accept":
                if not values:
                    raise RuntimeError("accept with empty value stack")
                return values[-1]

            raise RuntimeError(f"unknown action: {act}")

