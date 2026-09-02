# Experimental Data

This directory contains the public experimental evidence for the SAS study:
development-stage Sessions A–C and the frozen v4.8-review Session E confirmatory physical campaign.
The two evidence streams have different roles and experimental units and must not be
interpreted as one pooled validation dataset.

## Development-stage Sessions A–C

| Directory | Robot | Decisions | Content |
|-----------|-------|-----------|---------|
| session_a/ | Xplorer-C | 37 scenario | audits/ + csv_clean/ + csv_debug/ + mission_folders/ |
| session_b/ | Xplorer-B | 41 scenario | audits/ + csv/ + mission_folders/ |
| session_c/ | Both | 4 scenario | audits/ + mission_folders/ |
| memory/ | — | — | M1–M5 JSONL + compiled digest (MD5: 97241265) |

The 37 + 41 + 4 = 82 decisions above are the scenario-classified subset of the 165 logged
decisions; the machine-generated inclusion funnel is `../docs/ac_inclusion_funnel.csv` and
the per-start memory-digest ledger is `../docs/ac_startup_digest_map.csv`. Session E lives
in `session_e/` with its own documentation.

## Audit log format

Each `audits/*.jsonl` file contains structured entries with `_type: "decision"`. 
Key fields: `instruction`, `resolution_method`, `node_id`, `timing` (resolve_ms, 
vlm_ms, nav_total_s), `nav_outcome`, `confirmation`, `platform_id`.

## Pre-correction data

`session_a/csv_debug/` contains data from pre-v4.8 runs (before YOLO filtering 
fix). These are auxiliary, are excluded from the public 165-decision audit population (which is defined over `audits/*.jsonl` only), and are not used in the paper's analysis.
