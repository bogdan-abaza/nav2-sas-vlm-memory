"""Seal the C5 set (C5_CONSTRUCTION_RULE.md §6). Never overwrites. Usage: python3 -B c5_seal.py --operator NAME"""
import json, os, sys, hashlib, time, argparse, glob
HERE = os.path.dirname(os.path.abspath(__file__))
A2 = os.path.join(HERE, '..', '..', 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1', 'analysis', 'session_e', 'A2_m3_sensitivity')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument('--operator', required=True); a = ap.parse_args()
SP = os.path.join(HERE, 'C5_SEAL.json')
if os.path.exists(SP): sys.exit('C5_SEAL.json exists: never overwritten')
if os.path.exists(os.path.join(HERE, 'results')): sys.exit('results/ exists before seal: refused')
for f, s in [('C5_CONSTRUCTION_RULE.md', 'C5_CONSTRUCTION_RULE.sha256'), ('C5_AMENDMENT_01_20261005.md', 'C5_AMENDMENT_01_20261005.sha256'),
             ('C5_AMENDMENT_02_20261005.md', 'C5_AMENDMENT_02_20261005.sha256'), ('challenge_index_C.json', 'challenge_index_C.sha256')] + \
            [(os.path.relpath(b, HERE), os.path.relpath(b.replace('.csv', '.sha256'), HERE)) for b in sorted(glob.glob(os.path.join(HERE, 'authoring', 'batch_*.csv')))]:
    assert sha(os.path.join(HERE, f)) == open(os.path.join(HERE, s)).read().split()[0], 'hash file mismatch: ' + f
FILES = ['C5_CONSTRUCTION_RULE.md', 'C5_AMENDMENT_01_20261005.md', 'C5_AMENDMENT_02_20261005.md', 'challenge_index_C.json',
         'c5_build.py', 'candidates_log.csv', 'items.csv', 'c5_run.py', 'c5_seal.py',
         'review/C5_LABEL_REVIEW_SHEET.csv', 'review/C5_LABEL_REVIEW_SHEET.md'] + \
        sorted(os.path.relpath(b, HERE).replace(os.sep, '/') for b in glob.glob(os.path.join(HERE, 'authoring', 'batch_*.csv')))
RC1 = ['inputs/sas_text.py', 'inputs/memory_digest_standard.json', 'analyze_A2_m3_sensitivity.py']
seal = dict(sealed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), operator=a.operator, n_items=47,
            files={f: sha(os.path.join(HERE, f)) for f in FILES}, rc1_inputs={f: sha(os.path.join(A2, f)) for f in RC1},
            note='Diagnostic set constructed with access to similarity scores; labels assigned before each candidate was scored and reviewed on sheets without scores or decisions. Seal precedes any EXACT/JACCARD run.')
json.dump(seal, open(SP, 'w'), indent=1)
print('C5 SEALED', seal['sealed_utc'], len(FILES), 'files; C5_SEAL.json sha256', sha(SP))
