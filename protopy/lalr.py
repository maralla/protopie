from __future__ import annotations

from dataclasses import dataclass

from .grammar import (
    EOF as EOF_TYPE,
    Grammar,
    NonTerminalSymbol,
    Production,
    Symbol,
    TerminalSymbol,
)

# Extract the symbol from the type class
EOF = EOF_TYPE.symbol

# For backward compatibility in type hints  
Terminal = TerminalSymbol
NonTerminal = NonTerminalSymbol


@dataclass(frozen=True, slots=True)
class LR1Item:
    prod_index: int
    dot: int
    lookahead: Terminal

    def core(self) -> tuple[int, int]:
        return (self.prod_index, self.dot)


@dataclass(frozen=True, slots=True)
class ParseTable:
    """ACTION / GOTO tables for an LALR parser.

    ACTION[state][terminal] = ("shift", next_state) | ("reduce", prod_index) | ("accept", 0)
    GOTO[state][nonterminal] = next_state
    """

    action: dict[int, dict[Terminal, tuple[str, int]]]
    goto: dict[int, dict[NonTerminal, int]]


class GrammarAnalysisError(Exception):
    pass


def build_lalr_table(grammar: Grammar) -> ParseTable:
    # Compute FIRST sets over symbols (terminals and nonterminals), with ε tracking.
    nonterms: set[NonTerminal] = {p.head for p in grammar.productions}
    terms: set[Terminal] = {
        s for p in grammar.productions for s in p.body if isinstance(s, Terminal)
    }
    eps = object()

    first: dict[Symbol | object, set[Terminal | object]] = {}
    for t in terms:
        first[t] = {t}
    # Always include EOF as a terminal for lookahead computations.
    first[EOF] = {EOF}
    for nt in nonterms:
        first[nt] = set()

    def first_seq(seq: tuple[Symbol, ...]) -> set[Terminal | object]:
        out: set[Terminal | object] = set()
        if not seq:
            out.add(eps)
            return out
        for sym in seq:
            # Some terminals can appear only as lookaheads (not in bodies); treat them as base.
            if sym not in first and isinstance(sym, Terminal):
                first[sym] = {sym}
            sym_first = first[sym]
            out |= {x for x in sym_first if x is not eps}
            if eps not in sym_first:
                break
        else:
            out.add(eps)
        return out

    changed = True
    while changed:
        changed = False
        for p in grammar.productions:
            before = len(first[p.head])
            f = first_seq(p.body)
            first[p.head] |= f
            if len(first[p.head]) != before:
                changed = True

    def closure(items: set[LR1Item]) -> set[LR1Item]:
        out = set(items)
        changed2 = True
        while changed2:
            changed2 = False
            for it in list(out):
                prod = grammar.productions[it.prod_index]
                if it.dot >= len(prod.body):
                    continue
                sym = prod.body[it.dot]
                if not isinstance(sym, NonTerminal):
                    continue
                beta = prod.body[it.dot + 1 :]
                look = first_seq(beta + (it.lookahead,))
                lookaheads = [x for x in look if x is not eps]
                for j in grammar.productions_for(sym):
                    for la in lookaheads:
                        new_it = LR1Item(j, 0, la)  # type: ignore[arg-type]
                        if new_it not in out:
                            out.add(new_it)
                            changed2 = True
        return out

    def goto(items: set[LR1Item], sym: Symbol) -> set[LR1Item]:
        moved: set[LR1Item] = set()
        for it in items:
            prod = grammar.productions[it.prod_index]
            if it.dot < len(prod.body) and prod.body[it.dot] == sym:
                moved.add(LR1Item(it.prod_index, it.dot + 1, it.lookahead))
        return closure(moved) if moved else set()

    # Augment grammar with S' -> start
    # Accept when we finish start_prime and the lookahead is EOF.
    start_prime = NonTerminal(grammar.start.name + "'")
    augmented_prod = Production(
        head=start_prime,
        body=(grammar.start,),
        action=lambda xs: xs[0],
    )
    prods = (augmented_prod,) + grammar.productions
    g2 = Grammar(start=start_prime, productions=prods)

    # Recompute helper mappings for augmented grammar
    def prods_for(head: NonTerminal) -> tuple[int, ...]:
        return tuple(i for i, p in enumerate(g2.productions) if p.head == head)

    # Patch closure/goto to use augmented grammar; FIRST computed above already covers original
    # but we need FIRST for start_prime too.
    if start_prime not in first:
        first[start_prime] = set()
    # start_prime -> start; so FIRST(start_prime)=FIRST(start)
    first[start_prime] |= first[grammar.start]

    def closure2(items: set[LR1Item]) -> set[LR1Item]:
        out = set(items)
        changed2 = True
        while changed2:
            changed2 = False
            for it in list(out):
                prod = g2.productions[it.prod_index]
                if it.dot >= len(prod.body):
                    continue
                sym = prod.body[it.dot]
                if not isinstance(sym, NonTerminal):
                    continue
                beta = prod.body[it.dot + 1 :]
                look = first_seq(beta + (it.lookahead,))
                lookaheads = [x for x in look if x is not eps]
                for j in prods_for(sym):
                    for la in lookaheads:
                        new_it = LR1Item(j, 0, la)  # type: ignore[arg-type]
                        if new_it not in out:
                            out.add(new_it)
                            changed2 = True
        return out

    def goto2(items: set[LR1Item], sym: Symbol) -> set[LR1Item]:
        moved: set[LR1Item] = set()
        for it in items:
            prod = g2.productions[it.prod_index]
            if it.dot < len(prod.body) and prod.body[it.dot] == sym:
                moved.add(LR1Item(it.prod_index, it.dot + 1, it.lookahead))
        return closure2(moved) if moved else set()

    symbols: set[Symbol] = set()
    for p in g2.productions:
        symbols |= set(p.body)
    # EOF is never shifted in this augmented grammar; it's only a lookahead.
    symbols.discard(EOF)

    # Canonical LR(1) collection
    I0 = closure2({LR1Item(0, 0, EOF)})
    states: list[set[LR1Item]] = [I0]
    transitions: dict[tuple[int, Symbol], int] = {}

    def state_index(items: set[LR1Item]) -> int | None:
        for i, st in enumerate(states):
            if st == items:
                return i
        return None

    work = [0]
    while work:
        i = work.pop()
        st = states[i]
        for sym in symbols:
            nxt = goto2(st, sym)
            if not nxt:
                continue
            j = state_index(nxt)
            if j is None:
                j = len(states)
                states.append(nxt)
                work.append(j)
            transitions[(i, sym)] = j

    # Merge LR(1) states with same LR(0) core => LALR
    core_to_states: dict[frozenset[tuple[int, int]], list[int]] = {}
    for i, st in enumerate(states):
        core = frozenset(it.core() for it in st)
        core_to_states.setdefault(core, []).append(i)

    merged_states: list[set[LR1Item]] = []
    old_to_new: dict[int, int] = {}
    for core, idxs in core_to_states.items():
        # union lookaheads for items with same core
        merged: dict[tuple[int, int], set[Terminal]] = {c: set() for c in core}
        for i in idxs:
            for it in states[i]:
                merged[(it.prod_index, it.dot)].add(it.lookahead)
        new_items: set[LR1Item] = set()
        for (pidx, dot), las in merged.items():
            for la in las:
                new_items.add(LR1Item(pidx, dot, la))
        new_index = len(merged_states)
        merged_states.append(new_items)
        for i in idxs:
            old_to_new[i] = new_index

    merged_trans: dict[tuple[int, Symbol], int] = {}
    for (i, sym), j in transitions.items():
        merged_trans[(old_to_new[i], sym)] = old_to_new[j]

    # Build ACTION/GOTO
    action: dict[int, dict[Terminal, tuple[str, int]]] = {}
    goto_tbl: dict[int, dict[NonTerminal, int]] = {}

    def add_action(st: int, term: Terminal, act: tuple[str, int]) -> None:
        row = action.setdefault(st, {})
        if term in row and row[term] != act:
            raise GrammarAnalysisError(
                f"conflict in state {st} on {term.name}: {row[term]} vs {act}"
            )
        row[term] = act

    for i, st in enumerate(merged_states):
        for it in st:
            prod = g2.productions[it.prod_index]
            # shift
            if it.dot < len(prod.body):
                sym = prod.body[it.dot]
                if isinstance(sym, Terminal):
                    j = merged_trans.get((i, sym))
                    if j is not None:
                        add_action(i, sym, ("shift", j))
                else:
                    # goto handled below
                    pass
            else:
                # reduce / accept
                if it.prod_index == 0 and it.lookahead == EOF:
                    add_action(i, EOF, ("accept", 0))
                else:
                    # reduce by prod_index in original grammar indexing (exclude augmented)
                    add_action(i, it.lookahead, ("reduce", it.prod_index - 1))

        # gotos for nonterminals
        for sym in symbols:
            if isinstance(sym, NonTerminal):
                j = merged_trans.get((i, sym))
                if j is not None:
                    goto_tbl.setdefault(i, {})[sym] = j

    return ParseTable(action=action, goto=goto_tbl)


def expected_terminals(table: ParseTable, state: int) -> set[Terminal]:
    return set(table.action.get(state, {}).keys())


def all_terminals(grammar: Grammar) -> set[Terminal]:
    out: set[Terminal] = set()
    for p in grammar.productions:
        for s in p.body:
            if isinstance(s, Terminal):
                out.add(s)
    return out

