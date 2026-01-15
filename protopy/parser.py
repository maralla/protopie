from __future__ import annotations

from dataclasses import dataclass

from .errors import ParseError
from .grammar import (
    Grammar,
    Production,
    Token,
)
from .lalr import ParseTable, TableBuilder
from .symbol import Terminal


def _token_display(term: type[Terminal]) -> str:
    # Prefer printable punctuation and keywords as-is, fall back to name.
    v = term.symbol_name
    if len(v) == 1 and v in "{}[]()<>,.;=:":
        return v
    return v


@dataclass(slots=True)
class Parser:
    grammar: Grammar
    table: ParseTable

    @classmethod
    def for_grammar(cls, grammar: Grammar) -> Parser:
        return cls(grammar=grammar, table=TableBuilder(grammar).build())

    def parse(self, tokens: list[Token]) -> object:
        # State stack + semantic value stack
        states: list[int] = [0]
        values: list[object] = []
        i = 0

        while True:
            state = states[-1]
            tok = tokens[i]
            act = self.table.table.get(state, {}).get(tok.kind)  # tok.kind is Terminal
            if act is None:
                exp = sorted(self.table.terminals(state=state), key=lambda t: t.symbol_name)
                exp_s = ", ".join(_token_display(t) for t in exp[:12])
                hint_text = None
                if exp:
                    hint_text = f"expected one of: {exp_s}"
                # tok.kind is a type[Terminal], not an instance
                kind_name = tok.kind.symbol_name if hasattr(tok.kind, 'symbol_name') else str(tok.kind)
                raise ParseError.detail(span=tok.span, message=f"unexpected {kind_name}", hint=hint_text)

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
                        f"values={len(values)}, states={len(states)}, lookahead={tok.kind.symbol_name})"
                    )
                rhs_vals = tuple(values[-k:]) if k else ()
                if k:
                    del values[-k:]
                    del states[-k:]
                # Type ignore: values contains runtime Symbol instances, mypy sees generic objects
                out = prod.action(rhs_vals)  # type: ignore[arg-type]
                values.append(out)
                goto_action = self.table.table.get(states[-1], {}).get(prod.head)
                if goto_action is None:
                    raise RuntimeError(f"no goto from state {states[-1]} on {prod.head.symbol_name}")
                goto_kind, goto_state = goto_action
                if goto_kind != "goto":
                    raise RuntimeError(f"expected goto action, got {goto_kind}")
                states.append(goto_state)
                continue

            if kind == "accept":
                if not values:
                    raise RuntimeError("accept with empty value stack")
                return values[-1]

            raise RuntimeError(f"unknown action: {act}")

