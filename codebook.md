# Coordination codebook (v1, 2026-11-01)

The unit of analysis is the **thread**: one post plus its comment tree, as rendered in a digest. A digest shows the reply exchanges and leaves out the drive-by top-level comments. Code only what the digest shows. Do not infer intentions the text does not show.

## 1. `coordination_level` (ordinal 0–4; code the highest level the thread reaches)

| Level | Code | Definition | Minimal evidence |
|---|---|---|---|
| 0 | `none` | Adjacent monologues. Agents post near each other but do not orient to one another's specific contributions. | Replies could be pasted under any post. |
| 1 | `discursive` | Agents take up each other's specific claims through agreement, refinement, challenge or repair, and converge on, or contest, a shared framing or norm. Nobody proposes joint action. | A reply quotes or builds on a specific claim in the prior turn. |
| 2 | `proposed` | Someone explicitly proposes joint or interdependent action: a shared standard, a division of labour, an exchange, a collective act, or a joint test. No other agent takes it up. | A proposal move addressed to others. |
| 3 | `taken_up` | Another agent accepts, counter-proposes, or commits to a part of the proposal. | Proposal plus acceptance or commitment by a different author. |
| 4 | `enacted` | The digest shows that the joint action happened: a report-back, a shared artifact (repo, PR, spec, dataset), a transaction, or a follow-up result attributed to the arrangement. | A report-back or artifact tied to an earlier commitment. |

## 2. `forms` (multi-select; leave empty if level 0)

- `task_division`: splitting work, assigning roles.
- `protocol_negotiation`: agreeing on a format, standard, schema or procedure for interoperation.
- `joint_artifact`: co-producing a document, code, dataset or test.
- `exchange`: trade, payment, bounty, or service for service.
- `collective_action`: campaigns, votes, coordinated posting, boycotts, petitions.
- `knowledge_pooling`: contributing one's own measurements or cases toward a shared question.
- `norm_enforcement`: sanctioning, correcting or calling out a violation of a group norm.
- `repair`: resolving a misunderstanding about what was said or meant.

## 3. `interaction_quality` (one value)

- `dialogic`: most shown replies address specifics of the turn they answer.
- `mixed`
- `parallel`: replies are mostly generic or interchangeable.
- `templated`: replies visibly reuse stock openers, closers or structures.

## 4. `evidence` (0–4 items)

`{comment_id: "<8-char id from digest>", move: proposal|acceptance|counterproposal|commitment|report_back|challenge|repair|uptake, quote: "<≤25 words, verbatim>"}`

## 5. Other fields

- `human_principal`: true if any participant invokes a human operator ("my human", "my operator") as a source of permission, instruction or constraint.
- `exemplar`: true if the thread would serve as a clear teaching example of agent-to-agent coordination at level ≥ 2. Use it sparingly.
- `summary`: two plain sentences: what the thread is about, and what coordination (if any) happens.
- `confidence`: `high`, `med` or `low`.
