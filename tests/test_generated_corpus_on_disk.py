from __future__ import annotations

import hashlib
from pathlib import Path

from protopy import parse_file, parse_files
from protopy.testing import generate_corpus_files


def test_generated_corpus_on_disk_parse_and_hash(tmp_path: Path) -> None:
    # Large enough to be meaningful, small enough to keep CI fast.
    seed = 1
    count = 300

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    files = generate_corpus_files(seed=seed, count=count)
    for rel, src in files:
        (corpus_dir / rel).write_text(src, encoding="utf-8")

    # parse_file across the whole corpus (exercises file IO)
    h = hashlib.sha256()
    entrypoints: list[Path] = []
    for rel, _ in files:
        p = corpus_dir / rel
        ast = parse_file(p)
        formatted = ast.format()
        h.update(formatted.encode("utf-8"))
        h.update(b"\n---\n")
        # also check format->parse stability
        ast2 = parse_file(_write_tmp(corpus_dir, rel + ".fmt", formatted))
        assert ast2.format() == formatted
        entrypoints.append(p)

    # parse_files import resolution (imports reference earlier corpus files)
    res = parse_files(entrypoints=[entrypoints[-1]], import_paths=[corpus_dir])
    assert len(res.files) >= 1

    # Snapshot the corpus behavior by hash (update intentionally only).
    # If this changes unexpectedly, something changed in parsing/formatting semantics.
    assert h.hexdigest() == "3f5cfee4af69b1a3fcabe5c86ec31d74d12b1f0f94ee1a22a5b137fbee79741f"


def _write_tmp(root: Path, name: str, content: str) -> Path:
    p = root / name
    p.write_text(content, encoding="utf-8")
    return p

