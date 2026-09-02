# Source of this dataset

This dataset was built from the delivery archive as received, not from an
unpacked working copy. The archive is the provenance root:

```
file : livrare_sesiuneE_20_21_aug.zip
md5  : a51368db2b50fbb0083c0ffa36e41865
files: 1092
```

Building from the archive matters for two reasons. It fixes exactly which files
were delivered, so a file that later appeared in the working folder cannot be
promoted to evidence by accident. And it preserves the original modification
time of every file, which an unpack-and-copy loses.

## File timestamps

`PROVENANCE.tsv` carries a `source_mtime` column for every file, taken from the
archive rather than from the filesystem, so it survives copying, cloning and
checkout. Times are local (Europe/Bucharest, UTC+3 in August 2026) with the
2-second resolution of the archive format, and carry no timezone of their own.

Spot check against file content: `day1_20260820/logs/audit_20260820_115934.jsonl`
and the `timestamp_utc` of its first decision record differ by exactly 3 hours,
which is the expected offset.

### Files per month

| month | files |
|---|---|
| 2026-04 | 3 |
| 2026-08 | 1091 |

### The twelve oldest files

These bound how far back the delivered material reaches:

| source_mtime | dataset path |
|---|---|
| 2026-04-17T14:59:58 | `day1_20260820/code/executive_contract.py` |
| 2026-04-17T14:59:58 | `day2_20260821/code/executive_contract.py` |
| 2026-04-24T17:41:54 | `day1_20260820/config/memory_digest.json` |
| 2026-08-17T15:41:18 | `day1_20260820/config/semantic_objects_static_v2.geojson` |
| 2026-08-17T15:41:18 | `day2_20260821/config/semantic_objects_static_v2.geojson` |
| 2026-08-18T15:03:30 | `day1_20260820/code/sas_l3a.py` |
| 2026-08-18T15:03:30 | `day1_20260820/code/visual_confirmation_v2.py` |
| 2026-08-18T15:03:30 | `day2_20260821/code/sas_l3a.py` |
| 2026-08-18T15:03:30 | `day2_20260821/code/visual_confirmation_v2.py` |
| 2026-08-18T18:28:52 | `day1_20260820/config/route_graph_fiir.geojson` |
| 2026-08-18T18:28:52 | `day2_20260821/config/route_graph_fiir.geojson` |
| 2026-08-19T10:20:18 | `day1_20260820/code/vlm_navigator_node_v4_8_review.py` |

The most recent file is `_source/MD5SUMS_TOTAL.txt` at 2026-08-21T17:52:06.

## Files outside the delivered archive

These exist in the working folder but not in the archive. They are kept
under `_outside_delivery/` and are not evidence of what was run:

| dataset path | source path | md5 |
|---|---|---|
| `_outside_delivery/terminals_xplorer_b_c_ro.txt` | `Terminale Xplorer B-C.txt` | `bdea3c661588e6db29662b48e0aad49d` |
| `_outside_delivery/session_notes_day2_ro_superseded_draft.md` | `ziua2_20260821/NOTE_ziua2_20260821.md` | `4ce045a4f5355ff961455bb7f017e158` |

