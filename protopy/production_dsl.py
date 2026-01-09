from __future__ import annotations

from dataclasses import dataclass

from .grammar import NonTerminal, Production, Symbol, Terminal


@dataclass(frozen=True, slots=True)
class Rhs:
    syms: tuple[Symbol, ...]

    def __and__(self, other):
        # Support: A & B & C @ act  (parses as A & B & (C @ act))
        if isinstance(other, Bound):
            return Bound(self.syms + other.syms, other.action)
        if isinstance(other, Rhs):
            return Rhs(self.syms + other.syms)
        if isinstance(other, Sym):
            return Rhs(self.syms + (other.sym,))
        return NotImplemented

    def __matmul__(self, action):
        return Bound(self.syms, action)


@dataclass(frozen=True, slots=True)
class Bound:
    syms: tuple[Symbol, ...]
    action: object

    def __and__(self, other):
        raise TypeError("cannot use & after @ action; put @ action at the end")

    def __or__(self, other):
        if isinstance(other, (Sym, Rhs)):
            raise TypeError("cannot use | after @ action; put @ action at the end")
        if isinstance(other, Bound):
            if other.action != self.action:
                raise TypeError("alternation between different actions is not supported")
            return BoundAlts(action=self.action, alts=[self.syms, other.syms])
        if isinstance(other, Alts):
            return other.__ror__(self)
        if isinstance(other, BoundAlts):
            return other.__ror__(self)
        return NotImplemented


@dataclass(slots=True)
class Sym:
    sym: Symbol

    def __and__(self, other):
        # Support: A & B & C @ act  (parses as A & B & (C @ act))
        if isinstance(other, Bound):
            return Bound((self.sym,) + other.syms, other.action)
        if isinstance(other, Rhs):
            return Rhs((self.sym,) + other.syms)
        if isinstance(other, Sym):
            return Rhs((self.sym, other.sym))
        return NotImplemented

    def __or__(self, other):
        # Support: A | B | C @ act  (parses as A | B | (C @ act))
        if isinstance(other, Bound):
            return BoundAlts(action=other.action, alts=[(self.sym,), other.syms])
        if isinstance(other, Sym):
            return Alts([(self.sym,), (other.sym,)])
        if isinstance(other, Rhs):
            return Alts([(self.sym,), other.syms])
        if isinstance(other, Alts):
            return Alts([(self.sym,), *other.alts])
        if isinstance(other, BoundAlts):
            return BoundAlts(action=other.action, alts=[(self.sym,), *other.alts])
        return NotImplemented

    def __ror__(self, other):
        return self.__or__(other)

    def __matmul__(self, action):
        return Bound((self.sym,), action)


@dataclass(slots=True)
class RuleNt(Sym):
    """Nonterminal that can be used as RHS symbol and as an LHS with `|=`."""

    _sink: "ProductionSink"

    def __ior__(self, rhs):
        if isinstance(rhs, Bound):
            self._sink.add(self.sym, rhs.syms, rhs.action)
            return self
        if isinstance(rhs, BoundAlts):
            for body in rhs.alts:
                self._sink.add(self.sym, body, rhs.action)
            return self
        if isinstance(rhs, Rhs):
            raise TypeError("production missing action: use `rhs @ action`")
        if isinstance(rhs, Alts):
            raise TypeError("alternation missing action: use `(a | b | c) @ action`")
        raise TypeError("production must be `rhs @ action`")


@dataclass(slots=True)
class ProductionSink:
    productions: list[Production]

    def add(self, head: Symbol, body: tuple[Symbol, ...], action) -> None:
        if not isinstance(head, NonTerminal):
            raise TypeError("head must be a NonTerminal")
        self.productions.append(Production(head=head, body=body, action=action))


def eps() -> Rhs:
    return Rhs(tuple())


@dataclass(frozen=True, slots=True)
class Alts:
    alts: list[tuple[Symbol, ...]]

    def __or__(self, other):
        # Support: A | B | C @ act  (parses as (A | B) | (C @ act))
        if isinstance(other, Bound):
            return BoundAlts(action=other.action, alts=[*self.alts, other.syms])
        if isinstance(other, Sym):
            return Alts([*self.alts, (other.sym,)])
        if isinstance(other, Rhs):
            return Alts([*self.alts, other.syms])
        if isinstance(other, Alts):
            return Alts([*self.alts, *other.alts])
        if isinstance(other, BoundAlts):
            return BoundAlts(action=other.action, alts=[*self.alts, *other.alts])
        return NotImplemented

    def __ror__(self, other):
        if isinstance(other, Sym):
            return Alts([(other.sym,), *self.alts])
        if isinstance(other, Rhs):
            return Alts([other.syms, *self.alts])
        return NotImplemented

    def __matmul__(self, action):
        return BoundAlts(action=action, alts=self.alts)


@dataclass(frozen=True, slots=True)
class BoundAlts:
    action: object
    alts: list[tuple[Symbol, ...]]
