"""Dependency manifest for the A4 semantic comparison: records every file OUTSIDE 13_semantic_comparison/ that the execution code
actually opens (traced builtins.open / io.open during import of a4_bundle, key loading, a full dry pass of S and H, and the
qualification payload construction). Writes seal_inputs/DEPENDENCIES.sha256 (sha256 + path relative to the ROBOT-D-26-01090 root).
No model calls.  python3 -B sc_deps.py"""
import os, sys, io, builtins, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); ART = os.path.abspath(os.path.join(ROOT, '..', '..'))
seen = set(); _open = builtins.open
def tracing_open(file, *a, **k):
    try:
        p = os.path.abspath(os.fspath(file))
        if os.path.isfile(p): seen.add(p)
    except TypeError: pass
    return _open(file, *a, **k)
builtins.open = tracing_open; io.open = tracing_open
sys.path.insert(0, HERE)
_argv = list(sys.argv); sys.argv = [sys.argv[0]]
import sc_harness as H
sys.argv = _argv
keys = H.load_keys()
for cond in ('S', 'H'):
    rows, _ = H.load_schedule(cond)
    for r in rows: H.observe(H.bundle(cond, r['item_id']), r['arm'], int(r['seed']), keys, 'dry')
H.qualification_payload()
builtins.open = _open; io.open = _open
for m in list(sys.modules.values()):                       # imported modules are read by the import system, not open(): add their files
    f = getattr(m, '__file__', None)
    if isinstance(f, str) and os.path.isfile(f): seen.add(os.path.abspath(f))
ext = sorted(p for p in seen if not p.startswith(ROOT + os.sep) and p.startswith(ART + os.sep))
out = os.path.join(ROOT, 'seal_inputs'); os.makedirs(out, exist_ok=True)
with open(os.path.join(out, 'DEPENDENCIES.sha256'), 'w') as f:
    for p in ext: f.write('%s  %s\n' % (hashlib.sha256(_open(p, 'rb').read()).hexdigest(), os.path.relpath(p, ART).replace(os.sep, '/')))
outside = sorted(p for p in seen if not p.startswith(ART + os.sep) and '/usr/lib/python' not in p and 'site-packages' not in p and 'dist-packages' not in p)
print('external dependencies under ROBOT-D-26-01090:', len(ext), '| other files read outside the tree (system):', len(outside))
print(open(os.path.join(out, 'DEPENDENCIES.sha256')).read().count('\n'), 'lines written to seal_inputs/DEPENDENCIES.sha256')
