# A3 — M3 promotion-threshold sensitivity

**Status:** FROZEN 2026-08-25  
**Manuscript:** ROBOT-D-26-01090 major revision

This public-safe analysis reproduces and characterizes the frozen Session E M3 promotion gate over the controlled E4.1 and E4b.1 induction candidates.

## What it tests

Frozen rule:

```text
frequency >= 3
AND round(dominant_count / total, 2) >= 0.80
AND L3b_vlm_count >= 1
```

`None` node outcomes remain in the denominator. The analysis first reproduces the archived E4 rejection / E4b promotion outputs exactly. Only after that gate passes does it sweep:

- minimum frequency: 1–6;
- consistency threshold: 0.00–1.00 in 0.01 increments.

## Population

Primary experimental unit = **candidate association, N=3**:

- E4.1 deliveries: `[10, None, 10, 5]` → frequency 4, consistency 0.50 → reject at frozen rule;
- E4.1 quiet corner: `[9, 15, 9, 9]` → frequency 4, consistency 0.75 → reject;
- E4b.1 wet gloves: `[9, 9, 9, 9]` → frequency 4, consistency 1.00 → promote.

## Main result

At the frozen `(frequency=3, consistency=0.80)` operating point, the standalone analysis reproduces all three archived promotion decisions with zero mismatches.

The observed sensitivity is piecewise:

- consistency `<=0.50` (with minimum frequency <=4): 3/3 candidates promote;
- `0.51–0.75`: 2/3 promote;
- `0.76–1.00`: only the 4/4-consistent candidate promotes;
- minimum frequency >=5: 0/3 promote.

Thus `0.80` lies in the observed `0.76–1.00` plateau. The 0.75 quiet-corner candidate is near the boundary: lowering the consistency threshold from 0.80 to 0.75 would promote it. Conversely, because all three candidates have frequency 4, this Session E subset does not empirically distinguish minimum frequency 3 from 1, 2, or 4.

## Interpretation boundary

A3 is a **post-hoc sensitivity characterization of a pre-frozen rule**, not parameter tuning. Promotion consistency measures repeated-output stability, not semantic correctness.

## Reproduction

Place the released Session E raw archive and canonical analysis package at known paths, then run:

```bash
python3 analyze_A3_m3_promotion_sensitivity.py \
  --session-e-zip /path/to/E.zip \
  --canonical-analysis-zip /path/to/session_e_v3.zip \
  --out-dir .
```

The script requires only Python standard library plus the included, publication-approved `sas_text.py` v1.2.0. It does not import protected SAS production modules.
