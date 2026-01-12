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
    """An LR(1) item: (production_index, dot_position, lookahead_terminal)."""
    production_index: int
    dot_position: int
    lookahead: Terminal

    def core(self) -> tuple[int, int]:
        """Return the LR(0) core (production_index, dot_position)."""
        return (self.production_index, self.dot_position)


@dataclass(frozen=True, slots=True)
class ParseTable:
    """ACTION / GOTO tables for an LALR parser.

    ACTION[state][terminal] = ("shift", next_state) | ("reduce", production_index) | ("accept", 0)
    GOTO[state][nonterminal] = next_state
    """
    action: dict[int, dict[Terminal, tuple[str, int]]]
    goto: dict[int, dict[NonTerminal, int]]


class GrammarAnalysisError(Exception):
    """Raised when grammar analysis finds conflicts or issues."""
    pass


class TableBuilder:
    """Builds LALR parse tables from a grammar."""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.epsilon = object()  # Sentinel for epsilon in FIRST sets

        # Collect symbols
        self.nonterminals: set[NonTerminal] = {prod.head for prod in grammar.productions}
        self.terminals: set[Terminal] = {
            symbol for prod in grammar.productions
            for symbol in prod.body
            if isinstance(symbol, Terminal)
        }

        # FIRST sets
        self.first_sets: dict[Symbol | object, set[Terminal | object]] = {}
        self._initialize_first_sets()
        self._compute_first_sets()

        # Augmented grammar
        self.augmented_grammar = self._create_augmented_grammar()

    def _initialize_first_sets(self) -> None:
        """Initialize FIRST sets for all terminals and nonterminals."""
        for terminal in self.terminals:
            self.first_sets[terminal] = {terminal}

        # Always include EOF as a terminal for lookahead computations
        self.first_sets[EOF] = {EOF}

        for nonterminal in self.nonterminals:
            self.first_sets[nonterminal] = set()

    def _compute_first_sets(self) -> None:
        """Compute FIRST sets for all nonterminals using fixed-point iteration."""
        changed = True
        while changed:
            changed = False
            for production in self.grammar.productions:
                before_size = len(self.first_sets[production.head])
                first_of_body = self._first_of_sequence(production.body)
                self.first_sets[production.head] |= first_of_body
                if len(self.first_sets[production.head]) != before_size:
                    changed = True

    def _first_of_sequence(self, sequence: tuple[Symbol, ...]) -> set[Terminal | object]:
        """Compute FIRST set of a sequence of symbols."""
        result: set[Terminal | object] = set()

        if not sequence:
            result.add(self.epsilon)
            return result

        for symbol in sequence:
            # Some terminals can appear only as lookaheads (not in bodies)
            if symbol not in self.first_sets and isinstance(symbol, Terminal):
                self.first_sets[symbol] = {symbol}

            symbol_first = self.first_sets[symbol]
            result |= {x for x in symbol_first if x is not self.epsilon}

            if self.epsilon not in symbol_first:
                break
        else:
            # All symbols in sequence can derive epsilon
            result.add(self.epsilon)

        return result

    def _create_augmented_grammar(self) -> Grammar:
        """Create augmented grammar with S' -> S production."""
        start_prime = NonTerminal(self.grammar.start.name + "'")
        augmented_production = Production(
            head=start_prime,
            body=(self.grammar.start,),
            action=lambda values: values[0],
        )
        productions = (augmented_production,) + self.grammar.productions

        # Add FIRST set for start_prime
        if start_prime not in self.first_sets:
            self.first_sets[start_prime] = set()
        self.first_sets[start_prime] |= self.first_sets[self.grammar.start]

        return Grammar(start=start_prime, productions=productions)

    def _productions_for_nonterminal(self, nonterminal: NonTerminal) -> tuple[int, ...]:
        """Return production indices for a given nonterminal."""
        return tuple(
            index for index, production in enumerate(self.augmented_grammar.productions)
            if production.head == nonterminal
        )

    def _closure(self, items: set[LR1Item]) -> set[LR1Item]:
        """Compute closure of a set of LR(1) items."""
        result = set(items)
        changed = True

        while changed:
            changed = False
            for item in list(result):
                production = self.augmented_grammar.productions[item.production_index]

                if item.dot_position >= len(production.body):
                    continue

                symbol = production.body[item.dot_position]
                if not isinstance(symbol, NonTerminal):
                    continue

                beta = production.body[item.dot_position + 1:]
                lookahead_first = self._first_of_sequence(beta + (item.lookahead,))
                lookaheads = [x for x in lookahead_first if x is not self.epsilon]

                for production_index in self._productions_for_nonterminal(symbol):
                    for lookahead in lookaheads:
                        new_item = LR1Item(production_index, 0, lookahead)  # type: ignore[arg-type]
                        if new_item not in result:
                            result.add(new_item)
                            changed = True

        return result

    def _goto(self, items: set[LR1Item], symbol: Symbol) -> set[LR1Item]:
        """Compute goto(items, symbol)."""
        moved: set[LR1Item] = set()

        for item in items:
            production = self.augmented_grammar.productions[item.production_index]
            if item.dot_position < len(production.body) and production.body[item.dot_position] == symbol:
                moved.add(LR1Item(item.production_index, item.dot_position + 1, item.lookahead))

        return self._closure(moved) if moved else set()

    def _find_state_index(self, items: set[LR1Item], states: list[set[LR1Item]]) -> int | None:
        """Find the index of a state in the state list."""
        for index, state in enumerate(states):
            if state == items:
                return index
        return None

    def _build_lr1_states(self) -> tuple[list[set[LR1Item]], dict[tuple[int, Symbol], int]]:
        """Build canonical LR(1) collection of states."""
        # Collect all symbols from productions (excluding EOF)
        symbols: set[Symbol] = set()
        for production in self.augmented_grammar.productions:
            symbols |= set(production.body)
        symbols.discard(EOF)

        # Initial state
        initial_state = self._closure({LR1Item(0, 0, EOF)})
        states: list[set[LR1Item]] = [initial_state]
        transitions: dict[tuple[int, Symbol], int] = {}
        work = [0]

        while work:
            state_index = work.pop()
            state = states[state_index]

            for symbol in symbols:
                next_state = self._goto(state, symbol)
                if not next_state:
                    continue

                next_index = self._find_state_index(next_state, states)
                if next_index is None:
                    next_index = len(states)
                    states.append(next_state)
                    work.append(next_index)

                transitions[(state_index, symbol)] = next_index

        return states, transitions

    def _merge_lr1_to_lalr(
        self,
        lr1_states: list[set[LR1Item]],
        lr1_transitions: dict[tuple[int, Symbol], int]
    ) -> tuple[list[set[LR1Item]], dict[tuple[int, Symbol], int]]:
        """Merge LR(1) states with same LR(0) core to create LALR states."""
        # Group states by their LR(0) core
        core_to_states: dict[frozenset[tuple[int, int]], list[int]] = {}
        for index, state in enumerate(lr1_states):
            core = frozenset(item.core() for item in state)
            core_to_states.setdefault(core, []).append(index)

        # Merge states with same core
        merged_states: list[set[LR1Item]] = []
        old_to_new_index: dict[int, int] = {}

        for core, state_indices in core_to_states.items():
            # Union lookaheads for items with same core
            merged_lookaheads: dict[tuple[int, int], set[Terminal]] = {c: set() for c in core}
            for state_index in state_indices:
                for item in lr1_states[state_index]:
                    merged_lookaheads[(item.production_index, item.dot_position)].add(item.lookahead)

            # Create new items with merged lookaheads
            new_items: set[LR1Item] = set()
            for (production_index, dot_position), lookaheads in merged_lookaheads.items():
                for lookahead in lookaheads:
                    new_items.add(LR1Item(production_index, dot_position, lookahead))

            new_index = len(merged_states)
            merged_states.append(new_items)

            for state_index in state_indices:
                old_to_new_index[state_index] = new_index

        # Remap transitions
        merged_transitions: dict[tuple[int, Symbol], int] = {}
        for (state_index, symbol), next_index in lr1_transitions.items():
            merged_transitions[(old_to_new_index[state_index], symbol)] = old_to_new_index[next_index]

        return merged_states, merged_transitions

    def _add_action_entry(
        self,
        action: dict[int, dict[Terminal, tuple[str, int]]],
        state: int,
        terminal: Terminal,
        entry: tuple[str, int]
    ) -> None:
        """Add an entry to the ACTION table, checking for conflicts."""
        row = action.setdefault(state, {})
        if terminal in row and row[terminal] != entry:
            raise GrammarAnalysisError(
                f"conflict in state {state} on {terminal.name}: {row[terminal]} vs {entry}"
            )
        row[terminal] = entry

    def _build_action_goto_tables(
        self,
        states: list[set[LR1Item]],
        transitions: dict[tuple[int, Symbol], int],
        symbols: set[Symbol]
    ) -> ParseTable:
        """Build ACTION and GOTO tables from LALR states."""
        action: dict[int, dict[Terminal, tuple[str, int]]] = {}
        goto_table: dict[int, dict[NonTerminal, int]] = {}

        for state_index, state in enumerate(states):
            for item in state:
                production = self.augmented_grammar.productions[item.production_index]

                # Shift action
                if item.dot_position < len(production.body):
                    symbol = production.body[item.dot_position]
                    if isinstance(symbol, Terminal):
                        next_state = transitions.get((state_index, symbol))
                        if next_state is not None:
                            self._add_action_entry(action, state_index, symbol, ("shift", next_state))
                else:
                    # Reduce or accept action
                    if item.production_index == 0 and item.lookahead == EOF:
                        self._add_action_entry(action, state_index, EOF, ("accept", 0))
                    else:
                        # Reduce by production in original grammar (exclude augmented production)
                        self._add_action_entry(
                            action,
                            state_index,
                            item.lookahead,
                            ("reduce", item.production_index - 1)
                        )

            # GOTO entries for nonterminals
            for symbol in symbols:
                if isinstance(symbol, NonTerminal):
                    next_state = transitions.get((state_index, symbol))
                    if next_state is not None:
                        goto_table.setdefault(state_index, {})[symbol] = next_state

        return ParseTable(action=action, goto=goto_table)

    def build(self) -> ParseTable:
        """Build the complete LALR parse table."""
        # Build canonical LR(1) states
        lr1_states, lr1_transitions = self._build_lr1_states()

        # Merge to LALR
        lalr_states, lalr_transitions = self._merge_lr1_to_lalr(lr1_states, lr1_transitions)

        # Collect symbols
        symbols: set[Symbol] = set()
        for production in self.augmented_grammar.productions:
            symbols |= set(production.body)
        symbols.discard(EOF)

        # Build ACTION/GOTO tables
        return self._build_action_goto_tables(lalr_states, lalr_transitions, symbols)


def expected_terminals(table: ParseTable, state: int) -> set[Terminal]:
    """Get the set of terminals expected in a given parser state."""
    return set(table.action.get(state, {}).keys())


def all_terminals(grammar: Grammar) -> set[Terminal]:
    """Get all terminals used in the grammar."""
    terminals: set[Terminal] = set()
    for production in grammar.productions:
        for symbol in production.body:
            if isinstance(symbol, Terminal):
                terminals.add(symbol)
    return terminals
