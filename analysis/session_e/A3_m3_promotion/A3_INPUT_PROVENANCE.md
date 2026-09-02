# A3 input provenance

**Status:** FROZEN 2026-08-25

## Reviewer-facing source chain

1. **Primary raw evidence:** released Session E archive (`E.zip`), SHA-256 `9e2f1dbc0269a056efac7594e679c9b643a59b0a22a0916e8dde8c422f945f33`.
2. **Controlled induction inputs:** 8 E4.1 audit JSONLs and 4 E4b.1 audit JSONLs under the day-2 memory folders.
3. **Canonical analysis cross-check:** `session_e_v3.zip` / `results_E.json` (PASS).
4. **Public SAS source used by this analysis:** `sas_text.py` v1.2.0, SHA-256 `aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1`.
5. **Archived extractor outputs used for the reproduction gate:** E4.2 and E4b `M3_operator_preferences.jsonl` plus their compiled `memory_digest.json` files.

## Population

- E4.1: 8 audit files, 8 decisions, 2 candidate associations.
- E4b.1: 4 audit files, 4 decisions, 1 candidate association.
- Primary A3 experimental unit: candidate association, **N=3**.

## Frozen rule reproduced

- minimum frequency: 3
- consistency threshold: 0.80
- consistency convention: `round(dominant_count / total, 2)` before threshold comparison
- at least one `L3b_vlm` resolution required
- `None` node outcomes retained in the node counter and denominator

## Protected-code policy

Protected SAS production modules are not included in, imported by, or required to execute this public-safe analysis. The production extractor was used only as internal provenance during author verification; reviewer-facing reproduction is through released raw logs, released `sas_text.py`, documented rule, archived extractor outputs, and this standalone script.
