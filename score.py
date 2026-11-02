#!/usr/bin/env python3
"""Score each extracted thread for agent-to-agent coordination signal.

Deterministic heuristics only — the output is a ranked candidate list for a
human/LLM labeling pass, not a verdict. Per thread:

  participants   distinct comment authors (post author included)
  reply_edges    parent-author → child-author pairs, self-replies dropped
  reciprocal     unordered author pairs with replies in both directions
  turns_ab       longest A→B→A… alternation along one reply chain
  commit_hits    commitment / proposal phrases in replies (depth ≥ 1)
  mentions       @name references to another participant of the thread
  artifacts      links to repos, specs, endpoints, gists
  template_share comments whose opening 6 words recur ≥ 3× corpus-wide
                 (engagement-theatre openers) — subtracted

Writes <raw>/../threads.jsonl (all threads, scored) and prints the top N.
Usage: uv run --no-project python score.py [--raw data/raw] [--top 40]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

COMMIT = re.compile(
    r"\b(i'?ll (take|draft|write|build|run|send|open|ship|handle|test|post)|"
    r"i will (take|draft|write|build|run|send|open|handle)|i can take|count me in|"
    r"i'?m in\b|on it\b|deal\b|agreed\b|let'?s (do|build|try|test|draft|start|meet|sync|split|coordinate)|"
    r"we (could|should) (build|split|draft|standardi[sz]e|agree|try)|"
    r"(i|we) propose|proposal:|next step|division of labou?r|split (the|this) (work|task)|"
    r"you take|you handle|i'?ll handle|hand(ing)? (it )?off|handoff|"
    r"ping me|dm me|send me|reply with|sign(ed)? up|vote (on|for)|"
    r"fork(ed)? (it|the repo)|pull request|\bPR\b|merged)",
    re.IGNORECASE,
)
ARTIFACT = re.compile(r"https?://(github\.com|gist\.github|gitlab|[\w.-]+/(spec|rfc|api|docs))", re.IGNORECASE)
MENTION = re.compile(r"@([A-Za-z0-9_\-]{3,40})")
WORD = re.compile(r"[a-z']+")
# The search endpoint wraps matched terms in ⟦HL⟧…⟦/HL⟧ inside post text.
SEARCH_HL = re.compile(r"⟦/?HL⟧")


def unmark(text: str | None) -> str | None:
    return SEARCH_HL.sub("", text) if text else text


def opener(text: str) -> str:
    return " ".join(WORD.findall((text or "").lower())[:6])


def chain_alternation(cid, by_id, author_of):
    """Longest strict A,B,A,B… run walking up from comment cid."""
    seq = []
    while cid:
        seq.append(author_of[cid])
        cid = by_id[cid].get("parent_id")
    best = run = 1
    for i in range(2, len(seq)):
        if seq[i] == seq[i - 2] and seq[i] != seq[i - 1]:
            run += 1
            best = max(best, run + 1)
        else:
            run = 1
    return best if len(seq) > 1 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(Path(__file__).parent / "data" / "raw"))
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()
    raw = Path(args.raw)
    posts = {p["id"]: p for p in map(json.loads, (raw / "posts.jsonl").open())}
    by_post = defaultdict(dict)
    for c in map(json.loads, (raw / "comments.jsonl").open()):
        by_post[c["post_id"]][c["id"]] = c

    openers = Counter(opener(c.get("content")) for cs in by_post.values() for c in cs.values())
    rows = []
    for pid, cs in by_post.items():
        if not cs:
            continue
        post = posts.get(pid, {"id": pid})
        post_author = ((post.get("author") or {}).get("name")) or "?"
        author_of = {cid: (c.get("author") or {}).get("name") or "?" for cid, c in cs.items()}
        people = set(author_of.values()) | {post_author}
        edges, depth = Counter(), 0
        commit = mentions = artifacts = templ = 0
        for cid, c in cs.items():
            text = c.get("content") or ""
            parent = c.get("parent_id")
            to = author_of.get(parent, post_author) if parent else post_author
            if to != author_of[cid]:
                edges[(author_of[cid], to)] += 1
            depth = max(depth, c.get("depth") or 0)
            if parent:
                commit += len(COMMIT.findall(text))
            mentions += sum(1 for m in MENTION.findall(text) if m in people and m != author_of[cid])
            artifacts += len(ARTIFACT.findall(text))
            if openers[opener(text)] >= 3:
                templ += 1
        pairs = {frozenset(e) for e in edges}
        recip = sum(1 for p in pairs if len(p) == 2 and tuple(p) in edges and tuple(p)[::-1] in edges)
        turns = max((chain_alternation(cid, cs, author_of) for cid in cs), default=1)
        tshare = templ / len(cs)
        score = (3 * min(recip, 12) + 2 * min(commit, 8) + min(mentions, 10) + 2 * max(turns - 2, 0)
                 + min(depth, 6) + 2 * min(artifacts, 5)) * (1 - tshare)
        rows.append({
            "post_id": pid, "title": post.get("title"), "submolt": post.get("submolt_name")
            or (post.get("submolt") or {}).get("name"), "strata": post.get("strata", []),
            "post_author": post_author, "n_comments": len(cs), "participants": len(people),
            "reply_edges": sum(edges.values()), "reciprocal": recip, "turns_ab": turns,
            "max_depth": depth, "commit_hits": commit, "mentions": mentions,
            "artifacts": artifacts, "template_share": round(tshare, 3), "score": round(score, 2),
        })
    rows.sort(key=lambda r: -r["score"])
    with open(raw.parent / "threads.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"{len(rows)} threads scored → {raw.parent / 'threads.jsonl'}")
    for r in rows[: args.top]:
        print(f"{r['score']:6.1f}  rec={r['reciprocal']:<2} ab={r['turns_ab']:<2} cm={r['commit_hits']:<2} "
              f"d={r['max_depth']} n={r['n_comments']:<3} tpl={r['template_share']:.2f}  {(r['title'] or '')[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
