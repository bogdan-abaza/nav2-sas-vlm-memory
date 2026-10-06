"""Input seal for the A4 semantic comparison (protocol a4_semantic_comparison_20261005, s.11 step 6). Laptop only. Never overwrites.
Seals: protocol, harness/*.py, bundles/**, schedule/*, manifest_candidate/*, gates/*, tests/*.json, seal_inputs/DEPENDENCIES.sha256
(and, through it, every external file consumed from the v5 tree). Writes seal/SEAL.json and a read-only copy seal/sealed_set/.
  python3 -B sc_seal.py --operator "<name>" [--check-only]"""
import os, sys, json, glob, shutil, stat, hashlib, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); ART = os.path.abspath(os.path.join(ROOT, '..', '..'))
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
PATTERNS = ['protocol/*.md', 'harness/*.py', 'bundles/BUNDLES.sha256', 'bundles/S/*', 'bundles/H/*', 'schedule/*', 'manifest_candidate/*.csv',
            'manifest_candidate/*.md', 'manifest_candidate/*.txt', 'gates/*', 'tests/*.json', 'seal_inputs/DEPENDENCIES.sha256']
def sealed_files():
    fs = sorted({os.path.relpath(p, ROOT).replace(os.sep, '/') for pat in PATTERNS for p in glob.glob(os.path.join(ROOT, pat)) if os.path.isfile(p)})
    return fs
def deps():
    return [(l[:64], l[66:].strip()) for l in open(os.path.join(ROOT, 'seal_inputs', 'DEPENDENCIES.sha256')) if l.strip()]
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--operator', required=True); ap.add_argument('--check-only', action='store_true'); a = ap.parse_args()
    S = os.path.join(ROOT, 'seal'); SP = os.path.join(S, 'SEAL.json')
    if os.path.exists(SP): sys.exit('seal/SEAL.json exists: never overwritten')
    if glob.glob(os.path.join(ROOT, 'runs', '*', 'run_*')): sys.exit('measured run directories exist before the seal: refused')
    fs = sealed_files(); problems = []
    if not any(f.startswith('protocol/') for f in fs): problems.append('protocol missing')
    for t in ('tests/HARNESS_TESTS.json', 'tests/ANALYSIS_TESTS.json'):
        if t not in fs: problems.append(t + ' missing')
        else:
            d = json.load(open(os.path.join(ROOT, t)))
            if d.get('n_pass') != d.get('n'): problems.append(t + ' not all passed')
    ht = json.load(open(os.path.join(ROOT, 'tests', 'HARNESS_TESTS.json')))['harness_sha256'] if 'tests/HARNESS_TESTS.json' in fs else {}
    cur = {os.path.basename(f): sha(os.path.join(ROOT, f)) for f in fs if f.startswith('harness/')}
    if ht.get('sc_harness.py') != cur.get('sc_harness.py'): problems.append('harness tests ran on a different sc_harness.py')
    at = json.load(open(os.path.join(ROOT, 'tests', 'ANALYSIS_TESTS.json'))).get('analyze_sha256') if 'tests/ANALYSIS_TESTS.json' in fs else None
    if at != cur.get('sc_analyze.py'): problems.append('analysis tests ran on a different sc_analyze.py')
    bad_deps = [p for h, p in deps() if not os.path.isfile(os.path.join(ART, p)) or sha(os.path.join(ART, p)) != h]
    if bad_deps: problems.append('dependencies changed: %s' % bad_deps[:5])
    print('files to seal:', len(fs), '| external dependencies:', len(deps()), '| problems:', problems or 'none')
    if problems: sys.exit(1)
    if a.check_only: print('CHECK-ONLY: nothing written'); sys.exit(0)
    os.makedirs(os.path.join(S, 'sealed_set'))
    files = {}
    for f in fs:
        d = os.path.join(S, 'sealed_set', f); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(os.path.join(ROOT, f), d)
        files[f] = sha(d); os.chmod(d, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    seal = dict(protocol_id='a4_semantic_comparison_20261005', sealed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), operator=a.operator,
                files=files, external_dependencies={p: h for h, p in deps()}, n_files=len(files), n_external=len(deps()),
                note='Input seal. Qualification and run evidence are new append-only artifacts that reference this file by SHA256; they are not inserted into it.')
    json.dump(seal, open(SP, 'w'), indent=1)
    print('SEALED', seal['sealed_utc'], len(files), 'files +', len(deps()), 'external; SEAL.json sha256', sha(SP))
