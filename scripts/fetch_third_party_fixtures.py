from __future__ import annotations

# ruff: noqa: D103, T201, S603

import argparse
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="fetch_third_party_fixtures",
        description="Fetch a small set of third-party .proto fixtures for additional coverage.",
    )
    ap.add_argument(
        "--dest",
        default="tests/fixtures/third_party",
        help="Destination directory (default: tests/fixtures/third_party)",
    )
    ap.add_argument(
        "--ref",
        default="v26.1",
        help="Git ref/tag from the upstream protobuf repo (default: v26.1)",
    )
    ap.add_argument(
        "--subset",
        default="google/protobuf",
        help="Subtree of upstream repo to scan for proto3 files (default: google/protobuf)",
    )
    args = ap.parse_args(argv)

    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    # Uses the official protobuf repo (BSD-3-Clause). We only copy a few .proto files.
    repo = dest / "_protobuf_repo"
    if repo.exists():
        shutil.rmtree(repo)

    _run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            args.ref,
            "https://github.com/protocolbuffers/protobuf.git",
            str(repo),
        ],
        cwd=dest,
    )

    # Copy a proto3-only subset of fixtures.
    # Note: upstream may contain proto2 / edition-based files. We filter on syntax = "proto3".
    upstream_root = repo / "src" / args.subset
    if not upstream_root.exists():
        raise SystemExit(f"missing upstream subtree: {upstream_root}")

    out_dir = dest / "protobuf" / args.subset
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src in upstream_root.rglob("*.proto"):
        try:
            head = src.read_text(encoding="utf-8", errors="replace")[:2048]
        except OSError:
            continue
        if 'syntax = "proto3";' not in head:
            continue
        rel = src.relative_to(repo / "src")
        target = (dest / "protobuf" / rel).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        copied += 1

    # Copy license
    lic = repo / "LICENSE"
    if lic.exists():
        shutil.copyfile(lic, (dest / "protobuf" / "LICENSE.protobuf").resolve())

    shutil.rmtree(repo)
    print(f"wrote {copied} proto3 fixtures under {(dest / 'protobuf').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
