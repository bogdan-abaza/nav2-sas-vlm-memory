#!/usr/bin/env python3
"""Descriptive summary of the AprilTag external reference (Session E), recomputed from the published detections.

Inputs (published, read only; SHA-256 checked before use):
  data/session_e/external_reference/summary.json          images searched, detections, inclusion counts
  data/session_e/external_reference/detections.csv        one row per detection
  data/session_e/external_reference/pose_estimates.csv    one row per detection, with the inclusion decision and reason
Selection: the inclusion decision recorded in pose_estimates.csv, produced by the published apriltag_reference.py; the
exclusion criteria, in order of application, are tag not surveyed, PnP failure, mean tag side below 80 px, and tag with an
inconsistent survey.
Reported for the included detections: n, mean, sample SD (ddof = 1), min and max of dx (m), dy (m) and dyaw (deg); the same
per marker; counts per marker and per platform. No interval of the mean is computed: 10 of the 11 included detections
come from one marker, so the observations are not independent.
Usage, from the repository root:  python3 analysis/session_e/apriltag_summary/apriltag_summary.py --out <dir>
Standard library only."""
import os, sys, csv, json, hashlib, statistics, argparse
from collections import Counter, OrderedDict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
ER = os.path.join(REPO, 'data', 'session_e', 'external_reference')
PINNED = {'pose_estimates.csv': '04a1aed820e75f784149e17f22c6a282dd7582b445e05bf501cf50e3eecf47fb',
          'summary.json': 'd847b4f8547d831462eebe09cf52fb826d113ad0ebdaf5bf32fbe57a541a2a0a'}
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def desc(v):
    return OrderedDict(n=len(v), mean=round(statistics.mean(v), 4), sd=round(statistics.stdev(v), 4) if len(v) > 1 else None,
                       min=round(min(v), 4), max=round(max(v), 4))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    for f, h in PINNED.items():
        if sha(os.path.join(ER, f)) != h: sys.exit('input differs from the published file: ' + f)
    summ = json.load(open(os.path.join(ER, 'summary.json'), encoding='utf-8'))
    det = list(csv.DictReader(open(os.path.join(ER, 'detections.csv'), encoding='utf-8')))
    pe = list(csv.DictReader(open(os.path.join(ER, 'pose_estimates.csv'), encoding='utf-8')))
    inc = [r for r in pe if r['included'] == 'yes']
    if len(det) != summ['detections_total'] or len(pe) != summ['detections_total'] or len(inc) != summ['detections_included']:
        sys.exit('counts do not reconcile with summary.json')
    res = OrderedDict()
    res['funnel'] = OrderedDict(images_searched=summ['images_searched'], detections=len(pe), included=len(inc),
                                excluded_by_reason=dict(Counter(r['exclusion_reason'] for r in pe if r['included'] != 'yes')))
    res['included'] = OrderedDict((c, desc([float(r[k]) for r in inc])) for c, k in (('dx_m', 'dx_m'), ('dy_m', 'dy_m'), ('dyaw_deg', 'dyaw_deg')))
    res['per_marker'] = OrderedDict()
    for t in sorted({r['tag_id'] for r in inc}, key=int):
        sub = [r for r in inc if r['tag_id'] == t]
        res['per_marker']['tag_%s' % t] = OrderedDict((c, desc([float(r[c]) for r in sub])) for c in ('dx_m', 'dy_m', 'dyaw_deg'))
    res['counts'] = OrderedDict(by_marker=dict(Counter('tag_' + r['tag_id'] for r in inc)), by_platform=dict(Counter(r['platform_id'] for r in inc)))
    res['inputs_sha256'] = PINNED; res['script_sha256'] = sha(os.path.abspath(__file__))
    res['note'] = 'Descriptive only. Sample SD with ddof = 1. No interval of the mean is reported.'
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'apriltag_summary.json'), 'w', encoding='utf-8'), indent=1)
    L = ['# AprilTag external reference: descriptive summary', '',
         'Images searched %d; detections %d; included %d (excluded: %s).' % (summ['images_searched'], len(pe), len(inc),
            ', '.join('%s %d' % kv for kv in sorted(res['funnel']['excluded_by_reason'].items()))), '',
         '| Component | n | Mean | SD (ddof = 1) | Min | Max |', '|---|---:|---:|---:|---:|---:|']
    for c, d in res['included'].items():
        L.append('| %s | %d | %+.4f | %.4f | %+.4f | %+.4f |' % (c, d['n'], d['mean'], d['sd'], d['min'], d['max']))
    L += ['', 'Included detections by marker: %s; by platform: %s.' % (
        ', '.join('%s %d' % kv for kv in sorted(res['counts']['by_marker'].items())),
        ', '.join('%s %d' % kv for kv in sorted(res['counts']['by_platform'].items()))), '',
        'No interval of the mean is reported: 10 of the 11 included detections come from one marker.']
    open(os.path.join(a.out, 'APRILTAG_SUMMARY.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))

if __name__ == '__main__':
    main()
