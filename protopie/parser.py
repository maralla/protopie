"""LALR parser for Protocol Buffers proto3 syntax."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import ParseError
from .lalr import ParseTable, TableBuilder
from .grammar import GrammarBuilder

if TYPE_CHECKING:
    from .grammar import Grammar, Production, Token
    from .symbol import Terminal, Symbol, SymbolType


# Format terminal symbol for display in error messages
def _token_display(terminal: type[Terminal]) -> str:
    symbol_name = terminal.symbol_name
    if len(symbol_name) == 1 and symbol_name in "{}[]()<>,.;=:":
        return symbol_name
    return symbol_name


class GrammarError(Exception):
    """Grammar is invalid."""


@dataclass
class Parser:
    """LALR parser that processes tokens into an AST."""

    grammar: Grammar
    parse_table: ParseTable

    _cache: Parser | None = None

    @classmethod
    def instance(cls) -> Parser:
        """Get the parser instance for grammar."""
        if cls._cache is not None:
            return cls._cache

        grammar = GrammarBuilder.build()
        parser = cls(grammar=grammar, parse_table=TableBuilder(grammar).build())
        cls._cache = parser
        return parser

    # Get parse action for current state and token
    def _get_action(self, state: int, symbol: SymbolType) -> tuple[str, int] | None:
        return self.parse_table.table.get(state, {}).get(symbol)

    # Create a parse error with helpful context
    def _create_parse_error(self, state: int, token: Token) -> ParseError:
        max_expected_tokens = 5

        expected = sorted(self.parse_table.terminals(state=state), key=lambda t: t.symbol_name)
        expected_str = ", ".join(_token_display(t) for t in expected[:max_expected_tokens])
        hint = f"expected one of: {expected_str}" if expected else None
        token_name = type(token).symbol_name

        return ParseError.detail(span=token.span, message=f"unexpected {token_name}", hint=hint)

    def _assert_action(self, expected: str, action: str) -> None:
        if expected != action:
            raise GrammarError(f"expected {expected} action, got {action}")

    # Handle accept action: return final parse result
    def parse(self, tokens: list[Token]) -> Symbol:
        """Parse a list of tokens into an AST.

        Args:
            tokens: List of tokens to parse (must end with EOF token)

        Returns:
            The root AST node

        Raises:
            ParseError: If the input contains syntax errors
            RuntimeError: If there are internal parser errors

        """
        states: list[int] = [0]
        values: list[Symbol] = []
        token_index = 0

        while True:
            current_state = states[-1]
            current_token = tokens[token_index]
            action = self._get_action(current_state, type(current_token))

            if action is None:
                raise self._create_parse_error(current_state, current_token)

            action_kind, action_arg = action

            if action_kind == "shift":
                states.append(action_arg)
                values.append(current_token)
                token_index += 1
                continue

            if action_kind == "reduce":
                production: Production = self.grammar.productions[action_arg]
                head = production.head
                body_length = len(production.body)

                values_count = len(values)
                states_count = len(states)

                # Validate stack has enough elements
                if body_length > values_count or body_length > (states_count - 1):
                    lookahead_name = type(current_token).symbol_name
                    msg = (
                        f"invalid reduce: stack underflow (state={current_state}, "
                        f"prod={action_arg}='{production}', k={body_length}, "
                        f"values={values_count}, states={states_count}, lookahead={lookahead_name})"
                    )
                    raise GrammarError(msg)

                # Pop right-hand side values from stack
                action_values = tuple(values[-body_length:]) if body_length else ()
                if body_length:
                    del values[-body_length:]
                    del states[-body_length:]

                # Execute production action and push result
                result = production.action(action_values)
                values.append(result)

                # Perform goto transition
                state = states[-1]
                goto_action = self._get_action(state, head)
                if goto_action is None:
                    raise GrammarError(f"no goto from state {state} on {head.symbol_name}")

                goto_kind, goto_state = goto_action
                self._assert_action("goto", goto_kind)

                states.append(goto_state)
                continue

            if action_kind == "accept":
                if not values:
                    raise GrammarError("accept with empty value stack")

                return values[-1]

            raise GrammarError(f"unknown action: {action}")
