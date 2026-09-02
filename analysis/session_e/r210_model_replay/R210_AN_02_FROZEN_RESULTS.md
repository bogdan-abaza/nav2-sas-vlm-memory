# R210-AN-02 — Frozen computational verification

**Status:** FROZEN

**Core claim:** **L3b interface-level model portability, not semantic model invariance.**

## Integrity and population

- Session E: 214 audit sessions / 226 decisions.
- VLM call path: **105 attempts = 69 accepted-node + 22 clarification/blocked + 14 error/parse; 91 timed records**.
- Frozen replay: **69 × 3 models × 3 seeds = 621 outcomes**; primary E0-excluded analysis: **68 × 3 × 3 = 612**.
- Clustering unit: **68 records**, not the 612 repeated outputs.

## Primary model comparison

| Model | Parser-contract compliance | Accepted node | Negation `-1` | Other `-1` | Contract failure | Archive reference agreement | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:4b (control) | 181/204 = 88.7% | 160/204 = 78.4% | 21/204 = 10.3% | 0/204 = 0.0% | 23/204 = 11.3% | 137/204 = 67.2% | 7.20 s |
| gemma4:e2b | 204/204 = 100.0% | 194/204 = 95.1% | 10/204 = 4.9% | 0/204 = 0.0% | 0/204 = 0.0% | 131/204 = 64.2% | 6.77 s |
| qwen3.5:9b | 199/204 = 97.5% | 165/204 = 80.9% | 33/204 = 16.2% | 1/204 = 0.5% | 5/204 = 2.5% | 120/204 = 58.8% | 14.63 s |

## Negation accounting

- Full Session E negation population: **39 activations**; **35** reached the post-VLM guard.
- Original model: **22/35 = 62.9%** clarification (`-1`), **13/35** actionable non-forbidden, **0** forbidden proposals; **4** error/parse before guard.
- The full-population 22/35 rate is **descriptive only and is not directly compared** with replay rates.
- Replayable outcome-conditioned subset: **13 records / 117 outcomes**, **0 forbidden selections**.
- The post-VLM guard is interpreted as a **defense-in-depth mechanism**; no observed Session E or replayable-subset case required it to block a forbidden-node proposal.

## M3 promotion stability

- Quiet corner: archived `[9,15,9,9]` reject; **8/9 replay arms promote** → historical decision is not robust.
- Gloves: archived `[9,9,9,9]` promote; **9/9 replay arms promote** → robust.
- Delivery: one image missing; **0/9 replay arms promote** under the fixed-missing partial counterfactual → rejection remains, but this is not a full multimodal substitution.
- Frozen interpretation: **the gate measures sampled-output stability, not semantic truth**.

## Verification

All frozen headline assertions embedded in this script passed. Any change to the acquisition, runner, population accounting, or headline counts causes the analyzer to fail rather than silently producing a different R210-AN-02 result.
