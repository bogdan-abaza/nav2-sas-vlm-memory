# Experimental Data

This directory contains the complete dataset from the three-session validation 
described in Section 6 of the paper.

## Sessions

| Directory | Robot | Decisions | Content |
|-----------|-------|-----------|---------|
| session_a/ | Xplorer-C | 37 scenario | audits/ + csv_clean/ + csv_debug/ + mission_folders/ |
| session_b/ | Xplorer-B | 41 scenario | audits/ + csv/ + mission_folders/ |
| session_c/ | Both | 4 scenario | audits/ + mission_folders/ |
| memory/ | — | — | M1–M5 JSONL + compiled digest (MD5: 97241265) |

## Audit log format

Each `audits/*.jsonl` file contains structured entries with `_type: "decision"`. 
Key fields: `instruction`, `resolution_method`, `node_id`, `timing` (resolve_ms, 
vlm_ms, nav_total_s), `nav_outcome`, `confirmation`, `platform_id`.

## Pre-correction data

`session_a/csv_debug/` contains data from pre-v4.8 runs (before YOLO filtering 
fix). These are included for transparency and are not used in the paper's analysis.
