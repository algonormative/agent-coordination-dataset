#!/usr/bin/env python3
"""Assemble the committed dataset from raw pulls + labels.

  data/labels.jsonl              all coded threads (top-scored + random baseline),
                                 codebook fields + scorer signals + sample frame
  data/coordination-sample.jsonl threads coded level ≥ 3 (uptake or enacted), each
                                 with its labels and full flattened comment tree

Comment rows keep: id, parent_id, depth, author, created_at, content, upvotes,
is_spam, verification_status. Deleted comments are dropped.

Usage: uv run --no-project python build_sample.py <labels-all.jsonl> [--min-level 3]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from score import unmark

HERE = Path(__file__).parent
KEEP = ("id", "parent_id", "depth", "created_at", "content", "upvotes", "is_spam", "verification_status")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--min-level", type=int, default=3)
    args = ap.parse_args()
    raw = HERE / "data" / "raw"
    threads = {t["post_id"]: t for t in map(json.loads, (HERE / "data" / "threads.jsonl").open())}
    posts = {p["id"]: p for p in map(json.loads, (raw / "posts.jsonl").open())}
    labels = [json.loads(line) for line in Path(args.labels).read_text().splitlines()]
    for lab in labels:
        lab["frame"] = "random_baseline" if lab["file"].startswith("R") else "top_scored"
        lab["signals"] = {k: threads[lab["post_id"]][k] for k in (
            "n_comments", "participants", "reciprocal", "turns_ab", "max_depth",
            "commit_hits", "mentions", "artifacts", "template_share", "score")}
        lab.pop("file", None)
    labels.sort(key=lambda r: (-r["coordination_level"], r["frame"], r["post_id"]))
    with open(HERE / "data" / "labels.jsonl", "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in labels)

    want = {r["post_id"] for r in labels if r["coordination_level"] >= args.min_level}
    tree = defaultdict(list)
    for c in map(json.loads, (raw / "comments.jsonl").open()):
        if c["post_id"] in want and not c.get("is_deleted") and c.get("content"):
            row = {k: c.get(k) for k in KEEP}
            row["author"] = (c.get("author") or {}).get("name")
            tree[c["post_id"]].append(row)
    with open(HERE / "data" / "coordination-sample.jsonl", "w") as f:
        for lab in (r for r in labels if r["post_id"] in want):
            p = posts.get(lab["post_id"], {})
            f.write(json.dumps({
                "post": {"id": p.get("id"), "title": unmark(p.get("title")), "content": unmark(p.get("content")),
                         "author": (p.get("author") or {}).get("name"),
                         "submolt": p.get("submolt_name") or (p.get("submolt") or {}).get("name"),
                         "created_at": p.get("created_at"), "upvotes": p.get("upvotes"),
                         "url": f"https://www.moltbook.com/post/{lab['post_id']}"},
                "labels": lab,
                "comments": sorted(tree[lab["post_id"]], key=lambda c: c["created_at"] or ""),
            }, ensure_ascii=False) + "\n")
    print(f"{len(labels)} labels; {len(want)} threads at level ≥ {args.min_level}, "
          f"{sum(len(tree[i]) for i in want)} comments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
