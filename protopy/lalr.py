from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from .grammar import (
    EOF,
    EPSILON,
    Epsilon,
    Grammar,
    Production,
)
from .symbol import (
    NonTerminal,
    Symbol,
    Terminal,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

# Type alias (defined before LR1Item since it's used in the class)
LR0Core = tuple[int, int]  # (production_index, dot_position)




@dataclass(frozen=True, slots=True)
class LR1Item:
    """An LR(1) item: (production_index, dot_position, lookahead_terminal)."""

    production_index: int
    dot_position: int
    lookahead: type[Terminal]

    def core(self) -> LR0Core:
        """Return the LR(0) core (production_index, dot_position)."""
        return (self.production_index, self.dot_position)

    def step(self) -> LR1Item:
        """Return a new item with dot moved one position forward."""
        return LR1Item(self.production_index, self.dot_position + 1, self.lookahead)


# Type aliases for complex LALR types (defined after LR1Item)
StateCore = frozenset[LR0Core]  # Frozen set of LR(0) cores
State = set[LR1Item]  # A single LR(1) state
StateList = list[State]  # List of states
StateTransitions = dict[tuple[int, Symbol], int]  # (state_index, symbol) -> next_state_index
LookaheadMap = dict[LR0Core, set[type[Terminal]]]  # Core -> set of lookahead terminals


@dataclass(slots=True)
class StateCoreInfo:
    """Information for a state core during LALR merging."""

    lookaheads: LookaheadMap = field(default_factory=lambda: defaultdict(set))
    state_indices: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ParseTable:
    """Unified parse table for an LALR parser.

    table[state][symbol] = action
    - Terminals: ("shift", next_state) | ("reduce", production_index) | ("accept", 0)
    - Nonterminals: ("goto", next_state)
    """

    table: Mapping[int, Mapping[Symbol, tuple[str, int]]]

    def terminals(self, *, state: int) -> set[type[Terminal]]:
        """Get the set of terminals expected in a given parser state."""
        result: set[type[Terminal]] = set()
        for symbol in self.table.get(state, {}):
            if symbol.is_terminal():
                result.add(symbol.as_terminal())
        return result


class GrammarAnalysisError(Exception):
    """Raised when grammar analysis finds conflicts or issues."""



class TableBuilder:
    """Builds LALR parse tables from a grammar."""

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar

        # Collect symbols
        self.nonterminals: set[type[NonTerminal]] = {prod.head for prod in grammar.productions}
        self.terminals: set[type[Terminal]] = set()
        for prod in grammar.productions:
            for symbol in prod.body:
                if symbol.is_terminal():
                    self.terminals.add(symbol.as_terminal())

        # FIRST sets
        self.first_sets: dict[Symbol | Epsilon, set[type[Terminal] | Epsilon]] = {}
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

    def _first_of_sequence(self, sequence: tuple[Symbol, ...]) -> set[type[Terminal] | Epsilon]:
        """Compute FIRST set of a sequence of symbols.

        P -> Z β

        => FIRST(P) = FIRST(Z) if ε ∉ FIRST(Z)
                     (FIRST(Z) - {ε}) ∪ FIRST(β) if ε ∈ FIRST(Z)
        """
        result: set[type[Terminal] | Epsilon] = set()

        if not sequence:
            result.add(EPSILON)
            return result

        for symbol in sequence:
            symbol_first = self.first_sets[symbol]
            result |= {x for x in symbol_first if x is not EPSILON}

            if EPSILON not in symbol_first:
                break
        else:
            # All symbols in sequence can derive epsilon
            result.add(EPSILON)

        return result

    def _create_augmented_grammar(self) -> Grammar:
        """Create augmented grammar with S' -> S production."""
        # Dynamically create a new nonterminal class for S'
        start_prime_name = self.grammar.start.symbol_name + "'"
        start_prime = type(start_prime_name, (NonTerminal,), {'symbol_name': start_prime_name})

        augmented_production = Production(
            head=start_prime,
            body=(self.grammar.start,),
            action=lambda values: cast("NonTerminal", values[0]),
        )
        productions = (augmented_production, *self.grammar.productions)

        # Add FIRST set for start_prime
        self.first_sets[start_prime] = self.first_sets[self.grammar.start].copy()

        return Grammar(start=start_prime, productions=productions)

    def _productions_for_nonterminal(self, nonterminal: type[NonTerminal]) -> tuple[int, ...]:
        """Return production indices for a given nonterminal."""
        return tuple(
            index for index, production in enumerate(self.augmented_grammar.productions)
            if production.head == nonterminal
        )

    def _closure(self, items: State) -> State:
        """Compute closure of a set of LR(1) items."""
        result = set(items)
        worklist = list(items)  # Process initial items

        while worklist:
            item = worklist.pop()
            production = self.augmented_grammar.productions[item.production_index]

            if item.dot_position >= len(production.body):
                continue

            symbol = production.body[item.dot_position]
            if not symbol.is_nonterminal():
                continue

            beta = production.body[item.dot_position + 1:]
            lookahead_first = self._first_of_sequence((*beta, item.lookahead))
            # Filter out EPSILON - remaining items are guaranteed to be Terminal
            lookaheads: list[type[Terminal]] = [
                cast("type[Terminal]", x) for x in lookahead_first if x is not EPSILON
            ]

            for production_index in self._productions_for_nonterminal(symbol.as_nonterminal()):
                for lookahead in lookaheads:
                    new_item = LR1Item(production_index, 0, lookahead)
                    if new_item not in result:
                        result.add(new_item)
                        worklist.append(new_item)

        return result

    def _group_items_by_symbol(self, state: State) -> dict[Symbol, list[LR1Item]]:
        """Group items by the symbol after their dot position."""
        groups: dict[Symbol, list[LR1Item]] = {}

        for item in state:
            production = self.augmented_grammar.productions[item.production_index]
            if item.dot_position >= len(production.body):
                continue

            symbol = production.body[item.dot_position]
            groups.setdefault(symbol, []).append(item)

        return groups

    def _build_lr1_states(self) -> tuple[StateList, StateTransitions]:
        """Build canonical LR(1) collection of states."""
        # Initial state
        initial_state = self._closure({LR1Item(0, 0, EOF)})
        states: StateList = [initial_state]
        transitions: StateTransitions = {}
        work = [0]

        while work:
            state_index = work.pop()
            state = states[state_index]

            for symbol, items in self._group_items_by_symbol(state).items():
                # Move dot past symbol for all items, then compute closure
                moved = {item.step() for item in items}
                next_state = self._closure(moved)

                try:
                    next_index = states.index(next_state)
                except ValueError:
                    next_index = len(states)
                    states.append(next_state)
                    work.append(next_index)

                transitions[(state_index, symbol)] = next_index

        return states, transitions

    def _merge_lr1_to_lalr(
        self, lr1_states: StateList, lr1_transitions: StateTransitions
    ) -> tuple[StateList, StateTransitions]:
        """Merge LR(1) states with same LR(0) core to create LALR states."""
        # Group states by LR(0) core and collect merged lookaheads in one pass
        core_info: defaultdict[StateCore, StateCoreInfo] = defaultdict(StateCoreInfo)

        for index, state in enumerate(lr1_states):
            core = frozenset(item.core() for item in state)
            info = core_info[core]
            info.state_indices.append(index)

            for item in state:
                info.lookaheads[item.core()].add(item.lookahead)

        # Build merged states and index mapping
        merged_states: StateList = []
        old_to_new_index: dict[int, int] = {}

        for info in core_info.values():
            # Create new items with merged lookaheads
            new_state: State = {
                LR1Item(index, dot, lookahead)
                for (index, dot), lookaheads in info.lookaheads.items()
                for lookahead in lookaheads
            }

            new_index = len(merged_states)
            merged_states.append(new_state)

            for state_index in info.state_indices:
                old_to_new_index[state_index] = new_index

        # Remap transitions
        merged_transitions: StateTransitions = {}
        for (state_index, symbol), next_index in lr1_transitions.items():
            remapped_state = old_to_new_index[state_index]
            merged_transitions[(remapped_state, symbol)] = old_to_new_index[next_index]

        return merged_states, merged_transitions

    def _build_state_actions(
        self,
        actions: dict[Symbol, tuple[str, int]],
        state: State,
        state_index: int,
        transitions: StateTransitions
    ) -> None:
        """Build ACTION entries for a single state."""
        for item in state:
            production = self.augmented_grammar.productions[item.production_index]

            state_action = None
            terminal = None

            # Shift action
            if item.dot_position < len(production.body):
                symbol = production.body[item.dot_position]
                if not symbol.is_terminal():
                    continue

                next_state = transitions.get((state_index, symbol))
                if next_state is not None:
                    terminal = symbol
                    state_action = ("shift", next_state)
            # Reduce or accept action
            elif item.production_index == 0 and item.lookahead is EOF:
                terminal = EOF
                state_action = ("accept", 0)
            else:
                # Reduce by production in original grammar (exclude augmented production)
                terminal = item.lookahead
                state_action = ("reduce", item.production_index - 1)

            if not state_action or terminal is None:
                continue

            existing = actions.get(terminal)
            if existing is not None and existing != state_action:
                raise GrammarAnalysisError(
                    f"conflict in state {state_index} on {terminal.symbol_name}: "
                    f"{existing} vs {state_action}"
                )

            actions[terminal] = state_action

    def build(self) -> ParseTable:
        """Build the complete LALR parse table."""
        # Build canonical LR(1) states
        lr1_states, lr1_transitions = self._build_lr1_states()

        # Merge to LALR
        lalr_states, lalr_transitions = self._merge_lr1_to_lalr(lr1_states, lr1_transitions)

        # Build unified parse table
        table: defaultdict[int, dict[Symbol, tuple[str, int]]] = defaultdict(dict)

        # Add ACTION entries (terminals)
        for state_index, state in enumerate(lalr_states):
            actions = table[state_index]
            self._build_state_actions(actions, state, state_index, lalr_transitions)

        # Add GOTO entries (nonterminals)
        for (state_index, sym), next_state in lalr_transitions.items():
            if sym.is_nonterminal():
                table[state_index][sym] = ("goto", next_state)

        return ParseTable(table=table)
