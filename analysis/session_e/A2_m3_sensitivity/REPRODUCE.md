# REPRODUCE - A2 M3 sensitivity v1

Requirements: Python 3 standard library only. No network. No internal archive.

```bash
sha256sum -c A2_CHECKSUMS_SHA256.txt
python3 analyze_A2_m3_sensitivity.py --outdir ./regen
```

Expected stdout:

```json
{
  "reproduction_gate": "PASS",
  "active_records": 212,
  "nominal_matches": 39,
  "former_0.60_matches": 43,
  "grid_rows": 2511
}
```

These five files in `./regen` are byte-identical to the frozen copies:

```
A2_m3_record_replay.csv
A2_m3_sensitivity_grid.csv
A2_m3_sensitivity_results.json
A2_m3_threshold_keypoints.csv
A2_m3_margin_keypoints.csv
```

`A2_m3_sensitivity_report.md`, `README.md`, `A2_INPUT_PROVENANCE.md` and this file are
authored documents; the script does not produce them.

Optional cross-check against the canonical enriched table (needs the internal disk layout):

```bash
python3 -c "
import csv,collections,os
m=[x for x in csv.DictReader(open(os.environ['HOME']+'/mnt/Outputs/data/session_e/missions.csv'))
   if not x['experiment_id'].upper().startswith('E0') and x['digest_content_md5']]
acc=[x for x in m if x['resolution_step']=='0']
ru=[x for x in acc if x['m3_runner_up_score']]
print('population', len(m), 'accepts', len(acc))
print('scores', collections.Counter(x['m3_jaccard_score'] for x in acc))
print('min gap', min(float(x['m3_jaccard_score'])-float(x['m3_runner_up_score']) for x in ru))
print('negation_detected', sum(1 for x in m if x['escalation_reason']=='negation_detected'))"
```

Expected: population 212, accepts 39, all scores 1.0, min gap 0.8, negation_detected 39.
