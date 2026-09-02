# A1 — Cascade-step contribution (A1-v1)

**Date:** 2026-08-24  
**Status:** candidate for freeze after author validation  
**Analysis type:** direct log query; no replay, no model inference, no causal step ablation.

## Scope and interpretation

A1 reports the **first deterministic cascade step that resolved each fast-path decision**. It does **not** estimate the causal performance loss that would result from removing a step: a decision unresolved at one step could fall through to a later deterministic step or to L3b.

## Source-of-truth chain and validation gates

1. `E.zip/data/session_e/missions.csv` — primary raw Session E decision table.
2. `session_e_v3.zip/session_e/results_E.json` — canonical Session E analysis cross-check.
3. Author-confirmed enriched `missions.csv` — same 226 decisions with additional fields; all raw columns are checked row-by-row.

- Enriched-vs-raw row/column identity gate: **PASS**.
- Raw cascade counts vs Session E v3 `results_E.json`: **PASS**.
- E0 exclusion accounting: **PASS**.

## Primary result — E0 excluded

Session E contains **216 primary decisions** after excluding E0. Of these, **112** were resolved by deterministic Steps 0–6 (**51.9%** of primary decisions).

| Step | First-resolving rule | n | % of fast path (N=112) | % of all primary decisions (N=216) | Median resolve_ms | Mean resolve_ms | Max resolve_ms |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | M3 learned association | 39 | 34.8% | 18.1% | 0.132 | 0.135 | 0.257 |
| 1 | explicit node ID | 18 | 16.1% | 8.3% | 0.191 | 0.178 | 0.233 |
| 2 | node name | 17 | 15.2% | 7.9% | 0.389 | 0.397 | 0.780 |
| 3 | object ID (obj_id) | 8 | 7.1% | 3.7% | 0.347 | 0.375 | 0.728 |
| 4 | attribute match | 13 | 11.6% | 6.0% | 0.465 | 0.499 | 0.960 |
| 5 | single class match | 3 | 2.7% | 1.4% | 0.457 | 0.444 | 0.500 |
| 6 | class + proximity | 14 | 12.5% | 6.5% | 0.383 | 0.389 | 0.519 |

Across all 112 primary fast-path decisions, `resolve_ms` was median **0.245 ms**, mean **0.281 ms**, range **0.072–0.960 ms**. All 112/112 observations were below 1 ms; only 4/112 were below 0.1 ms. Therefore the manuscript should describe the complete deterministic cascade as **sub-millisecond**, not `<0.1 ms`.

## Raw archival composition — E0 included

Including E0, **121** decisions carry a resolution step. The raw counts are Step 0–6 = 43, 18, 22, 8, 13, 3, 14.
E0 contributes **9** fast-path decisions: 4 at Step 0 and 5 at Step 2. Removing E0 yields the primary 112-decision composition.

## Workload dependence

The cascade composition is visibly block-dependent, so the percentages above are a description of the Session E workload rather than universal resolver probabilities. For example, E1 contributes Steps 0/1/2/6, E3 spans Steps 0/2/3/4/6, E4 and E5 contain no deterministic step resolutions, and E7 contributes only five fast-path decisions.

### E0-excluded block breakdown

| Block | All decisions | Fast path | Step counts (0→6) |
|---|---:|---:|---|
| E1 | 39 | 39 | 8/18/8/0/0/0/5 |
| E2 | 49 | 8 | 4/0/4/0/0/0/0 |
| E3 | 56 | 56 | 23/0/4/8/12/0/9 |
| E4 | 23 | 0 | 0/0/0/0/0/0/0 |
| E4b | 10 | 4 | 4/0/0/0/0/0/0 |
| E5 | 6 | 0 | 0/0/0/0/0/0/0 |
| E6 | 4 | 0 | 0/0/0/0/0/0/0 |
| E7 | 29 | 5 | 0/0/1/0/1/3/0 |

## Manuscript-ready statement

**In the E0-excluded Session E validation set, 112/216 decisions were resolved on the deterministic fast path. The first-resolving-step composition was 39 M3 Step-0 matches, 18 explicit-node-ID matches, 17 node-name matches, 8 object-ID matches, 13 attribute matches, 3 single-class matches, and 14 class-plus-proximity matches. All 112 deterministic resolutions completed in under 1 ms (median 0.245 ms; maximum 0.960 ms). These counts describe observed workload composition and are not a leave-one-step-out causal ablation.**

## Freeze recommendation

After author review, this A1 package can be marked **FROZEN** if the input hashes and all three validation gates remain unchanged. No R2-10 result is used by A1.
