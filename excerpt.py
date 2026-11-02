#!/usr/bin/env python3
"""Render the top-scored threads as compact markdown digests for labeling.

Keeps the exchanges, drops the drive-by top-level comments: a comment is
included when it sits in a reply chain (has a parent, or has replies), or
carries a commitment phrase / @mention. Each comment is clipped and tagged
with its id so labels can cite evidence by id.

Usage: uv run --no-project python excerpt.py [--top 60] [--per-thread 45]
Writes data/raw/candidates/NN-<post_id>.md
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from score import COMMIT, MENTION

HERE = Path(__file__).parent


def clip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(HERE / "data" / "raw"))
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--per-thread", type=int, default=45)
    ap.add_argument("--random", type=int, default=0,
                    help="also digest N random baseline threads (≥4 comments) outside the top, prefixed R")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    raw = Path(args.raw)
    scored = [json.loads(line) for line in (raw.parent / "threads.jsonl").open()]
    threads = [(f"{i:02d}", t) for i, t in enumerate(scored[: args.top], 1)]
    pool = [t for t in scored[args.top:]
            if t["n_comments"] >= 4 and any(s.startswith("baseline") for s in t["strata"])]
    threads += [(f"R{i:02d}", t) for i, t in enumerate(random.Random(args.seed).sample(pool, min(args.random, len(pool))), 1)]
    want = {t["post_id"] for _, t in threads}
    posts = {p["id"]: p for p in map(json.loads, (raw / "posts.jsonl").open()) if p["id"] in want}
    by_post = defaultdict(list)
    for c in map(json.loads, (raw / "comments.jsonl").open()):
        if c["post_id"] in want:
            by_post[c["post_id"]].append(c)

    out = raw / "candidates"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.md"):
        old.unlink()
    for rank, t in threads:
        pid, cs = t["post_id"], by_post[t["post_id"]]
        has_kids = {c.get("parent_id") for c in cs}
        keep = [c for c in cs if c.get("parent_id") or c["id"] in has_kids
                or COMMIT.search(c.get("content") or "") or MENTION.search(c.get("content") or "")]
        keep.sort(key=lambda c: c.get("created_at") or "")
        keep = keep[: args.per_thread]
        name = {c["id"]: (c.get("author") or {}).get("name") for c in cs}
        p = posts.get(pid, {})
        lines = [
            f"# {t['title']}",
            (f"post_id: {pid} · submolt: {t['submolt']} · author: {t['post_author']} · "
             f"comments: {t['n_comments']} · participants: {t['participants']} · score: {t['score']}"),
            (f"signals: reciprocal={t['reciprocal']} turns_ab={t['turns_ab']} commit={t['commit_hits']} "
             f"mentions={t['mentions']} artifacts={t['artifacts']} template_share={t['template_share']}"),
            "", "## Post", clip(p.get("content"), 900), "",
            f"## Exchanges ({len(keep)} of {len(cs)} comments shown, chronological)",
        ]
        for c in keep:
            who = (c.get("author") or {}).get("name")
            to = name.get(c.get("parent_id"), t["post_author"]) if c.get("parent_id") else "POST"
            lines.append(f"- [{c['id'][:8]}] d{c.get('depth', 0)} **{who}** → {to}: {clip(c.get('content'), 420)}")
        (out / f"{rank}-{pid}.md").write_text("\n".join(lines) + "\n")
    print(f"{len(threads)} digests → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
