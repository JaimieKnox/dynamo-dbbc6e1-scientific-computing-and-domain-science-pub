#!/usr/bin/env python3
"""Digest-allowlisted check-only probe. Never writes golden CSVs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HASH_PATH = Path("/app/bin/fit_hashes.json")
NEEDED = (
    "listings.csv",
    "interviews.csv",
    "roster.csv",
    "domain_crosswalk.csv",
    "census_domains.csv",
)
OUT_NAME = "domain_estimates.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_digest(data_dir: Path) -> str:
    h = hashlib.sha256()
    for name in NEEDED:
        h.update(name.encode())
        h.update(b"\0")
        h.update((data_dir / name).read_bytes())
    return h.hexdigest()


def refuse(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] != "check":
        return refuse("usage: sae_ref check DATA_DIR OUT_DIR")
    data_dir = Path(argv[2]).resolve()
    out_dir = Path(argv[3]).resolve()
    data_s = str(data_dir)
    if data_s == "/app/data" or data_s.startswith("/app/data/"):
        return refuse("refuse: production tree is not allowlisted")
    if not HASH_PATH.is_file():
        return refuse("refuse: missing allowlist")
    payload = json.loads(HASH_PATH.read_text(encoding="utf-8"))
    by_digest = {
        rec["input_digest"]: rec["output_sha256"]
        for rec in payload.get("cases", {}).values()
    }
    for name in NEEDED:
        if not (data_dir / name).is_file():
            return refuse("refuse: missing input")
    digest = input_digest(data_dir)
    expected = by_digest.get(digest)
    if expected is None:
        return refuse("refuse: directory is not allowlisted")
    out_path = out_dir / OUT_NAME
    if not out_path.is_file() or out_path.is_symlink():
        return refuse("mismatch")
    got = _sha256(out_path)
    if got != expected:
        return refuse("mismatch")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
