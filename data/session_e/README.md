# Session E — raw dataset

Two experimental days, 20 and 21 August 2026, on the FIIR indoor test floor, with the
two-platform SAS stack (`xplorer-b`, `xplorer-c`). This directory is the *raw evidence*
for the Session E experiments (blocks E0–E7, E4b) plus generated English indexes.

## What is and is not modified

Every file carried over from the delivery is **byte-identical** to the original. Only
directory and file *names* were translated to English. `PROVENANCE.tsv` maps every file
in this dataset back to its original path and records its MD5, so any rename is
reversible and any file is verifiable.

Romanian text inside the audit logs, the session notes and the sealed instruction set is
**primary evidence and was not translated**. Translating it would destroy the record of
what was actually said to the robot. English access to the same content is provided by
the generated indexes below, which add columns rather than replacing text.

## Generated indexes (English, machine-readable)

| File | Unit | Content |
|---|---|---|
| `missions.csv` | one row per archived decision cycle | flattened decision record: instruction, resolution path, target node, navigation outcome, poses, AMCL state, timings, visual confirmation, memory state, and image references |
| `sessions.csv` | one row per audit session | run configuration: platform, model, digest, thresholds, graph hashes, and code commit |
| `PROVENANCE.tsv` | one row per delivered-source file | dataset path, source path, size, MD5, and provenance flags |
| `PROVENANCE_PUBLIC.tsv` | post-delivery public additions | provenance for public-reference material added after the original delivery |
| `CHECKSUMS_PUBLIC.md5` | one entry per covered public file | MD5 manifest for the published Session E release |

`external_reference/` contains the published AprilTag external-localization reference
artifacts and its own checksum manifest. Post-hoc analyses are published separately under
`analysis/session_e/`. The canonical machine-readable Session E core results are in
`analysis/session_e/core/results_E.json`; A1, A2, A3, and the controlled model-substitution
replay retain their own supporting artifacts under `analysis/session_e/`.

The CSV indexes were generated from the JSONL audit evidence during controlled dataset
construction; they contain no hand-entered experimental values. The public release is
verified directly through `CHECKSUMS_PUBLIC.md5`. Reconstructing the dataset from the
original delivery is a separate provenance operation and requires material outside the
public release.

## Counting convention — read before quoting any n

An audit record with `resolution_method = "escalated"` is an **unresolved escalation
record**: an L3b-path attempt that did not return parseable JSON. It remains part of the
archived decision-cycle population but is not a resolved-or-blocked record.

`missions.csv` preserves all archived decision cycles, including unresolved escalation
records. Analyses must therefore use the population explicitly defined for the
corresponding result rather than treating audit sessions, decision-bearing runs, decision
cycles, resolved-or-blocked records, and unresolved escalation records as interchangeable
units.

The public population definitions and denominator conventions are documented in
`data/SESSIONS.md` and `docs/session_e_l3b_population_dictionary.md`.

## Verifying this dataset

The integrity of the published Session E dataset can be checked from the repository alone:

```bash
cd data/session_e
md5sum -c CHECKSUMS_PUBLIC.md5
```

Dataset reconstruction is a separate provenance operation and requires the original
non-public delivery. If that source is available under the journal's confidential review
process, the published builder can be invoked from the repository root as:

```bash
python3 tools/build_dataset.py --source <delivery> --output <dataset> --verify-only
```

The second command is not required to verify the integrity of the public release.

## Layout

```text
notes/                         session notes recorded during the runs (Romanian)

day1_20260820/
  config/                      route graph, static semantic objects, memory state
  dynamic_graph_archive/       per-run dynamic-graph snapshots
  logs/                        audit JSONL files and referenced mission images
  CHECKSUMS_source.md5         delivery-time checksum record
  git_head.txt
  git_status.txt
  mission_index_ro.txt
  session_notes_day1_ro.md

day2_20260821/
  config/
  dynamic_graph_archive/
  logs/
  evidence/                    raw VLM payload/response captures
  memory/                      digests and per-block extractor outputs
  session/                     run sheets, sealed E7 set, and session records
  CHECKSUMS_source.md5
  E7_seal.txt
  git_head.txt
  git_status.txt
  mission_index_ro.txt

external_reference/            published external-localization reference artifacts
public_code/                   public SAS source boundary (`sas_text.py`) + provenance

missions.csv
sessions.csv
PROVENANCE.tsv
PROVENANCE_PUBLIC.tsv
CHECKSUMS_PUBLIC.md5
SOURCE.md
KNOWN_DISCREPANCIES.md
README.md
```

The delivery-time `code/` directories and the `_source/` staging area are intentionally
outside the public release. The publication boundary exposes only `public_code/sas_text.py`
as production SAS source, together with its provenance metadata. Raw evidence and the
published day-specific configuration material remain preserved under the paths above.
