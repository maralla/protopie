from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, TypeVar

from .tokens import TokenKind

if TYPE_CHECKING:
    from .tokens import Token


SemVal = TypeVar("SemVal")


@dataclass(frozen=True, slots=True)
class Terminal:
    kind: TokenKind

    def __str__(self) -> str:
        return f"T({self.kind.value})"


@dataclass(frozen=True, slots=True)
class NonTerminal:
    name: str

    def __str__(self) -> str:
        return f"N({self.name})"


Symbol = Terminal | NonTerminal


ActionFn = Callable[[list[object]], object]


@dataclass(frozen=True, slots=True)
class Production:
    head: NonTerminal
    body: tuple[Symbol, ...]
    action: ActionFn

    def __str__(self) -> str:
        rhs = " ".join(str(s) for s in self.body) if self.body else "ε"
        return f"{self.head.name} -> {rhs}"


@dataclass(frozen=True, slots=True)
class Grammar(Generic[SemVal]):
    start: NonTerminal
    productions: tuple[Production, ...]

    def prods_for(self, head: NonTerminal) -> tuple[int, ...]:
        return tuple(i for i, p in enumerate(self.productions) if p.head == head)


def t(kind: TokenKind) -> Terminal:
    return Terminal(kind)


def n(name: str) -> NonTerminal:
    return NonTerminal(name)

