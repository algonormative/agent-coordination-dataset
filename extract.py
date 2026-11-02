#!/usr/bin/env python3
"""Pull a Moltbook traffic sample: posts plus full comment trees, read-only.

Three sampling strata, each tagged on the post row so analysis can weigh
them apart (the targeted strata are biased toward coordination by design):

  baseline  — /api/v1/posts?sort=new and sort=top pages
  search    — /api/v1/search for coordination vocabulary
  submolt   — top posts of submolts whose name/description reads as
              collaborative (projects, guilds, builds, swarms ...)

Uses moltbook_api.py: the key comes from MOLTBOOK_API_KEY and goes in the
Authorization header only, never logged. GETs only.

Output (JSONL, resumable — posts already in comments.jsonl are skipped):
  <out>/posts.jsonl     one row per post, with `strata` list
  <out>/comments.jsonl  one row per comment, flattened, with parent_id
  <out>/agents.jsonl    one row per author seen

Usage: uv run --no-project python extract.py [--out data/raw] [--min-comments 3]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import moltbook_api as mb

SEARCH_TERMS = [
    "coordinate", "collaborate", "let's build together", "working group",
    "proposal", "RFC", "protocol spec", "standard for agents", "join us",
    "who wants to", "looking for agents", "divide the work", "handoff",
    "bounty", "escrow", "pay another agent", "consensus", "vote",
    "open call", "co-author", "shared repo", "pull request", "swarm",
    "alliance", "guild", "pact", "agreement between agents", "task board",
    "I'll take", "count me in",
]
SUBMOLT_PAT = re.compile(
    r"collab|project|build|guild|swarm|dao|cooperat|coordinat|bounty|"
    r"market|hire|jobs|task|team|alliance|governance|protocol|standard",
    re.IGNORECASE,
)
PAUSE = 0.35


def get(path: str, key: str, tries: int = 4):
    for i in range(tries):
        try:
            r = mb.request("GET", path, key)
        except OSError as e:  # connection reset mid-read escapes the client
            r = {"error": repr(e)}
        if isinstance(r, dict) and r.get("success") is not False and "error" not in r:
            time.sleep(PAUSE)
            return r
        status = str(r.get("status") or r.get("error") or "")[:120] if isinstance(r, dict) else str(r)[:120]
        print(f"  retry {i + 1} {path}: {status}", file=sys.stderr)
        time.sleep(2 ** (i + 1))
    return None


def paged(path: str, key: str, list_key: str, pages: int):
    out, cur = [], None
    for _ in range(pages):
        sep = "&" if "?" in path else "?"
        r = get(path + (f"{sep}cursor={urllib.parse.quote(cur)}" if cur else ""), key)
        if not r:
            break
        out.extend(r.get(list_key) or [])
        cur = r.get("next_cursor")
        if not (r.get("has_more") and cur):
            break
    return out


def flatten(tree, parent_id=None):
    for c in tree or []:
        replies = c.pop("replies", None) or []
        c.setdefault("parent_id", parent_id)
        yield c
        yield from flatten(replies, c["id"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "raw"))
    ap.add_argument("--min-comments", type=int, default=3)
    ap.add_argument("--baseline-pages", type=int, default=8)
    ap.add_argument("--search-limit", type=int, default=40)
    ap.add_argument("--submolts", type=int, default=25)
    args = ap.parse_args()
    key = mb.load_key()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    posts: dict[str, dict] = {}

    def add(p: dict, stratum: str):
        if not p.get("id"):
            return
        row = posts.setdefault(p["id"], {**p, "strata": []})
        if stratum not in row["strata"]:
            row["strata"].append(stratum)

    for sort in ("new", "top"):
        for p in paged(f"/api/v1/posts?sort={sort}&limit=50", key, "posts", args.baseline_pages):
            add(p, f"baseline:{sort}")
    print(f"baseline: {len(posts)} posts", file=sys.stderr)

    for term in SEARCH_TERMS:
        q = urllib.parse.quote(term)
        r = get(f"/api/v1/search?q={q}&type=posts&limit={args.search_limit}", key)
        for p in (r or {}).get("results") or []:
            if p.get("type", "post") == "post":
                add(p, f"search:{term}")
    print(f"+search: {len(posts)} posts", file=sys.stderr)

    subs = paged("/api/v1/submolts?limit=100", key, "submolts", 10)
    picked = [s for s in subs if SUBMOLT_PAT.search(f"{s.get('name')} {s.get('description') or ''}")]
    picked.sort(key=lambda s: -(s.get("subscriber_count") or s.get("post_count") or 0))
    for s in picked[: args.submolts]:
        r = get(f"/api/v1/submolts/{urllib.parse.quote(s['name'])}/feed?sort=top&limit=25", key)
        for p in (r or {}).get("posts") or []:
            add(p, f"submolt:{s['name']}")
    print(f"+submolt ({len(picked[: args.submolts])} subs): {len(posts)} posts", file=sys.stderr)

    with open(out / "posts.jsonl", "w") as f:
        for p in posts.values():
            f.write(json.dumps(p) + "\n")

    done = set()
    cpath = out / "comments.jsonl"
    if cpath.exists():
        done = {json.loads(line)["post_id"] for line in cpath.open()}
    agents: dict[str, dict] = {}
    todo = [p for p in posts.values()
            if (p.get("comment_count") or 0) >= args.min_comments and p["id"] not in done]
    # search results carry no comment_count — fetch them regardless
    todo += [p for p in posts.values() if "comment_count" not in p and p["id"] not in done]
    print(f"fetching trees for {len(todo)} posts", file=sys.stderr)
    with open(cpath, "a") as f:
        for i, p in enumerate(todo, 1):
            r = get(f"/api/v1/posts/{p['id']}/comments?sort=old&limit=500", key)
            for c in flatten((r or {}).get("comments")):
                a = c.get("author") or {}
                if a.get("id"):
                    agents[a["id"]] = a
                c["post_id"] = p["id"]
                f.write(json.dumps(c) + "\n")
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
                f.flush()
    with open(out / "agents.jsonl", "a") as f:
        for a in agents.values():
            f.write(json.dumps(a) + "\n")
    print("done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
