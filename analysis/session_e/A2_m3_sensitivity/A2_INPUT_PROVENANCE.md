# A2 input provenance

All inputs in this frozen package are public-safe.

| Input | SHA-256 | Role |
|---|---|---|
| `inputs/missions.csv` | `f19f380877522c6c2db64a8c8d573226b83b713602e51fce3f1847ba67004bf7` | Session E raw decision table, 58 columns, as delivered in `E.zip` |
| `inputs/sessions.csv` | `e997c2a097ba2f2cbe45e594715d160556d5a480c9ebdbc48705e804e21683f2` | frozen threshold/margin and version provenance |
| `inputs/sas_text.py` | `aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1` | approved public text normalization/tokenization/negation/Jaccard utility |
| `inputs/memory_digest_standard.json` | `1fe64ed09a96343bac5abd0cae476545bd0100dd496dc25122b1ca4a2cd7c3ab` | six-association digest; content MD5 `0fd61f9e82e8fe6991f0311014384e0c` |
| `inputs/memory_digest_E4b.json` | `ee981d9c6fb6b8c8e281d8bb6abc70b537bbb43d324c01b741b8dad694dcdc30` | one-association E4b digest; content MD5 `5b3f14bc71a1896da5b29a4e655479fa` |

Source archive used to assemble these inputs: Session E delivery `E.zip`,
SHA-256 `9e2f1dbc0269a056efac7594e679c9b643a59b0a22a0916e8dde8c422f945f33`.
A2 execution does not require the full internal archive.

## Which `missions.csv` this is, and why

Two variants exist and they are NOT interchangeable by file name:

| Variant | SHA-256 | Columns | Status |
|---|---|---:|---|
| raw, `E.zip` member `data/session_e/missions.csv` | `f19f3808...04bf7` | 58 | **the file bundled here** |
| canonical enriched, `Outputs\data\session_e\missions.csv` | `7759648c...d970a` | 67 | canonical Session E source of truth (author declaration, 2026-08-25) |

The enriched file is a strict superset: same 226 rows, all 58 common columns identical
in value and order, 9 added derived columns (`escalation_reason`, `negation_intent`,
`negation_markers`, `m3_jaccard_score`, `m3_runner_up_score`, `m3_matched_example`,
`vlm_eval_count`, `vlm_raw_reason`, `vlm_error`).

A2 deliberately replays from the RAW variant. Those 9 added columns are themselves
derived matcher outputs: replaying from them would make the reproduction gate circular.
Using the raw variant is what makes A2 reproducible from released artifacts alone.

Rule adopted for the whole revision dossier: always name the container, never just the
file name.

## Historical metadata

The `navigator_version` field inside the standard April digest is digest-level historical
metadata and is NOT Session E runtime provenance. Runtime threshold and version
provenance come from `sessions.csv`.
