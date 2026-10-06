#!/usr/bin/env python3
"""Re-run the sealed analyses of this release from the public tree, without modifying any sealed file.

The sealed scripts were frozen in the working layout in which they were sealed, and they verify the SHA-256 of their inputs
before running. This adapter therefore does not edit them and does not bypass any check. It builds a temporary sandbox that
reproduces the layout the scripts expect:
  <sandbox>/Review_14.05.2026/Outputs/PUBLIC_REPO_WORK/RC1  -> this repository (read only)
  <sandbox>/w/<component>                                   -> a copy of analysis/session_e/<component>/sealed
It then runs the sealed command with explicit output directories inside the sandbox, and compares the regenerated outputs
with the published ones.

One name-level step is needed for the semantic comparison. Its run directories are published with the redacted header
`RUN_HEADER.redacted.json`, and the analyzer reads `RUN_HEADER.json`, so the adapter copies the redacted header under that
name inside the sandbox. The analyzer's checks (completion, schedule, bundles, harness and input-seal hashes) all still run.
The original header is not published (it contains runtime environment data). Its SHA-256 is recorded in the redacted copy.

Usage, from the repository root:
  python3 tools/rerun_sealed.py m3_boundary | e7_adjudication | semantic_comparison | reference_sensitivity | all  [--keep]
Requires Python 3.8+ and the standard library only. No network access, no model, no robot."""
import os, sys, shutil, subprocess, tempfile, hashlib, json, csv, argparse, filecmp

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SE = os.path.join(REPO, 'analysis', 'session_e')
LEGACY = os.path.join('Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1')

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def sandbox(comp, tmp):
    os.makedirs(os.path.join(tmp, os.path.dirname(LEGACY)), exist_ok=True)
    link = os.path.join(tmp, LEGACY)
    try: os.symlink(REPO, link, target_is_directory=True)
    except (OSError, NotImplementedError): shutil.copytree(REPO, link, ignore=shutil.ignore_patterns('.git'))
    w = os.path.join(tmp, 'w', comp); shutil.copytree(os.path.join(SE, comp, 'sealed'), w)
    return w

def run(cmd, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable, '-B'] + cmd, cwd=cwd, env=env, capture_output=True, text=True)
    print(r.stdout[-1500:]); print(r.stderr[-1500:], file=sys.stderr)
    if r.returncode != 0: raise SystemExit('command failed (exit %d): %s' % (r.returncode, ' '.join(cmd)))

def same(a, b):
    ok = os.path.isfile(a) and os.path.isfile(b) and filecmp.cmp(a, b, shallow=False)
    print('  %-58s %s' % (os.path.relpath(b, REPO), 'identical' if ok else 'DIFFERS'))
    return ok

def m3_boundary(tmp):
    w = sandbox('m3_boundary', tmp)
    shutil.rmtree(os.path.join(w, 'results'))          # the sealed script writes results/ itself and never overwrites it
    run(['c5_run.py'], w)
    return all(same(os.path.join(w, 'results', f), os.path.join(SE, 'm3_boundary', 'sealed', 'results', f)) for f in ('per_item.csv', 'summary.csv'))

def e7_adjudication(tmp):
    w = sandbox('e7_adjudication', tmp); out = os.path.join(tmp, 'out_e7')
    run(['c3_analysis.py', '--responses', os.path.join(w, 'returned', 'dumitrescu', 'response_form.csv'), '--out', out], w)
    pub = os.path.join(SE, 'e7_adjudication', 'sealed', 'analysis')
    return all(same(os.path.join(out, f), os.path.join(pub, f)) for f in ('per_cell_dumitrescu.csv', 'C3_ADJUDICATION_RESULTS.json'))

def semantic_comparison(tmp):
    w = sandbox('semantic_comparison', tmp); pubc = os.path.join(SE, 'semantic_comparison')
    for c in 'SH':
        d = os.path.join(w, 'runs', c, 'run_primary'); shutil.copytree(os.path.join(pubc, 'runs', c, 'run_primary'), d)
        shutil.copyfile(os.path.join(d, 'RUN_HEADER.redacted.json'), os.path.join(d, 'RUN_HEADER.json'))
    out = os.path.join(tmp, 'out_sc')
    run(['sc_analyze.py', '--run-S', '../runs/S/run_primary', '--run-H', '../runs/H/run_primary', '--out', out], os.path.join(w, 'harness'))
    ok = True
    for dp, _, fs in os.walk(out):
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(dp, f), out)
            ok &= same(os.path.join(dp, f), os.path.join(pubc, 'results', rel))
    return ok

def reference_sensitivity(tmp):
    """Frozen post-run script sealed/post_run/sc_reference_sensitivity.py; it reads results/RESULT_FREEZE.json and runs/
    relative to its own location, so the sandbox places both next to the sealed copy."""
    w = sandbox('semantic_comparison', tmp); pubc = os.path.join(SE, 'semantic_comparison')
    for c in 'SH':
        shutil.copytree(os.path.join(pubc, 'runs', c, 'run_primary'), os.path.join(w, 'runs', c, 'run_primary'))
    os.makedirs(os.path.join(w, 'results')); shutil.copyfile(os.path.join(pubc, 'results', 'RESULT_FREEZE.json'), os.path.join(w, 'results', 'RESULT_FREEZE.json'))
    out = os.path.join(tmp, 'out_ref')
    run(['sc_reference_sensitivity.py', '--per-cell', os.path.join(SE, 'e7_adjudication', 'sealed', 'analysis', 'per_cell_dumitrescu.csv'), '--out', out],
        os.path.join(w, 'post_run'))
    return all(same(os.path.join(out, f), os.path.join(pubc, 'results_reference_sensitivity', f))
               for f in ('REFERENCE_SENSITIVITY.json', 'reference_sensitivity_per_item.csv'))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('component'); ap.add_argument('--keep', action='store_true'); a = ap.parse_args()
    comps = ['m3_boundary', 'e7_adjudication', 'semantic_comparison', 'reference_sensitivity'] if a.component == 'all' else [a.component]
    res = {}
    for c in comps:
        tmp = tempfile.mkdtemp(prefix='rerun_%s_' % c); print('==', c, '(sandbox %s)' % tmp)
        try: res[c] = globals()[c](tmp)
        finally:
            if not a.keep: shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({c: ('REPRODUCED' if v else 'DIFFERENCES') for c, v in res.items()}, indent=1))
    sys.exit(0 if all(res.values()) else 1)

if __name__ == '__main__':
    main()
