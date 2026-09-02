# R210-AN-02 — COMPLETE FROZEN PACKAGE

This package is the complete computational freeze for R2-10 / ROBOT-D-26-01090.

## Frozen conclusion

**L3b interface-level model portability, not semantic model invariance.**

## Canonical files

- `R2-10_Final_Controlled_Replay_Analysis_20260824_FROZEN.md` — authoritative narrative analysis.
- `analyze_r210_an02_frozen.py` — canonical standalone analyzer; supersedes `analyze_r210_v3_final.py` as report-generation source.
- `R210_AN_02_FROZEN_RESULTS.json` — machine-readable recomputation.
- `R210_AN_02_FROZEN_RESULTS.md` — concise computational verification.
- `session_e_r210_reference.json` — minimal public-safe Session E analysis reference.
- `extract_session_e_r210_reference.py` — regenerates that reference from an authorized local `E.zip`.
- `R2-10_controlled_replay_v3_20260823.tar.gz` — frozen replay acquisition.
- `R2-10_replay_package_20260823_CORRECTED.zip` — corrected replay input set.
- `run_replay_v3.py` — byte-identical executed runner.
- `R210_AN_02_FREEZE_MANIFEST.json` — provenance/governance.
- `REPRODUCE.md` — exact reproduction commands.
- `CHECKSUMS_SHA256.txt` — member checksums.

## Important boundary

The raw `E.zip` is **not included** because it contains protected SAS runtime source. The safe reference contains only selected analysis fields required for R2-10 and can be independently regenerated from the raw archive.

Any later change to the frozen arithmetic or interpretation requires a new identifier (`R210-AN-03` or later).
