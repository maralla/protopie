from __future__ import annotations

import argparse
import hashlib

from protopy import parse_source


def _generate(seed: int, count: int) -> list[str]:
    from protopy.testing import generate_proto_sources

    return generate_proto_sources(seed=seed, count=count)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="compute_snapshot_hash")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--count", type=int, default=1000)
    args = ap.parse_args(argv)

    h = hashlib.sha256()
    for i, src in enumerate(_generate(args.seed, args.count)):
        ast1 = parse_source(src, file=f"snapshot:{args.seed}:{i}.proto")
        out1 = ast1.format()
        ast2 = parse_source(out1, file=f"snapshot:{args.seed}:{i}.proto")
        out2 = ast2.format()
        if out2 != out1:
            raise SystemExit(f"non-idempotent formatting at case {i}")
        h.update(out2.encode("utf-8"))
        h.update(b"\n---\n")

    print(h.hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

