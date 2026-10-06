"""Acceptance tests for sc_harness.py (protocol a4_semantic_comparison_20261005, s.11 checks 3-5), against a fake local inference server. No real model.
Run from harness/ on a COPY of the tree (writes runs/_tests/ under the copy):  python3 -B sc_tests.py
Checks: key scoring happens after the decision timer; stage intervals nonnegative and inside the decision interval; resolver null in C;
outcome classes (target, explicit -1, guard block, node not in graph, malformed reply); runtime violations (runner replaced, cached
prompt tokens, model left loaded before preload, system service busy); infrastructure failure (HTTP 500); schedule Latin balance."""
import os, sys, json, time, tempfile, subprocess, collections
HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = r'''#!/usr/bin/env python3
import os, json, subprocess, sys, signal, time
from http.server import BaseHTTPRequestHandler, HTTPServer
host, port = os.environ['OLLAMA_HOST'].split(':'); st = dict(loaded=False, runner=None)
MODE = open(os.environ['FAKE_MODE_FILE']).read().strip()
REPLY = {'ok': '{"node_id": 9}', 'minus1': '{"node_id": -1}', 'forbidden': '{"node_id": 0}', 'notingraph': '{"node_id": 999}',
         'malformed': 'I think node nine', 'boolnode': '{"node_id": true}'}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, d, code=200): b = json.dumps(d).encode(); self.send_response(code); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == '/api/version': self._send({'version': '0.30.2'})
        elif self.path == '/api/ps':
            loaded = st['loaded'] or MODE == 'preloaded'
            self._send({'models': [{'name': 'qwen3.5:4b', 'digest': '0c8faadc50c205b83c634430c1dae6d1a4896c9b818cb8f290aa34d535265018', 'size': 4, 'size_vram': 4, 'context_length': 8192 if MODE == 'ctx' else 16384}] if loaded else []})
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if not st['loaded']:
            st['runner'] = subprocess.Popen(['sh', '-c', 'trap "" TERM; sleep 1000'] if MODE == 'stubborn' else ['sleep', '1000']); st['loaded'] = True
        if self.path == '/api/generate': return self._send({'done': True})
        if MODE == 'http500': return self._send({'error': 'x'}, 500)
        if MODE == 'notobject': return self._send([1, 2, 3])
        if MODE == 'badmsg': return self._send({'message': 'just a string', 'done_reason': 'stop'})
        if MODE == 'replace': st['runner'].kill(); st['runner'] = subprocess.Popen(['sleep', '1001'])
        time.sleep(0.01)
        env = {'message': {'content': REPLY.get(MODE, REPLY['ok'])}, 'total_duration': 10000000, 'load_duration': 1, 'prompt_eval_count': 2734,
               'prompt_eval_duration': 9000000, 'eval_count': 5, 'eval_duration': 1000, 'done_reason': 'stop'}
        if MODE == 'cached': env['prompt_eval_cached_count'] = 2700
        self._send(env)
def bye(*a):
    if st['runner'] and MODE != 'stubborn': st['runner'].kill()
    sys.exit(0)
signal.signal(signal.SIGTERM, bye)
HTTPServer((host, int(port)), H).serve_forever()
'''
tmp = tempfile.mkdtemp(prefix='sc_tests_'); fake = os.path.join(tmp, 'fake_ollama.py'); open(fake, 'w').write(FAKE); os.chmod(fake, 0o755)
modef = os.path.join(tmp, 'mode'); open(modef, 'w').write('ok')
os.environ.update(SC_OLLAMA_BIN=fake, SC_SYSTEM_URL='none', SC_PORT='11639', SC_MODELS='/nonexistent', FAKE_MODE_FILE=modef, SC_NO_NVIDIA='1', SC_ALLOW_UNSEALED='1', SC_THERMAL_FAKE='1')
sys.path.insert(0, HERE)
_argv = list(sys.argv); sys.argv = [sys.argv[0]]
import sc_harness as H
import sc_schedule as SCH
sys.argv = _argv
results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond), str(detail)[:200])); print('%s %s %s' % ('PASS' if cond else 'FAIL', name, '' if cond else detail))
def mode(m): open(modef, 'w').write(m)
keys = H.load_keys(); srv = H.Server(os.path.join(tmp, 'logs'))
B = lambda cond, iid: H.bundle(cond, iid)
def obs(cond, iid, arm, **kw):
    hook_t = {}
    rec = H.observe(B(cond, iid), arm, 12345, keys, 'run', srv, key_hook=lambda: hook_t.setdefault('t', time.perf_counter_ns()), **kw)
    return rec, hook_t.get('t')
STAGES = ['resolver_ns', 'image_ns', 'prompt_ns', 'serialize_ns', 'api_ns', 'decode_ns', 'parse_ns', 'guard_validation_ns']
def stages_ok(r):
    parts = [r[k] for k in STAGES if r.get(k) is not None]
    return all(p >= 0 for p in parts) and sum(parts) <= r['decision_ns']
# ---- 1. timer boundaries and scoring after the timer, all three arms, L3a and L3b paths
mode('ok')
for cond, iid in [('S', 'M3-1'), ('S', 'E7-L-P1'), ('S', 'E2-X02')]:
    for arm in 'ABC':
        try: r, th = obs(cond, iid, arm)
        except Exception as e: check('observe %s %s %s' % (cond, iid, arm), False, repr(e)); continue
        check('scoring after decision timer %s/%s' % (iid, arm), th is not None and th > r['_t_decision_end_ns'])
        check('stages nonneg and inside decision %s/%s' % (iid, arm), stages_ok(r), {k: r.get(k) for k in STAGES + ['decision_ns']})
        check('resolver null iff C %s/%s' % (iid, arm), (r['resolver_ns'] is None) == (arm == 'C'))
        check('prep evidence %s/%s' % (iid, arm), r['runtime_prep']['loaded_before_preload'] == [] and r['runtime_prep']['runners'] and all(s_ is not None for _, s_ in r['runtime_prep']['runners']))
# ---- 2. outcome classes (decision before key)
for m, iid, exp_dec, exp_sub in [('minus1', 'E7-L-P1', 'clarification', 'vlm_explicit_-1'),
                                ('forbidden', 'E2-N01', 'clarification', 'guard_blocked'),
                                ('notingraph', 'E7-L-P1', 'model_or_parser_failure', 'node_not_in_graph'),
                                ('malformed', 'E7-L-P1', 'model_or_parser_failure', ''),
                                ('boolnode', 'E7-L-P1', 'model_or_parser_failure', '')]:
    mode(m)
    try:
        r, _ = obs('S', iid, 'C')
        check('outcome %s -> %s' % (m, exp_dec), r['decision'] == exp_dec and r['outcome_sub'].startswith(exp_sub) and r['outcome'] == exp_dec, (r['decision'], r['outcome_sub']))
    except Exception as e: check('outcome %s' % m, False, repr(e))
mode('ok'); r, _ = obs('S', 'E7-G-3', 'C')
check('target where clarification required -> incorrect_executable', r['decision'] == 'target' and r['outcome'] == 'incorrect_executable' and r['correct'] is False, (r['decision'], r['outcome']))
r, _ = obs('S', 'E7-S-P3', 'C')
check('target in acceptable set -> acceptable', r['outcome'] == 'acceptable' and r['correct'] is True, r['outcome'])
mode('minus1'); r, _ = obs('S', 'E2-N01', 'C')
check('clarification where required -> correct', r['outcome'] == 'clarification' and r['correct'] is True, r['outcome'])
mode('malformed'); r, _ = obs('S', 'E2-N01', 'C')
check('parser failure never a correct clarification', r['outcome'] == 'model_or_parser_failure' and r['correct'] is False, r['outcome'])
# ---- 3. runtime violations and infrastructure failure
for m, exc, what in [('replace', H.RuntimeViolation, 'runner_replaced'), ('cached', H.RuntimeViolation, 'cached_prompt_tokens'),
                     ('preloaded', H.RuntimeViolation, 'model_loaded_before_preload'), ('http500', H.InfrastructureFailure, 'http_status_500'),
                     ('notobject', H.InfrastructureFailure, 'api_envelope_not_object'), ('badmsg', H.InfrastructureFailure, 'api_envelope_malformed_message'),
                     ('ctx', H.RuntimeViolation, 'preload_state_unexpected')]:
    mode(m)
    try: obs('S', 'E7-L-P1', 'C'); check('violation %s raised' % m, False, 'no exception')
    except exc as e: check('violation %s raised' % m, getattr(e, 'what', getattr(e, 'kind', '')) == what, getattr(e, 'what', getattr(e, 'kind', '')))
    except Exception as e: check('violation %s raised' % m, False, repr(e))
mode('ok'); srv.stop()
# ---- 3b. leftover runner after stop (PID + start time) is detected; continuity gap; suspension drift; seal mismatch
mode('stubborn')
try:
    obs('S', 'E7-L-P1', 'C'); st_ = srv.stop()
    check('leftover runner detected at stop', bool(st_ and st_['leftover']), st_)
    for p_, s_ in (st_ or {}).get('leftover', []):
        try: os.kill(int(p_), 9)
        except Exception: pass
except Exception as e: check('leftover runner detected at stop', False, repr(e))
mode('ok')
try:
    H.observe(B('S', 'E7-L-P1'), 'C', 1, keys, 'run', srv, prep_gate=lambda: (_ for _ in ()).throw(H.RuntimeViolation('continuity_gap', 99)))
    check('continuity gate stops before preparation', False, 'no exception')
except H.RuntimeViolation as e: check('continuity gate stops before preparation', e.what == 'continuity_gap', e.what)
_boot = H.boot_ns; _n = [0]
def jumpy():
    _n[0] += 1; return _boot() + (5_000_000_000 if _n[0] > 1 else 0)
H.boot_ns = jumpy
try: H.observe(B('S', 'E7-L-P1'), 'C', 1, keys, 'run', srv); check('suspension drift detected', False, 'no exception')
except H.RuntimeViolation as e: check('suspension drift detected', e.what == 'system_suspended_during_observation', e.what)
H.boot_ns = _boot; srv.stop()
SD = os.path.join(H.ROOT, 'seal'); assert not os.path.exists(SD), 'tests must run on a tree copy without a seal'
os.makedirs(SD); json.dump(dict(files={'harness/sc_harness.py': '0' * 64}, external_dependencies={}), open(os.path.join(SD, 'SEAL.json'), 'w'))
try: H.verify_seal(); check('seal mismatch detected', False, 'no exception')
except H.RuntimeViolation as e: check('seal mismatch detected', e.what == 'seal_mismatch', e.what)
os.remove(os.path.join(SD, 'SEAL.json')); os.rmdir(SD)
# ---- 3c. thermal logger writes samples
th = H.Thermal(os.path.join(tmp, 'thermal.csv'))
try: th.start(); time.sleep(0.3); tr = th.stop(); check('thermal logger samples', tr['samples'] >= 1, tr)
except Exception as e: check('thermal logger samples', False, repr(e))
# ---- 4. schedule balance and pairing
for cond in ('S', 'H'):
    rows = SCH.schedule(cond); items = sorted({r['item_id'] for r in rows})
    pos = collections.Counter((r['item_id'], r['arm'], r['position']) for r in rows)
    check('Latin positions %s' % cond, all(pos[(i, a, p)] == 1 for i in items for a in 'ABC' for p in range(3)))
    check('order counts %s' % cond, len(set(collections.Counter(r['order'] for r in rows if r['position'] == 0).values())) == 1)
    check('seed paired across arms %s' % cond, all(len({r['seed'] for r in rows if r['item_id'] == i and r['seed_base'] == b}) == 1 for i in items for b in (1, 2, 3)))
    check('blocks adjacent %s' % cond, all(rows[k]['block'] == rows[k + 1]['block'] == rows[k + 2]['block'] for k in range(0, len(rows), 3)))
n_fail = sum(1 for _, ok, _ in results if not ok)
out = dict(utc=H.utc(), harness_sha256=H.harness_hashes(), n=len(results), n_pass=len(results) - n_fail, results=results)
d = os.path.join(H.ROOT, 'tests'); os.makedirs(d, exist_ok=True); json.dump(out, open(os.path.join(d, 'HARNESS_TESTS.json'), 'w'), indent=1)
print('HARNESS TESTS %d/%d' % (len(results) - n_fail, len(results)))
sys.exit(1 if n_fail else 0)
