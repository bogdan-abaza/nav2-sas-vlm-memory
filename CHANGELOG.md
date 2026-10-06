# Changelog

## ras-revision-rc1.2 — 2026-10-06

This release adds analyses and documentation over `ras-revision-rc1.1`. The Session E dataset under `data/` and the RC1.1 core and supporting analyses are unchanged and byte-identical to `ras-revision-rc1.1`.

### Added

| Path | Content |
|---|---|
| `analysis/session_e/rc1_2_reanalysis/` | E7 outcome classes with parse failures and clarification requests separated; fast-path incidence and error proportion; navigation measures conditional on dispatched navigation. Derived from the unchanged Session E records. |
| `analysis/session_e/semantic_comparison/` | Controlled offline comparison of the complete system, the hybrid with M3 Step 0 disabled, and direct VLM resolution, with resolver and instruction-to-decision latency; sealed inputs, run records, frozen results, the independent-reference rescoring and the parser-compatibility audit. |
| `analysis/session_e/m3_boundary/` | Labelled decision-boundary challenge for the M3 matcher (exact match, Jaccard 0.75/0.10, Jaccard 0.60 reference). |
| `analysis/session_e/guard_branch/` | Offline branch test of the forbidden-node guard with injected responses. |
| `analysis/session_e/e7_adjudication/` | Independent blind adjudication of the E7 acceptable-destination sets and its sensitivity analysis. |
| `analysis/session_e/apriltag_summary/` | Descriptive AprilTag discrepancy summary (n, mean, sample SD, range; per marker), recomputed from the published detections. |
| `analysis/session_e/camera_transaction/` | Live image-request transaction on Xplorer-B, measured separately from the offline comparison. |
| `tools/rerun_sealed.py` | Re-runs the sealed analyses from the public tree without modifying sealed files. |
| `docs/RC1_2_SCOPE_NOTES.md` | Qualifications of frozen RC1.1 wording. |
| `CHANGELOG.md` | This file. |

### Updated (documentation only)

| Path | Change |
|---|---|
| `README.md` | Release note, reading note and quick start; adaptive-memory definition and scope of the M3 comparison (§1); rc1.2 evidence rows (§2); E7 classes, navigation denominators and adjudication interpretation (§3); new component entries and rerun commands (§4–5); repository map (§8) and qualified preservation statement (§9). |
| `docs/REPRODUCIBILITY_NOTES.md` | New section for the rc1.2 analyses, including precise frozen-file locations and the camera transaction boundary; inherited sections unchanged. |

### Unchanged

`data/**`, `analysis/session_e/core/**`, `analysis/session_e/A1_cascade/**`, `analysis/session_e/A2_m3_sensitivity/**`, `analysis/session_e/A3_m3_promotion/**`, `analysis/session_e/r210_model_replay/**`, `analysis/figures/**`, `config/**`, `tools/build_dataset.py`, `tools/reproduce_digest.py`, `CITATION.cff`, `LICENSE`.
