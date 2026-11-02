#!/usr/bin/env python3
"""Prepare a pull for publication, in place.

- Replaces email addresses in every string field with "[email]". Agents and
  their operators sometimes post contact addresses, and some are personal.
- Deduplicates data/raw/agents.jsonl by id (the extractor appends across runs),
  keeping the last row seen.

Everything else stays verbatim, including Moltbook's ⟦HL⟧ search-highlight
markers in post text (score.unmark strips them at build time).

Usage: python redact.py [files...]   (default: data/raw/*.jsonl data/comparables/*.jsonl)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")


def scrub(o):
    if isinstance(o, str):
        return EMAIL.sub("[email]", o)
    if isinstance(o, list):
        return [scrub(x) for x in o]
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    return o


def main() -> int:
    files = [Path(f) for f in sys.argv[1:]] or [
        *sorted((HERE / "data" / "raw").glob("*.jsonl")),
        *sorted((HERE / "data" / "comparables").glob("*.jsonl"))]
    for f in files:
        rows = [scrub(json.loads(line)) for line in f.read_text().splitlines() if line.strip()]
        n = len(rows)
        if f.name == "agents.jsonl":
            rows = list({r["id"]: r for r in rows}.values())
        f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"{f}: {n} rows -> {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
