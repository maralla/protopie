from __future__ import annotations

# ruff: noqa: D103, T201

from protopie.grammar import GrammarBuilder


def main() -> None:
    g = GrammarBuilder.build()
    print(f"productions: {len(g.productions)}")
    for i, p in enumerate(g.productions):
        print(f"{i:>3}: {p}")


if __name__ == "__main__":
    main()
