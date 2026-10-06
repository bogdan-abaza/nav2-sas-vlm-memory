#!/usr/bin/env python3
"""c3_seal.py -- seals the C3 blind-adjudication set before dispatch. Refuses to reseal.
Checks: BUILD_RECORD file hashes still match the packet; analysis self-test PASS on the current
analysis script; then writes internal/C3_SEAL.json (hashes of packet zip, code map, build and
analysis scripts, self-test results, evaluator instructions) and marks it read-only."""
import hashlib, json, os, stat, subprocess, sys, datetime
H = os.path.dirname(os.path.abspath(__file__)); I = os.path.join(H, 'internal')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
S = os.path.join(I, 'C3_SEAL.json')
if os.path.exists(S): sys.exit('C3 SEAL REFUSED: already sealed')
rec = json.load(open(os.path.join(I, 'BUILD_RECORD.json')))
pk = os.path.join(H, 'packets_blind', rec['packet'])
for n, h in rec['packet_files'].items():
    if sha(os.path.join(pk, n)) != h: sys.exit('C3 SEAL REFUSED: packet file changed: ' + n)
if sha(os.path.join(H, 'packets_blind', rec['packet'] + '.zip')) != rec['packet_zip_sha256']: sys.exit('C3 SEAL REFUSED: zip changed')
if sha(os.path.join(H, 'c3_build_packet.py')) != rec['script_sha256']: sys.exit('C3 SEAL REFUSED: build script changed since the packet was built')
cp = subprocess.run([sys.executable, '-B', os.path.join(H, 'c3_analysis.py'), '--self-test'], capture_output=True, text=True)
st = json.load(open(os.path.join(I, 'SELF_TEST_RESULTS.json')))
if cp.returncode or st['n'] != st['n_pass'] or st['analysis_sha256'] != sha(os.path.join(H, 'c3_analysis.py')):
    sys.exit('C3 SEAL REFUSED: analysis self-test')
seal = dict(sealed_utc=datetime.datetime.utcnow().isoformat() + 'Z', status='sealed before dispatch; post-hoc sensitivity analysis',
            packet_zip_sha256=rec['packet_zip_sha256'], code_map_sha256=rec['code_map_sha256'],
            build_script_sha256=rec['script_sha256'], analysis_sha256=st['analysis_sha256'],
            self_test='%d/%d' % (st['n_pass'], st['n']), build_record_sha256=sha(os.path.join(I, 'BUILD_RECORD.json')),
            analysis_plan_sha256=sha(os.path.join(H, 'ANALYSIS_PLAN.md')))
json.dump(seal, open(S, 'w'), indent=1)
for p in (S, os.path.join(I, 'CODE_MAP.csv'), os.path.join(I, 'BUILD_RECORD.json')):
    os.chmod(p, stat.S_IREAD)
print('C3 SEALED:', seal['packet_zip_sha256'][:16])
