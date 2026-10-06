"""A4 controlled semantic comparison harness (protocol a4_semantic_comparison_20261005).
Arms: A = Step 0 (M3) + Steps 1-6 + VLM on escalation; B = Step 0 disabled; C = VLM-direct (Steps 0-6 bypassed).
Common to all arms (frozen in the bundle): M1/M2 prefix, negation envelope, L3b prompt, parser, forbidden-node guard, structural policy.
Modes:
  dry     : no server, no model. Routing, prompt integrity, payload identity across arms, schedule coverage.
  qualify : diagnostic twelve-call qualification only (writes runtime/). Not used for measurement.
  run     : one condition, one process: verify input seal -> start thermal logger -> twelve-call qualification -> verify seal again ->
            measured schedule (first measured preparation <= 60 s after qualification; idle gap between observations <= 60 s).
            Fresh dedicated server + empty preload before EVERY observation (protocol s.8.2).
Timing (s.9.1): main timer from raw instruction to semantic decision (target / clarification / model-parser failure); key scoring,
integrity checks and file writes happen after it. Stage intervals in ns. Resolver = Steps 0-6 (A/B); C: null (not applicable).
Exit codes: 3 infrastructure failure (no usable model response), 4 runtime/continuity/seal violation, 5 harness error."""
import sys, os, json, csv, time, base64, hashlib, argparse, urllib.request, urllib.error, re, subprocess, signal, socket, http.client, platform, calendar
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); ART = os.path.abspath(os.path.join(ROOT, '..', '..'))
_argv = list(sys.argv); sys.argv = [sys.argv[0]]
import a4_bundle as AB                      # frozen-code hash check + ROS stubs + RC1.1 loaders (no side effects on import)
sys.argv = _argv
import sc_schedule as SCH
NAV, NEG, L3A = AB.NAV, AB.NEG, AB.L3A
import executive_contract as EC
PROTOCOL_ID = 'a4_semantic_comparison_20261005'
MODEL = 'qwen3.5:4b'
CONTROL_DIGEST = '0c8faadc50c205b83c634430c1dae6d1a4896c9b818cb8f290aa34d535265018'
OPTIONS = {'num_predict': 500, 'temperature': 0.3, 'num_ctx': 16384, 'top_k': 20, 'top_p': 0.95, 'presence_penalty': 1.5}
THINK = False
QUAL_RECORD = '20260821_143713#1'
CONTINUITY_S = 60
PORT = int(os.environ.get('SC_PORT', '11435')); URL = 'http://127.0.0.1:%d' % PORT
BIN = os.environ.get('SC_OLLAMA_BIN', '/usr/local/bin/ollama')
MODELS = os.environ.get('SC_MODELS', '/usr/share/ollama/.ollama/models')
SYSTEM_URL = os.environ.get('SC_SYSTEM_URL', 'http://127.0.0.1:11434')   # system service: checked, never touched
NO_NVIDIA = os.environ.get('SC_NO_NVIDIA') == '1'                         # tests only
ALLOW_UNSEALED = os.environ.get('SC_ALLOW_UNSEALED') == '1'               # tests only: recorded as UNSEALED-TEST
POLICY_PATH = os.path.join(AB.RC, 'config', 'policy.yaml'); POLICY = EC.load_policy(POLICY_PATH)
pc = time.perf_counter_ns
def boot_ns(): return time.clock_gettime_ns(time.CLOCK_BOOTTIME)       # advances during system suspend; perf_counter does not
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()
def utc(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
def harness_hashes(): return {f: sha(os.path.join(HERE, f)) for f in sorted(os.listdir(HERE)) if f.endswith('.py')}

class InfrastructureFailure(Exception):
    def __init__(self, kind, message): super().__init__(message); self.kind = kind; self.message = message
class RuntimeViolation(Exception):
    def __init__(self, what, detail): super().__init__(what); self.what = what; self.detail = detail

# ------------------------------------------------------------------ input seal (protocol s.8.3, s.11 steps 6-8)
def verify_seal():
    """full input seal: every sealed file in this tree, the harness file set, and every external v5 dependency. Returns SEAL.json sha256."""
    SP = os.path.join(ROOT, 'seal', 'SEAL.json')
    if not os.path.exists(SP):
        if ALLOW_UNSEALED: return 'UNSEALED-TEST'
        raise RuntimeViolation('seal_missing', SP)
    S = json.load(open(SP)); bad = []
    for f, h in S['files'].items():
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or sha(p) != h: bad.append(f)
    for f, h in S['external_dependencies'].items():
        p = os.path.join(ART, f)
        if not os.path.isfile(p) or sha(p) != h: bad.append('EXT:' + f)
    sealed_py = {os.path.basename(f) for f in S['files'] if f.startswith('harness/') and f.endswith('.py')}
    if set(harness_hashes()) != sealed_py: bad.append('harness .py set differs: %s' % sorted(set(harness_hashes()) ^ sealed_py))
    if bad: raise RuntimeViolation('seal_mismatch', bad[:20])
    return sha(SP)

# ------------------------------------------------------------------ processes, dedicated inference service (protocol s.8.1-8.2)
def _http(url, payload=None, timeout=600):
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
def proc_start(pid):
    try: return int(open('/proc/%s/stat' % pid).read().rsplit(')', 1)[1].split()[19])
    except Exception: return None
def _proc_table():
    out = subprocess.run(['ps', '-eo', 'pid,ppid,cmd'], capture_output=True, text=True).stdout.splitlines()[1:]
    return [l.strip().split(None, 2) for l in out]
def gpu_compute_pids():
    if NO_NVIDIA: return 'unavailable'
    r = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], capture_output=True, text=True)
    return sorted(x.strip() for x in r.stdout.splitlines() if x.strip()) if r.returncode == 0 else 'unavailable'
def launch_spec():
    return [BIN, 'serve'], dict(os.environ, OLLAMA_HOST='127.0.0.1:%d' % PORT, OLLAMA_MODELS=MODELS, OLLAMA_NOPRUNE='1')
class Server:
    def __init__(self, logdir): self.p = None; self.id = None; self.logdir = logdir; os.makedirs(logdir, exist_ok=True)
    def children(self):
        if not self.p: return []
        return [(r[0], proc_start(r[0]), r[2][:200]) for r in _proc_table() if len(r) > 2 and r[1] == str(self.p.pid)]
    def stop(self):
        if not self.p: return None
        pid = self.p.pid; kids = [(k[0], k[1]) for k in self.children()]; t0 = pc()
        try: os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: self.p.wait(timeout=30)
        except subprocess.TimeoutExpired: os.killpg(pid, signal.SIGKILL); self.p.wait()
        alive = []
        for _ in range(100):
            alive = [(p, s) for p, s in kids + [self.id] if s is not None and proc_start(p) == s]   # same PID AND same start time
            if not alive: break
            time.sleep(0.05)
        self.p = None
        return dict(server=self.id, runners=kids, stop_ns=pc() - t0, leftover=alive)
    def start(self):
        cmd, env = launch_spec(); log = os.path.join(self.logdir, 'server_%d.log' % time.time_ns())
        t0 = pc(); self.p = subprocess.Popen(cmd, env=env, stdout=open(log, 'w'), stderr=subprocess.STDOUT, start_new_session=True)
        self.id = (str(self.p.pid), proc_start(self.p.pid))
        for _ in range(600):
            try: v = _http(URL + '/api/version', timeout=2); break
            except Exception: time.sleep(0.05)
        else: raise RuntimeViolation('server_not_ready', log)
        return dict(server=self.id, version=v.get('version'), ready_ns=pc() - t0, log=os.path.basename(log))
    def preload(self):
        t0 = pc(); r = _http(URL + '/api/generate', {'model': MODEL, 'keep_alive': -1, 'options': {'num_ctx': OPTIONS['num_ctx']}})
        return pc() - t0, r
def system_service_models():
    if SYSTEM_URL == 'none': return []
    try: return [m.get('name') for m in _http(SYSTEM_URL + '/api/ps', timeout=5).get('models', [])]
    except Exception as e: return ['unreachable: %r' % e]
def prepare(server):
    """stop -> confirm runner (PID + start time) gone -> no competing GPU process -> fresh start -> nothing loaded -> empty preload ->
    verify digest, context 16384, GPU placement, runner identity, GPU processes = own runner only. Outside the decision timer."""
    ev = dict(t_utc=utc())
    st = server.stop(); ev['previous_stop'] = st
    if st and st['leftover']: raise RuntimeViolation('runner_not_terminated', st)
    sysm = system_service_models(); ev['system_service_loaded'] = sysm
    if sysm: raise RuntimeViolation('system_service_has_model_loaded', sysm)
    g0 = gpu_compute_pids(); ev['gpu_compute_pids_before_start'] = g0
    if g0 != 'unavailable' and g0: raise RuntimeViolation('competing_gpu_process', g0)
    ev['start'] = server.start()
    ps0 = _http(URL + '/api/ps').get('models', []); ev['loaded_before_preload'] = ps0
    if ps0: raise RuntimeViolation('model_loaded_before_preload', ps0)
    ev['preload_ns'], ev['preload_response'] = server.preload()
    ps1 = _http(URL + '/api/ps').get('models', [])
    ev['ps_after_preload'] = [{k: m.get(k) for k in ('name', 'digest', 'size', 'size_vram', 'context_length', 'expires_at')} for m in ps1]
    ev['runners'] = sorted((k[0], k[1]) for k in server.children()); ev['runner_cmds'] = [k[2] for k in server.children()]
    g1 = gpu_compute_pids(); ev['gpu_compute_pids_after_preload'] = g1
    ok = (len(ps1) == 1 and ps1[0].get('digest') == CONTROL_DIGEST and ps1[0].get('context_length') == OPTIONS['num_ctx']
          and (ps1[0].get('size_vram') or 0) > 0 and bool(ev['runners']) and all(s is not None for _, s in ev['runners']))
    if not ok: raise RuntimeViolation('preload_state_unexpected', ev)
    if g1 != 'unavailable' and not set(g1) <= {p for p, _ in ev['runners']}: raise RuntimeViolation('competing_gpu_process', dict(gpu=g1, runners=ev['runners']))
    return ev

# ------------------------------------------------------------------ model call, parser (frozen contract, unchanged)
def post_chat(body):
    req = urllib.request.Request(URL + '/api/chat', data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp: return resp.read()
    except urllib.error.HTTPError as e: raise InfrastructureFailure('http_status_%s' % e.code, repr(e))
    except urllib.error.URLError as e: raise InfrastructureFailure('connection_error', repr(e))
    except (socket.timeout, TimeoutError) as e: raise InfrastructureFailure('timeout', repr(e))
    except (ConnectionError, http.client.HTTPException) as e: raise InfrastructureFailure('transport_error', repr(e))
def decode_envelope(raw):
    try: result = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e: raise InfrastructureFailure('api_envelope_not_json', repr(e))
    if not isinstance(result, dict): raise InfrastructureFailure('api_envelope_not_object', type(result).__name__)
    if result.get('error') is not None: raise InfrastructureFailure('api_error_field', str(result.get('error'))[:300])
    msg = result.get('message')
    if msg is not None and (not isinstance(msg, dict) or not all(isinstance(msg.get(k), (str, type(None))) for k in ('content', 'thinking'))):
        raise InfrastructureFailure('api_envelope_malformed_message', repr(msg)[:300])
    return result
def parse(result):
    msg = result.get('message') or {}
    raw = (msg.get('content') or '').strip() or (msg.get('thinking') or '').strip()
    c = raw
    if '<think>' in c:
        i = c.rfind('</think>')
        if i != -1: c = c[i + 8:].strip()
    c = c.replace('```json', '').replace('```', '').strip()
    out = dict(raw_content=raw, json_parse='none', node_id=None, contract_ok=False, reason='')
    try: parsed = json.loads(c); out['json_parse'] = 'direct'
    except json.JSONDecodeError:
        m = re.search(r'\{.*?\}', c, re.DOTALL)
        if not m: out['json_parse'] = 'no_json'; return out
        try: parsed = json.loads(m.group(0)); out['json_parse'] = 'extracted'
        except json.JSONDecodeError: out['json_parse'] = 'malformed'; return out
    if not isinstance(parsed, dict) or 'node_id' not in parsed: out['json_parse'] += '_no_node_id'; return out
    nid = parsed['node_id']; out['reason'] = str(parsed.get('reason', ''))[:500]
    if isinstance(nid, int) and not isinstance(nid, bool): out['node_id'] = nid; out['contract_ok'] = True
    else: out['node_id_raw'] = json.dumps(nid)
    return out
def payload_bytes(prompt, img_b64, seed):
    return json.dumps({'model': MODEL, 'stream': False, 'think': THINK, 'keep_alive': -1, 'options': dict(OPTIONS, seed=seed),
                       'messages': [{'role': 'user', 'content': prompt, 'images': [img_b64]}]}).encode()
API_FIELDS = ['total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_cached_count', 'prompt_eval_duration', 'eval_count', 'eval_duration', 'done_reason']
def api_fields(result):
    out = {}
    for k in API_FIELDS:
        if k in result: out['api_' + k] = result[k]
        else: out['api_' + k] = None; out['api_' + k + '_status'] = 'unavailable_in_0.30.2' if k == 'prompt_eval_cached_count' else 'absent'
    return out

# ------------------------------------------------------------------ keys and context (setup, outside the timer)
def load_keys():
    E7 = {r['cell_id']: r for r in csv.DictReader(open(os.path.join(AB.SE, 'day2_20260821', 'session', 'E7_sealed_set_v2.csv'), encoding='utf-8'))}
    E2 = {r['item_id']: r for r in csv.DictReader(open(os.path.join(ROOT, 'manifest_candidate', 'e2_historical_key_transcription.csv'), encoding='utf-8'))}
    return E7, E2
def key_for(b, nodes, keys):
    E7, E2 = keys; iid = b['item_id']
    if iid.startswith('M3-'): return dict(kind='node_set', acceptable={int(b['key_ref'].split('node ')[1])})
    if iid.startswith('E7-'):
        acc = E7[iid[3:]]['acceptabil']
        return dict(kind='clarification') if acc == '-1' else dict(kind='node_set', acceptable={int(x) for x in acc.split('|')})
    k = E2[iid[3:]]
    if iid[3] == 'N': return dict(kind='clarification')
    forb = {int(x) for x in k['forbidden_nodes'].split('|')}; cur = b['current_node']['node_id']
    return dict(kind='node_set', acceptable=set(nodes) - forb - {cur}, current_node=cur)
def context_from_bundle(b):
    day = 'day1_20260820' if b['parent']['run_id'].startswith('20260820') else 'day2_20260821'
    for k in ('route_graph', 'static_objects', 'image_start'):
        if AB.sha(os.path.join(AB.RC, b[k]['path'])) != b[k]['sha256']: sys.exit('INPUT HASH MISMATCH %s %s' % (b['item_id'], k))
    nodes = AB.NODES[day]; pose = b['pose']
    mp = AB.mapping(day, nodes) if b['condition'] == 'S' else AB.mapping(day, nodes, b['dynamic']['yolo_objects'], b['dynamic']['static_currently_detected'], pose)
    digest = None
    if b['memory_digest']:
        if AB.sha(os.path.join(AB.RC, b['memory_digest']['path'])) != b['memory_digest']['sha256']: sys.exit('DIGEST HASH ' + b['item_id'])
        digest, _ = NAV.load_memory_digest(os.path.join(AB.RC, b['memory_digest']['path']))
    return day, nodes, pose, mp, digest

# ------------------------------------------------------------------ one observation
def observe(b, arm, seed, keys, mode, server=None, key_hook=None, prep_gate=None):
    day, nodes, pose, mp, digest = context_from_bundle(b)                       # resident state, loaded before the instruction
    m3_index = L3A.precompute_m3_tokens(digest) if (digest and arm == 'A') else None
    env = b['negation_envelope']; neg_flag = env['active']; forbidden = set(env['forbidden_nodes'])
    rec = dict(item_id=b['item_id'], condition=b['condition'], arm=arm, seed=seed, stratum=b['stratum'])
    if mode == 'run':
        if prep_gate: rec['continuity'] = prep_gate()                           # idle-gap check before this preparation
        rec['runtime_prep'] = prepare(server)
    b0, m0 = boot_ns(), time.monotonic_ns()
    T = {}; result = None; vlm = None; prompt = notice = body = None
    # ======== main decision timer ========
    t0 = pc()
    path, node = None, None
    if arm in ('A', 'B'):
        r0 = pc(); nid, reason, det = L3A.try_deterministic_resolve(b['instruction'], nodes, mp, pose, m3_index); T['resolver_ns'] = pc() - r0
        rec.update(l3a_reason=reason, escalation_reason=det.get('escalation_reason'), resolution_step=det.get('resolution_step'))
        if nid is not None: path, node = 'L3a', nid
    else:
        T['resolver_ns'] = None                                                   # C: not applicable
    if path is None:
        path = 'L3b'
        s = pc(); img_b64 = base64.b64encode(open(os.path.join(AB.RC, b['image_start']['path']), 'rb').read()).decode(); T['image_ns'] = pc() - s
        s = pc(); prefix = NAV.build_memory_prefix(digest); notice = env['rendered_notice']
        prompt = NAV.build_vlm_prompt(b['instruction'], pose, nodes, mp, memory_prefix=prefix, negation_notice=notice); T['prompt_ns'] = pc() - s
        s = pc(); body = payload_bytes(prompt, img_b64, seed); T['serialize_ns'] = pc() - s
        if mode == 'dry':
            rec.update(path=path, decision='would_call_vlm', payload_sha256=shab(body), **{k: T.get(k) for k in ('resolver_ns', 'image_ns', 'prompt_ns', 'serialize_ns')})
            _post_checks(b, env, prompt, notice); return rec
        s = pc(); raw = post_chat(body); T['api_ns'] = pc() - s
        s = pc(); result = decode_envelope(raw); T['decode_ns'] = pc() - s
        s = pc(); vlm = parse(result); T['parse_ns'] = pc() - s
        node = vlm['node_id']
    s = pc(); decision, sub, gstate = None, '', None
    if path == 'L3b' and not vlm['contract_ok']: decision = 'model_or_parser_failure'
    elif node == -1: decision, sub = 'clarification', 'vlm_explicit_-1'
    elif neg_flag:
        ok, gstate = NEG.validate_vlm_against_negation(node, forbidden)
        if not ok: decision, sub = 'clarification', 'guard_blocked:' + gstate
    if decision is None and node not in nodes: decision, sub = 'model_or_parser_failure', 'node_not_in_graph'
    if decision is None:
        vr = EC.validate_action(node, 'ComputeRoute', nodes, POLICY, pose)
        decision, sub = ('target', '') if vr.allowed else ('clarification', 'validation_blocked')
    T['guard_validation_ns'] = pc() - s
    t_end = pc(); T['decision_ns'] = t_end - t0
    # ======== after the timer: suspension, integrity, runtime checks, scoring, record ========
    rec['_t_decision_end_ns'] = t_end
    if mode == 'run':
        drift = (boot_ns() - b0) - (time.monotonic_ns() - m0); rec['suspend_drift_ns'] = drift
        if drift > 1_000_000_000: raise RuntimeViolation('system_suspended_during_observation', drift)
    if path == 'L3b': _post_checks(b, env, prompt, notice)
    if mode == 'run' and path == 'L3b':
        after = sorted((k[0], k[1]) for k in server.children())
        rec['runners_after_call'] = after
        if after != rec['runtime_prep']['runners']: raise RuntimeViolation('runner_replaced', dict(before=rec['runtime_prep']['runners'], after=after))
        cached = result.get('prompt_eval_cached_count')
        if isinstance(cached, int) and cached > 0: raise RuntimeViolation('cached_prompt_tokens', cached)
    if key_hook: key_hook()
    key = key_for(b, nodes, keys)
    if decision == 'target':
        if key['kind'] == 'clarification': cls = 'incorrect_executable'
        elif node in key['acceptable']: cls = 'acceptable'
        else: cls = 'incorrect_executable'; sub = 'same_node_no_motion' if key.get('current_node') == node else sub
    else: cls = decision
    correct = (cls == 'clarification') if key['kind'] == 'clarification' else (cls == 'acceptable')
    rec.update(path=path, node_id=node, decision=decision, outcome=cls, outcome_sub=sub, guard_state=gstate, correct=correct, **T)
    if path == 'L3b':
        rec.update(payload_sha256=shab(body), prompt_sha256=AB.shas(prompt), raw_content=vlm['raw_content'], json_parse=vlm['json_parse'],
                   contract_ok=vlm['contract_ok'], vlm_reason=vlm['reason'], node_id_raw=vlm.get('node_id_raw'), **api_fields(result), api_envelope=result)
    return rec
def _post_checks(b, env, prompt, notice):
    if AB.shas(notice) != env['rendered_notice_sha256']: sys.exit('NEGATION ENVELOPE INTEGRITY FAIL ' + b['item_id'])
    if AB.shas(prompt) != b['l3b_prompt']['sha256']: sys.exit('PROMPT INTEGRITY FAIL ' + b['item_id'])

# ------------------------------------------------------------------ verification helpers
def verify_bundles():
    B = os.path.join(ROOT, 'bundles'); bad = []
    for line in open(os.path.join(B, 'BUNDLES.sha256')):
        h, p = line.split('  ', 1); p = p.strip()
        if AB.sha(os.path.join(B, p)) != h: bad.append(p)
    if bad: sys.exit('BUNDLE HASH MISMATCH: %s' % bad[:5])
    return sha(os.path.join(B, 'BUNDLES.sha256'))
def load_schedule(cond):
    D = os.path.join(ROOT, 'schedule'); exp = dict(l.split()[::-1] for l in open(os.path.join(D, 'SCHEDULE.sha256')))
    p = os.path.join(D, 'SCHEDULE_%s.csv' % cond)
    if sha(p) != exp['SCHEDULE_%s.csv' % cond]: sys.exit('SCHEDULE HASH MISMATCH')
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    if rows != [{k: str(v) for k, v in r.items()} for r in SCH.schedule(cond)]: sys.exit('SCHEDULE != regenerated schedule')
    return rows, sha(p)
def bundle(cond, iid): return json.load(open(os.path.join(ROOT, 'bundles', cond, iid + '.json'), encoding='utf-8'))
def json_default(o): return sorted(o) if isinstance(o, set) else str(o)

# ------------------------------------------------------------------ thermal logger (protocol s.8.5)
class Thermal:
    def __init__(self, path): self.path = path; self.p = None
    def start(self):
        self.p = subprocess.Popen([sys.executable, '-B', os.path.join(HERE, 'sc_thermal.py'), self.path, '5'], start_new_session=True)
        for _ in range(300):
            if os.path.exists(self.path) and sum(1 for _ in open(self.path)) >= 3: return
            if self.p.poll() is not None: break
            time.sleep(0.05)
        raise RuntimeViolation('thermal_logger_not_running', self.path)
    def alive(self): return self.p is not None and self.p.poll() is None
    def stop(self):
        if not self.p: return None
        try: os.killpg(self.p.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: self.p.wait(timeout=15)
        except subprocess.TimeoutExpired: os.killpg(self.p.pid, signal.SIGKILL)
        lines = [l for l in open(self.path) if l and not l.startswith('#')]
        mono = [int(l.split(',')[1]) for l in lines[1:]]
        gaps = [(b - a) / 1e9 for a, b in zip(mono, mono[1:])]
        return dict(file=os.path.basename(self.path), sha256=sha(self.path), samples=len(mono), max_gap_s=round(max(gaps), 3) if gaps else None,
                    header=open(self.path).readline().strip())

# ------------------------------------------------------------------ qualification (protocol s.8.3)
def qualification_payload():
    run, seq = QUAL_RECORD.split('#'); r = AB.REC[(run, seq)]; bb = AB.build(r, 'H')
    if bb['prompt'] != r['extra']['vlm_prompt_full']: sys.exit('qualification prompt != historical prompt')
    parents = {(x['parent_run_id'], x['parent_record_seq']) for x in csv.DictReader(open(os.path.join(ROOT, 'manifest_candidate', 'A4_items_candidate.csv'), encoding='utf-8'))}
    if (run, seq) in parents: sys.exit('qualification record is a manifest parent: refused')
    img = os.path.join(AB.SE, r['_day'], 'logs', r['images']['start'])
    return bb['prompt'], img, payload_bytes(bb['prompt'], base64.b64encode(open(img, 'rb').read()).decode(), SCH.item_seed(0, QUAL_RECORD, 'qualification'))
def qualify(outdir, server, seal_sha, thermal=None):
    prompt, img, body = qualification_payload()
    Q = dict(protocol=PROTOCOL_ID, seal_sha256=seal_sha, started_utc=utc(), record=QUAL_RECORD, prompt_sha256=AB.shas(prompt), image_sha256=sha(img),
             payload_sha256=shab(body), harness_sha256=harness_hashes(), calls=[])
    def one(phase, i, prep):
        s = pc(); raw = post_chat(body); w = pc() - s; res = decode_envelope(raw); pv = parse(res)
        after = sorted((k[0], k[1]) for k in server.children())
        c = dict(phase=phase, i=i, wall_ns=w, contract_ok=pv['contract_ok'], node_id=pv['node_id'], content_sha256=hashlib.sha256(pv['raw_content'].encode()).hexdigest(),
                 runners_after_call=after, prep=prep, **api_fields(res), api_envelope=res)
        Q['calls'].append(c)
        print('Q %s%d wall %.0f ms | prompt_eval %.0f ms | cached %s | runner %s | contract %s' % (phase, i, w / 1e6, (res.get('prompt_eval_duration') or 0) / 1e6,
              c.get('api_prompt_eval_cached_count_status', c['api_prompt_eval_cached_count']), after, pv['contract_ok']), flush=True)
        if thermal and not thermal.alive(): raise RuntimeViolation('thermal_logger_died', 'qualification')
        return c
    prep = prepare(server)
    for i in range(1, 7): one('R', i, prep if i == 1 else None)
    for i in range(1, 7): one('I', i, prepare(server))
    Q['final_stop'] = server.stop(); Q['ended_utc'] = utc(); Q['ended_boot_ns'] = boot_ns()
    I = [c for c in Q['calls'] if c['phase'] == 'I']; R = [c for c in Q['calls'] if c['phase'] == 'R']
    crit = dict(
        all_contract_ok=all(c['contract_ok'] for c in Q['calls']),
        isolated_distinct_servers=len({tuple(c['prep']['start']['server']) for c in I}) == 6,
        isolated_distinct_runners=len({tuple(map(tuple, c['prep']['runners'])) for c in I}) == 6,
        isolated_nothing_loaded_before_preload=all(c['prep']['loaded_before_preload'] == [] for c in I),
        isolated_identity_after_preload=all(c['prep']['ps_after_preload'][0]['digest'] == CONTROL_DIGEST and c['prep']['ps_after_preload'][0]['context_length'] == OPTIONS['num_ctx'] for c in I),
        isolated_runner_not_replaced=all(c['runners_after_call'] == c['prep']['runners'] for c in I),
        no_leftover_processes=all(not (c['prep']['previous_stop'] or {}).get('leftover') for c in I) and not (Q['final_stop'] or {}).get('leftover'),
        system_service_idle=all(c['prep']['system_service_loaded'] == [] for c in I),
        cached_count_zero_or_unavailable=all(c['api_prompt_eval_cached_count'] in (None, 0) for c in I),
        thermal_logger_alive=(thermal.alive() if thermal else True))
    pe = lambda cs: [c['api_prompt_eval_duration'] / 1e6 for c in cs if isinstance(c['api_prompt_eval_duration'], int)]
    Q['corroboration'] = dict(prompt_eval_cached_count=('unavailable_in_0.30.2' if all(c['api_prompt_eval_cached_count'] is None for c in Q['calls']) else 'present'),
                              retained_R2_R6_prompt_eval_ms=pe(R[1:]), isolated_prompt_eval_ms=pe(I))
    Q['criteria'] = crit; Q['pass'] = all(crit.values())
    fn = os.path.join(outdir, 'QUALIFICATION.json'); json.dump(Q, open(fn, 'w'), indent=1, default=json_default)
    print('QUALIFICATION', 'PASS' if Q['pass'] else 'FAIL', {k: v for k, v in crit.items() if not v}, sha(fn), flush=True)
    return Q, fn

def runtime_capture():
    run = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
    cmd, env = launch_spec()
    return dict(captured_utc=utc(), host=platform.node(), os=run('. /etc/os-release && echo "$PRETTY_NAME"'), kernel=platform.release(),
                cpu=run("lscpu | grep -E 'Model name|^CPU\\(s\\)'"), ram_bytes=run("free -b | awk '/Mem:/{print $2}'"),
                gpu=run('nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader'), python=sys.version.split()[0],
                ollama_bin=BIN, ollama_bin_sha256=sha(BIN) if os.path.exists(BIN) else None, ollama_version=run('%s --version' % BIN),
                server_launch=dict(cmd=cmd, env=env), models_dir=MODELS, port=PORT, system_url=SYSTEM_URL,
                options=OPTIONS, think=THINK, model=MODEL, control_digest=CONTROL_DIGEST, continuity_limit_s=CONTINUITY_S)

# ------------------------------------------------------------------ main
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry', 'qualify', 'run'], required=True)
    ap.add_argument('--condition', choices=['S', 'H'])
    ap.add_argument('--run-tag', help='run: new directory runs/<cond>/run_<tag>; never reused')
    a = ap.parse_args()
    bundles_sha = verify_bundles(); keys = load_keys()
    if a.mode == 'qualify':
        d = os.path.join(ROOT, 'runtime', 'qualify_%s' % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())); os.makedirs(d)
        seal_sha = verify_seal(); json.dump(runtime_capture(), open(os.path.join(d, 'RUNTIME_CAPTURE.json'), 'w'), indent=1)
        srv = Server(os.path.join(d, 'server_logs'))
        try: Q, fn = qualify(d, srv, seal_sha)
        finally: srv.stop()
        sys.exit(0 if Q['pass'] else 4)
    if not a.condition: sys.exit('--condition required')
    rows, sched_sha = load_schedule(a.condition)
    if a.mode == 'dry':
        from collections import Counter, defaultdict
        out = os.path.join(ROOT, 'runs', a.condition, 'dry'); os.makedirs(out, exist_ok=True); recs = []
        for r in rows: recs.append(observe(bundle(a.condition, r['item_id']), r['arm'], int(r['seed']), keys, 'dry'))
        ph = defaultdict(set)
        for x in recs:
            if x.get('payload_sha256'): ph[(x['item_id'], x['seed'])].add(x['payload_sha256'])
        same = all(len(v) == 1 for v in ph.values())
        print(a.condition, 'dry', len(recs), 'observations | routing', dict(Counter((x['arm'], x['path'], x.get('decision') or x.get('outcome')) for x in recs)))
        print('payload identical across arms for every item x seed reaching the VLM:', same, '(%d keys)' % len(ph))
        json.dump(dict(condition=a.condition, schedule_sha256=sched_sha, bundles_sha256=bundles_sha, harness_sha256=harness_hashes(), n=len(recs),
                       payload_identity=same, records=recs), open(os.path.join(out, 'DRY.json'), 'w'), indent=1, default=json_default)
        sys.exit(0 if same else 1)
    # ---- run: seal -> thermal -> qualification -> seal -> measured schedule, one process
    if not a.run_tag or not re.fullmatch(r'[A-Za-z0-9_-]+', a.run_tag): sys.exit('run mode requires --run-tag [A-Za-z0-9_-]+')
    out = os.path.join(ROOT, 'runs', a.condition, 'run_' + a.run_tag)
    if os.path.exists(out): sys.exit('run directory exists: never reused')
    os.makedirs(out); server = Server(os.path.join(out, 'server_logs')); thermal = Thermal(os.path.join(out, 'thermal.csv'))
    hp = os.path.join(out, 'RUN_HEADER.json')
    header = dict(protocol=PROTOCOL_ID, condition=a.condition, run_tag=a.run_tag, started_utc=utc(), ended_utc=None, completed=False, valid=False,
                  records_expected=len(rows), records_written=0, schedule_sha256=sched_sha, bundles_sha256=bundles_sha, harness_sha256=harness_hashes(),
                  runtime_capture=runtime_capture(), frozen_code={f: AB.sha(os.path.join(AB.CODE, f)) for f in AB.FROZEN}, timer='time.perf_counter_ns',
                  options=OPTIONS, think=THINK, policy_sha256=sha(POLICY_PATH), continuity_limit_s=CONTINUITY_S)
    def save(): json.dump(header, open(hp, 'w'), indent=1, default=json_default)
    save(); code = 0
    last_end = {}
    def gate():
        now = boot_ns(); gap = (now - last_end['boot']) / 1e9
        if gap > CONTINUITY_S: raise RuntimeViolation('continuity_gap', dict(after=last_end['what'], gap_s=round(gap, 3)))
        return dict(gap_s=round(gap, 3), after=last_end['what'])
    try:
        header['seal_sha256_before_qualification'] = verify_seal(); save()
        thermal.start()
        Q, qfn = qualify(out, server, header['seal_sha256_before_qualification'], thermal)
        header['qualification'] = dict(file=os.path.basename(qfn), sha256=sha(qfn), passed=Q['pass']); save()
        if not Q['pass']: raise RuntimeViolation('qualification_failed', {k: v for k, v in Q['criteria'].items() if not v})
        header['seal_sha256_before_measurement'] = verify_seal()
        if header['seal_sha256_before_measurement'] != header['seal_sha256_before_qualification']: raise RuntimeViolation('seal_changed', '')
        last_end.update(boot=Q['ended_boot_ns'], what='qualification'); save()
        for r in rows:
            if not thermal.alive(): raise RuntimeViolation('thermal_logger_died', header['records_written'])
            rec = observe(bundle(a.condition, r['item_id']), r['arm'], int(r['seed']), keys, 'run', server, prep_gate=gate)
            rec.update(seq=int(r['seq']), block=int(r['block']), position=int(r['position']), order=r['order'], seed_base=int(r['seed_base']))
            with open(os.path.join(out, 'records.jsonl'), 'a', encoding='utf-8') as f: f.write(json.dumps(rec, ensure_ascii=False, default=json_default) + '\n')
            header['records_written'] += 1; save()
            last_end.update(boot=boot_ns(), what='seq %d' % int(r['seq']))
            if header['records_written'] % 10 == 0: print('%s %d/%d' % (a.condition, header['records_written'], len(rows)), flush=True)
    except InfrastructureFailure as e:
        header['infrastructure_failure'] = dict(seq=header['records_written'], type=e.kind, message=e.message, utc=utc()); code = 3
    except RuntimeViolation as e:
        header['runtime_violation'] = dict(seq=header['records_written'], what=e.what, detail=e.detail, utc=utc()); code = 4
    except Exception as e:
        header['harness_error'] = dict(seq=header['records_written'], error=repr(e), utc=utc()); code = 5
    finally:
        try: header['final_stop'] = server.stop()
        except Exception as e: header['final_stop'] = dict(error=repr(e), leftover=['unknown'])
        try: header['thermal'] = thermal.stop()
        except Exception as e: header['thermal'] = dict(error=repr(e))
        header['ended_utc'] = utc(); header['completed'] = header['records_written'] == len(rows) and code == 0
        leftover = (header['final_stop'] or {}).get('leftover') if isinstance(header['final_stop'], dict) else None
        if leftover: header['final_leftover_processes'] = leftover
        header['valid'] = bool(header['completed'] and not leftover and isinstance(header.get('thermal'), dict) and header['thermal'].get('samples'))
        save()
    print('%s run %s: %d/%d records, completed=%s valid=%s exit=%d' % (a.condition, a.run_tag, header['records_written'], len(rows), header['completed'], header['valid'], code))
    sys.exit(code)
