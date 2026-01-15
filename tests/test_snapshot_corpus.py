from __future__ import annotations

import hashlib
import os

from protopy import parse_source

from protopy.testing import generate_proto_sources


# Update this by running: `uv run python scripts/compute_snapshot_hash.py`
EXPECTED_SHA256 = "dba287fee1e4348b9ceaf80ea49f23f0ead60e3dd2213ae1823f2e9d52f02933"


def test_snapshot_corpus_hash() -> None:
    seed = int(os.environ.get("PROTO_SNAPSHOT_SEED", "1"))
    count = int(os.environ.get("PROTO_SNAPSHOT_CASES", "1000"))

    h = hashlib.sha256()
    for i, src in enumerate(generate_proto_sources(seed=seed, count=count)):
        ast1 = parse_source(src, file=f"snapshot:{seed}:{i}.proto")
        out1 = ast1.format()
        ast2 = parse_source(out1, file=f"snapshot:{seed}:{i}.proto")
        out2 = ast2.format()
        assert out2 == out1

        h.update(out2.encode("utf-8"))
        h.update(b"\n---\n")

    digest = h.hexdigest()
    assert (
        digest == EXPECTED_SHA256
    ), f"snapshot corpus changed (seed={seed}, count={count})\nexpected {EXPECTED_SHA256}\nactual   {digest}"

