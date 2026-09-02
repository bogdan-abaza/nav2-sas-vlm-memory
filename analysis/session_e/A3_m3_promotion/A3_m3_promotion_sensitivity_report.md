# A3 — M3 frequency / consistency promotion-threshold sensitivity

**Status:** FROZEN 2026-08-25  
**Analysis ID:** `A3_m3_promotion_sensitivity_v1`  
**Scope:** post-hoc offline sensitivity analysis of the **frozen Session E M3 promotion gate**. This is not parameter tuning and not a physical rerun.

## Reproduction gate

The standalone public-safe implementation reads the released E4.1 and E4b.1 audit logs, clusters instructions with released `sas_text.py` v1.2.0, and applies the documented promotion rule:

`frequency >= 3 AND round(dominant_count / total, 2) >= 0.80 AND L3b_vlm_count >= 1`

`None` node outcomes remain in the node counter and denominator, matching the frozen extractor convention.

**Gate: PASS** — 3/3 candidate associations reproduced; 0 mismatches.  
Canonical `session_e_v3` cross-check: **PASS**.

## Controlled induction candidates

| Candidate | Block | Node outcomes | Frequency | Rounded consistency | Nominal outcome |
|---|---|---|---:|---:|---|
| `deliveries` | E4.1 | `[10, None, 10, 5]` | 4 | 0.50 | REJECT |
| `quiet_corner` | E4.1 | `[9, 15, 9, 9]` | 4 | 0.75 | REJECT |
| `wet_gloves` | E4b.1 | `[9, 9, 9, 9]` | 4 | 1.00 | PROMOTE |


At the frozen operating point (`minimum frequency = 3`, `consistency threshold = 0.80`), the two E4.1 candidates are rejected and the E4b.1 `wet_gloves` association is promoted, exactly reproducing the archived Session E outputs.

## Sensitivity findings

1. **Consistency is the discriminating parameter in the controlled Session E candidates.** With minimum frequency fixed at 3:
   - threshold `<= 0.50`: all three candidates promote;
   - `0.51–0.75`: `quiet_corner` and `wet_gloves` promote;
   - `0.76–1.00`: only `wet_gloves` promotes.

2. **The frozen 0.80 threshold lies on a stable observed plateau (`0.76–1.00`)** for these three candidates: only the 4/4-consistent association is promoted.

3. **The `quiet_corner` rejection is close to the boundary.** Its extractor-rounded consistency is 0.75, only 0.05 below the frozen threshold. A threshold of exactly 0.75 would promote it. This shows why promotion should be described as a stability gate rather than a semantic-correctness guarantee.

4. **Frequency sensitivity is weakly identified by Session E.** All three controlled candidates have frequency 4. At consistency 0.80, minimum-frequency settings 1, 2, 3, and 4 produce the same result; setting 5 or higher rejects all candidates, including the otherwise stable `wet_gloves` case. Thus Session E does **not** empirically optimize or uniquely justify `minimum frequency = 3`.

5. **Rounding is implemented production-faithfully.** The analysis computes `round(dominant_count / total, 2)` before comparison. For the three Session E candidates (2/4, 3/4, 4/4), rounding does not itself change an outcome, but retaining this convention is necessary for reproducibility and for other populations.

## Interpretation for the revision

A3 supports a conservative claim: the frozen promotion rule is exactly reproducible on the controlled Session E induction cases, and the 0.80 consistency threshold rejects both observed unstable candidates while admitting the 4/4-stable association. The analysis does **not** establish that 0.80 or frequency 3 is globally optimal. The gate measures repeated-output stability; semantic correctness requires separate safeguards and evidence.

This sensitivity analysis should therefore be presented as **post-hoc robustness characterization of a pre-frozen rule**, not as data-driven threshold selection.

## Public-release boundary

The public A3 artifact contains the standalone analysis, released `sas_text.py`, machine-readable outputs and provenance. It does **not** contain or import the protected production memory extractor or other protected SAS runtime source files.

## Files

- `analyze_A3_m3_promotion_sensitivity.py` — standalone analysis
- `sas_text.py` — approved released text-processing utility
- `A3_m3_candidate_replay.csv` — reconstructed candidate-level evidence
- `A3_m3_promotion_sensitivity_grid.csv` — candidate-level 2D grid
- `A3_m3_promotion_summary_grid.csv` — compact 2D grid summary
- `A3_m3_frequency_keypoints.csv` — frequency sweep at consistency 0.80
- `A3_m3_consistency_keypoints.csv` — consistency boundary keypoints at frequency 3
- `A3_m3_promotion_sensitivity_results.json` — machine-readable summary
- `A3_INPUT_PROVENANCE.md` — provenance and scope
- `A3_CHECKSUMS_SHA256.txt` — artifact checksums

## Limitations

- Primary experimental unit here is the **candidate association**, N=3, not the 12 underlying audit records.
- The three candidates are intentionally controlled induction cases, not a population sample from which to infer a universally optimal threshold.
- The `>=1 L3b_vlm` requirement is held fixed and is not itself ablated.
- A3 does not assess semantic ground-truth correctness of the promoted node.
