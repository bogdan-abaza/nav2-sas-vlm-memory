# REPRODUCE - A3 M3 promotion-threshold sensitivity v1

Requirements: Python 3 standard library only. No network. No protected SAS module.

You need two released archives, placed anywhere:

```
E.zip             sha256 9e2f1dbc0269a056efac7594e679c9b643a59b0a22a0916e8dde8c422f945f33
session_e_v3.zip  sha256 e8d863f1ea748152be67b42788cd15cf8bef782c47c7ae29f18652205948931f
```

```bash
sha256sum -c A3_CHECKSUMS_SHA256.txt
python3 analyze_A3_m3_promotion_sensitivity.py \
  --session-e-zip <path>/E.zip \
  --canonical-analysis-zip <path>/session_e_v3.zip \
  --out-dir ./regen
```

Expected stdout:

```json
{
  "analysis_id": "A3_m3_promotion_sensitivity_v1",
  "status": "FROZEN 2026-08-25",
  "reproduction_gate": "PASS",
  "canonical_v3_crosscheck": "PASS",
  "candidate_count": 3,
  "nominal_promoted": ["wet_gloves"],
  "detail_grid_rows": 1818,
  "summary_grid_rows": 606
}
```

Everything in `./regen` is byte-identical to the frozen copies, except
`A3_CHECKSUMS_SHA256.txt`: the script writes a checksum file covering only the
artifacts it produces plus `README.md`, `sas_text.py` and itself, while the frozen
`A3_CHECKSUMS_SHA256.txt` also covers `A3_FREEZE_MANIFEST_20260825.txt` and this file.
Do not run the script with `--out-dir .` over the frozen package unless you intend to
rewrite that checksum file.

`README.md`, `REPRODUCE.md` and `A3_FREEZE_MANIFEST_20260825.txt` are authored
documents. `A3_m3_promotion_sensitivity_report.md` and `A3_INPUT_PROVENANCE.md`
ARE script output - the script writes them from the same computation, so their status
line follows the `STATUS` constant in the script.

Optional independent cross-check, straight from the canonical enriched table, without
this script (needs the internal disk layout):

```bash
python3 -c "
import csv,collections,os
m=[x for x in csv.DictReader(open(os.environ['HOME']+'/mnt/Outputs/data/session_e/missions.csv'))
   if x['experiment_phase'] in ('E4.1','E4b.1')]
g=collections.defaultdict(list)
for x in m: g[x['instruction_text'][:40]].append(x)
for ins,rows in g.items():
    nodes=[r['node_id'] or None for r in rows]
    dom,dc=collections.Counter(nodes).most_common(1)[0]
    l3b=sum(1 for r in rows if r['resolution_method']=='L3b_vlm')
    ok = len(rows)>=3 and round(dc/len(rows),2)>=0.80 and l3b>=1
    print(len(rows), round(dc/len(rows),2), 'PROMOTE' if ok else 'REJECT', ins)"
```

Expected: 12 records in three groups - 4/0.5 REJECT (deliveries), 4/0.75 REJECT
(quiet corner), 4/1.0 PROMOTE (wet gloves).
