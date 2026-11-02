#!/usr/bin/env python3
"""Build data/conversations.json for the report's Conversations tab.

Every thread coded level ≥ 3, plus a few hand-picked contrast cases that show
what non-coordination looks like. Each entry carries the post, its labels, and
the full comment tree (deleted comments dropped).

Usage: uv run --no-project python build_viewer.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from score import unmark

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
KEEP = ("id", "parent_id", "depth", "created_at", "content", "upvotes")

# post-id prefix -> why it is shown alongside the coordinating threads
CONTRAST = {
    "525ccf97": "Baseline noise: spam, promotional links and stock praise under a short market note.",
    "9a6ed68a": "Templated talk: many comments are near-identical stock questions about zero trust.",
    "c2e024c8": "Offers without uptake: many agents propose testing or collaboration and the author never answers.",
    "858fc089": "Proposals left hanging: two concrete standards are proposed and only restated, never taken up.",
    "ed5257d6": "Dialogue without joint action: a long, tightly interlocked exchange that converges on a framing and stops there.",
    "166f4db6": "Hub-and-spoke: the author answers nearly every commenter, but commenters rarely address each other.",
}


def main() -> int:
    labels = [json.loads(line) for line in (HERE / "data" / "labels.jsonl").open()]
    pick = [r for r in labels if r["coordination_level"] >= 3]
    pick += [r for r in labels if r["post_id"][:8] in CONTRAST]
    want = {r["post_id"] for r in pick}

    posts = {p["id"]: p for p in map(json.loads, (RAW / "posts.jsonl").open()) if p["id"] in want}
    tree, seen = defaultdict(list), set()
    for c in map(json.loads, (RAW / "comments.jsonl").open()):
        if c["post_id"] in want and c["id"] not in seen and not c.get("is_deleted") and c.get("content"):
            seen.add(c["id"])
            row = {k: c.get(k) for k in KEEP}
            row["author"] = (c.get("author") or {}).get("name")
            tree[c["post_id"]].append(row)

    out = []
    for lab in pick:
        p = posts[lab["post_id"]]
        out.append({
            "group": "contrast" if lab["post_id"][:8] in CONTRAST else f"level{lab['coordination_level']}",
            "note": CONTRAST.get(lab["post_id"][:8]),
            "post": {"id": p["id"], "title": unmark(p.get("title")), "content": unmark(p.get("content")),
                     "author": (p.get("author") or {}).get("name"),
                     "submolt": p.get("submolt_name") or (p.get("submolt") or {}).get("name"),
                     "created_at": p.get("created_at"), "upvotes": p.get("upvotes"),
                     "url": f"https://www.moltbook.com/post/{p['id']}"},
            "labels": {k: lab.get(k) for k in (
                "coordination_level", "coordination_code", "forms", "interaction_quality",
                "evidence", "human_principal", "exemplar", "summary", "confidence", "frame")},
            "signals": lab["signals"],
            "comments": sorted(tree[lab["post_id"]], key=lambda c: c["created_at"] or ""),
        })
    # U+FFFD in the source text is kept, but as a JSON escape: the artifact host rejects it raw.
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("\ufffd", "\\ufffd")
    (HERE / "data" / "conversations.json").write_text(text)
    print(f"{len(out)} threads, {sum(len(t['comments']) for t in out)} comments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
