# Agent coordination dataset

A sample of agent-to-agent traffic on [Moltbook](https://www.moltbook.com), the Reddit-style forum whose posters are AI agents, with 100 threads coded for coordination. The 22 threads where one agent's proposal is taken up or carried through by others are extracted with their full comment trees.

**Report and thread viewer:** <https://algonormative.github.io/agent-coordination-dataset/>
**Downloads:** [v0.1.0 release](https://github.com/algonormative/agent-coordination-dataset/releases/tag/v0.1.0)

Collected 2026-11-02 (UTC), read-only, through Moltbook's public API.

## Headline numbers

| | |
|---|---|
| Corpus | 2,341 posts · 1,699 threads with comments · 76,017 comments (deleted excluded) · 7,428 comment authors · 124 submolts |
| Reciprocity | 35% of comments are replies; 10% of directed author pairs reply both ways |
| Templated talk | 16.5% of comments open with a six-word opener used at least three times |
| Coordination in ordinary threads | about 5% of random threads reach uptake or enactment (2 of 40; weighted 4.7%, 95% CI ≈ 1–17%) |
| Where it happens | median 13 participants in coordinating threads, against 80 elsewhere |
| Reliability | 25-thread double-coding: 22/25 exact; quadratic κ = 0.91 (both coders are LLMs of one family) |

## Files

In the repository:

| File | Contents |
|---|---|
| `data/coordination-sample.jsonl` | The 22 threads coded level ≥ 3: post, labels, evidence turns, full flattened comment tree (1,304 comments) |
| `data/labels.jsonl` | All 100 coded threads: codebook fields, sample frame (`top_scored` or `random_baseline`), scorer signals |
| `data/conversations.json` | The 28 threads in the report's Conversations tab (the 22 plus six contrast cases) |
| `data/threads.jsonl` | Per-thread interaction signals for all 1,699 threads (reciprocity, A↔B alternation, depth, commitment phrases, template share, score) |
| `data/stats.json` | Every corpus statistic in the report |
| `data/coder-labels.jsonl` | Raw coder output, before `build_sample.py` joins in frame and signals |
| `data/irr-coder2.jsonl`, `data/irr-sample.txt` | Second-coder labels and the 25-thread reliability subsample |
| `data/comparables/nostr-dvm-2026-11-02.jsonl` | 953 Nostr NIP-90 job events from two public relays over about two hours |
| `codebook.md` | The coordination codebook: a 0–4 ladder (none, discursive, proposed, taken up, enacted), forms, interaction quality, evidence moves |

In the release only (`moltbook-raw-2026-11-02.tar.gz`, ~30 MB; 121 MB unpacked), extracted to `data/raw/`:

| File | Contents |
|---|---|
| `posts.jsonl` | 2,341 posts as served, each tagged with its sampling `strata` |
| `comments.jsonl` | 77,885 comment rows, flattened from the nested trees with `parent_id`, including deleted stubs |
| `agents.jsonl` | 6,324 agent profiles (name, description, karma, follower counts, timestamps) |
| `candidates/*.md` | The 100 trimmed digests the coders read |

## Sampling

Three strata, tagged on each post: **baseline** (the `new` and `top` feeds), **search** (30 coordination terms such as "working group", "RFC", "bounty") and **submolt** (top posts of communities whose names read as collaborative). The targeted strata are biased toward coordination by design; prevalence figures use the random baseline only. Comment trees were fetched for posts reporting at least three comments (four after a mid-pull restart).

The 100 coded threads are the top 60 by a heuristic score and 40 drawn at random (seed 7).

## Caveats

- **LLM coding.** Five Sonnet coders labelled the threads in interleaved batches; a blind second coder of the same family double-coded 25. Agreement may reflect shared priors. Human double-coding is the obvious next step.
- **The API under-serves.** The comment endpoint returns fewer comments than a post's count reports, and nothing below depth 5. Coders saw digests capped at 45 exchanges per thread.
- **Search highlights.** Posts pulled through search carry `⟦HL⟧…⟦/HL⟧` markers in their text in the raw files. `score.unmark` strips them in the built files; the coders' digests still had them.
- **Time skew.** Dates run from 2026-01-28 to 2026-11-02, weighted toward March and late October–November; 18 of the 22 coordinating threads are from October.

## Ethics

The posters are software agents, but each has a human operator, and some handles or profile descriptions name that person or their social-media account. Handles, text and profiles are kept as served so analyses can follow agents across threads. Email addresses in any text field are replaced with `[email]` (`redact.py`); nothing else is altered. The collector operates one agent on Moltbook; it does not appear in the coded sample.

If you operate an agent in this data and want its content removed, open an issue.

## Rebuild

Python 3.10+, standard library only.

```bash
MOLTBOOK_API_KEY=... python extract.py --out data/raw   # pull (resumable, GETs only)
python redact.py                                        # redact emails, dedupe agents
python score.py                                         # data/threads.jsonl
python analyze.py                                       # data/stats.json
python excerpt.py --top 60 --random 40 --seed 7 --per-thread 45   # coder digests
python build_sample.py data/coder-labels.jsonl          # labels.jsonl, coordination-sample.jsonl
python build_viewer.py                                  # conversations.json
```

A fresh pull will differ from this one. To reproduce the published files exactly, unpack the release tarball with `tar -xzf moltbook-raw-2026-11-02.tar.gz -C data` and start at `score.py`.

## License

Code: MIT (`LICENSE`). Annotations (codebook, labels, statistics): CC BY 4.0. Post, comment and profile text belongs to its authors and is redistributed for research.
