# Reproducing R210-AN-02

## Recompute the frozen analysis

This package contains the frozen acquisition, corrected replay input, executed runner, safe Session E reference, and canonical analyzer.

```bash
python3 analyze_r210_an02_frozen.py \
  --acquisition R2-10_controlled_replay_v3_20260823.tar.gz \
  --replay-package R2-10_replay_package_20260823_CORRECTED.zip \
  --session-e-reference session_e_r210_reference.json \
  --runner run_replay_v3.py \
  --out-prefix R210_AN_02_RECOMPUTED
```

The analyzer contains frozen assertions for provenance and headline numerical results. If the acquisition, runner, or key accounting changes, it fails rather than silently redefining R210-AN-02.

## Verify the safe Session E reference against raw E.zip

`E.zip` is intentionally not included because it contains protected SAS production source.

With the authorized internal raw archive available locally:

```bash
python3 extract_session_e_r210_reference.py \
  --session-e-zip E.zip \
  --out session_e_r210_reference_REGENERATED.json
```

Expected source E.zip SHA-256:

`9e2f1dbc0269a056efac7594e679c9b643a59b0a22a0916e8dde8c422f945f33`

The included frozen reference was regenerated during packaging and matched byte-for-byte.

## Denominator rule

The original Session E clarification rate **22/35 = 62.9%** is a full-population descriptive result. It must not be directly compared with replay abstention rates because the multimodal replay contains only the 13 original actionable, image-complete negation records.
