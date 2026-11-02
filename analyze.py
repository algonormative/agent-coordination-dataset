#!/usr/bin/env python3
"""Corpus-level descriptive statistics for the report.

Reads data/raw/{posts,comments,agents}.jsonl and writes data/stats.json:
structure (reply share, depth, OP participation), dyadic reciprocity,
participation inequality (Gini, top-1% share), stock openers, reply
latency, principal framing ("my human"), and per-stratum splits.

Usage: uv run --no-project python analyze.py
"""
from __future__ import annotations

import json
import re
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from score import opener

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
HUMAN = re.compile(r"\bmy (human|operator|owner|creator)\b", re.IGNORECASE)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def gini(xs):
    xs = sorted(xs)
    n, cum = len(xs), 0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def main() -> int:
    posts = {p["id"]: p for p in map(json.loads, (RAW / "posts.jsonl").open())}
    comments, seen, deleted = [], set(), 0
    for c in map(json.loads, (RAW / "comments.jsonl").open()):
        if c.get("is_deleted") or c.get("content") in (None, "", "[deleted]"):
            deleted += 1
            continue
        if c["id"] not in seen:
            seen.add(c["id"])
            comments.append(c)
    by_id = {c["id"]: c for c in comments}
    by_post = defaultdict(list)
    for c in comments:
        by_post[c["post_id"]].append(c)

    def name(c):
        return (c.get("author") or {}).get("name") or "?"

    def op(pid):
        return ((posts.get(pid) or {}).get("author") or {}).get("name") or "?"

    replies = [c for c in comments if c.get("parent_id")]
    depth = Counter(min(c.get("depth") or 0, 5) for c in comments)

    # OP participation: does the post author ever comment in their own thread?
    threads = [pid for pid in by_post if by_post[pid]]
    op_active = sum(1 for pid in threads if any(name(c) == op(pid) for c in by_post[pid]))

    # dyads: directed edges commenter -> addressee (parent author, else OP)
    edges = Counter()
    for c in comments:
        to = name(by_id[c["parent_id"]]) if c.get("parent_id") in by_id else op(c["post_id"])
        if to != name(c):
            edges[(name(c), to)] += 1
    dyads = {frozenset(e) for e in edges}
    mutual = sum(1 for d in dyads if len(d) == 2 and tuple(d) in edges and tuple(d)[::-1] in edges)

    # inequality
    per_author = Counter(name(c) for c in comments)
    counts = sorted(per_author.values(), reverse=True)
    top1 = counts[: max(1, len(counts) // 100)]

    # stock openers
    ops = Counter(opener(c.get("content")) for c in comments)
    stock = sum(1 for c in comments if ops[opener(c.get("content"))] >= 3)

    # latency parent -> reply (minutes)
    lat = []
    for c in replies:
        p = by_id.get(c["parent_id"])
        if p and c.get("created_at") and p.get("created_at"):
            d = (ts(c["created_at"]) - ts(p["created_at"])).total_seconds() / 60
            if d >= 0:
                lat.append(d)
    # top-level latency post -> comment
    lat0 = []
    for c in comments:
        if not c.get("parent_id") and (posts.get(c["post_id"]) or {}).get("created_at"):
            d = (ts(c["created_at"]) - ts(posts[c["post_id"]]["created_at"])).total_seconds() / 60
            if d >= 0:
                lat0.append(d)

    # bursts: max comments by one author within any 60s window
    times = defaultdict(list)
    for c in comments:
        if c.get("created_at"):
            times[name(c)].append(ts(c["created_at"]).timestamp())
    burst = Counter()
    for a, tl in times.items():
        tl.sort()
        j = 0
        for i in range(len(tl)):
            while tl[i] - tl[j] > 60:
                j += 1
            burst[a] = max(burst[a], i - j + 1)

    nonascii = sum(1 for c in comments if sum(ord(ch) > 127 for ch in (c.get("content") or "")[:300]) > 30)
    lens = [len((c.get("content") or "").split()) for c in comments]
    verif = Counter(c.get("verification_status") or "none" for c in comments)
    dates = sorted(c["created_at"] for c in comments if c.get("created_at"))
    pdates = sorted(p["created_at"] for p in posts.values() if p.get("created_at"))

    strata = defaultdict(lambda: {"posts": 0, "threads": 0, "comments": 0, "replies": 0})
    for p in posts.values():
        for s in {s.split(":")[0] for s in p.get("strata", [])}:
            strata[s]["posts"] += 1
            cs = by_post.get(p["id"], [])
            if cs:
                strata[s]["threads"] += 1
                strata[s]["comments"] += len(cs)
                strata[s]["replies"] += sum(1 for c in cs if c.get("parent_id"))

    stats = {
        "collected": "2026-11-02",
        "posts": len(posts), "threads_with_comments": len(threads), "comments": len(comments), "deleted_excluded": deleted,
        "comment_authors": len(per_author),
        "submolts": len({p.get("submolt_name") or (p.get("submolt") or {}).get("name") for p in posts.values()}),
        "post_date_range": [pdates[0][:10], pdates[-1][:10]] if pdates else None,
        "comment_date_range": [dates[0][:10], dates[-1][:10]] if dates else None,
        "reply_share_pct": pct(len(replies), len(comments)),
        "depth_dist": dict(sorted(depth.items())),
        "op_active_in_own_thread_pct": pct(op_active, len(threads)),
        "dyads": len(dyads), "mutual_dyads": mutual, "mutual_dyad_pct": pct(mutual, len(dyads)),
        "gini_comments_per_author": round(gini(list(per_author.values())), 3),
        "top1pct_author_share_pct": pct(sum(top1), len(comments)),
        "median_comments_per_author": st.median(counts),
        "stock_opener_share_pct": pct(stock, len(comments)),
        "top_openers": [(o, n) for o, n in ops.most_common(12) if o],
        "reply_latency_min": {"median": round(st.median(lat), 1), "p25": round(st.quantiles(lat, n=4)[0], 1),
                              "p75": round(st.quantiles(lat, n=4)[2], 1)} if lat else None,
        "toplevel_latency_min_median": round(st.median(lat0), 1) if lat0 else None,
        "authors_bursting_5_per_min": sum(1 for v in burst.values() if v >= 5),
        "max_burst_per_min": max(burst.values()) if burst else 0,
        "my_human_comment_pct": pct(sum(1 for c in comments if HUMAN.search(c.get("content") or "")), len(comments)),
        "my_human_post_pct": pct(sum(1 for p in posts.values() if HUMAN.search(p.get("content") or "")), len(posts)),
        "nonlatin_comment_pct": pct(nonascii, len(comments)),
        "median_comment_words": st.median(lens),
        "verification_status": dict(verif),
        "strata": {k: {**v, "reply_share_pct": pct(v["replies"], v["comments"])} for k, v in strata.items()},
    }
    (HERE / "data" / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False))
    print(json.dumps(stats, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
