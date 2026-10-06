"""Forbidden-node guard branch test (Comment 5), offline, no model, no robot.
Drives the FROZEN deployed method VLMNavigatorNode._vlm_cycle (vlm_navigator_node_v4_8_review.py) for each of the 14 distinct E2
negation instructions, with the parent record's context, a synthetic /api/chat envelope injected at HTTP level (so the deployed
call_vlm parser runs), the deployed negation_guard, validate_action and fallback branch. Navigation dispatch is intercepted.
Modes:
  build : write cases/CASES.json (every forbidden node per instruction, one permitted-node control, parser/contract controls) with the
          expected branch per case, derived from the frozen code BEFORE any run. Writes nothing else.
  seal  : seal cases + this script + a4_bundle.py (never overwrites)        --operator NAME
  run   : verify seal, run all cases, write results/ (never overwrites)
python3 -B gt.py build | seal --operator NAME | run"""
import os, sys, json, csv, time, hashlib, argparse, io, types, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
_argv = list(sys.argv); sys.argv = [sys.argv[0]]
import a4_bundle as AB
sys.argv = _argv
NAV, NEG = AB.NAV, AB.NEG
import executive_contract as EC
E2_KEY = os.path.join(ROOT, '..', '13_semantic_comparison', 'manifest_candidate', 'e2_historical_key_transcription.csv')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def utc(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

# ------------------------------------------------------------------ context of each instruction (parent = first chronological record)
def parent(instr):
    hits = sorted((k for k, r in AB.REC.items() if (r.get('instruction') or '').strip().lower() == instr.strip().lower()), key=lambda k: (k[0], int(k[1])))
    return hits[0] if hits else None
def context(key):
    r = AB.REC[key]; day = r['_day']; nodes = AB.NODES[day]; b = AB.build(r, 'S')
    graph = json.load(open(os.path.join(AB.SE, day, 'config', 'route_graph_fiir.geojson')))
    return r, day, nodes, b, graph

# ------------------------------------------------------------------ build: cases and expected branches (from the frozen code)
CONTROLS = [('explicit_minus1', '{"node_id": -1, "reason": "unclear"}'),
            ('missing_target', '{"reason": "no target given"}'),
            ('string_target', '{"node_id": "%(perm)d", "reason": "string id"}'),
            ('boolean_true', '{"node_id": true, "reason": "boolean"}'),
            ('float_of_forbidden', '{"node_id": %(forb0)d.0, "reason": "float id"}'),
            ('malformed_no_json', 'I would go to node %(perm)d'),
            ('nonexistent_node', '{"node_id": 999, "reason": "not in graph"}')]
def expected(kind, val, forbidden, nodes, perm_ok_dispatch=True):
    """branch implied by the frozen code (negation path of _vlm_cycle):
    call_vlm: no JSON -> ValueError -> 'vlm_failed'; otherwise returns parsed['node_id'] unchanged (no int coercion).
    validate_vlm_against_negation: None -> vlm_no_answer (blocked); -1 -> vlm_requested_clarification (blocked); x in forbidden ->
    vlm_violated_negation (blocked); else ok. Then: node None or not in nodes -> 'vlm_invalid_response'; else validate_action -> dispatch.
    Python equality: True == 1 and 0.0 == 0, so set/dict membership treats them as those integers."""
    if kind == 'malformed_no_json': return dict(outcome='vlm_failed', guard_state=None, dispatch=False)
    if val is None: return dict(outcome='clarification_requested', guard_state='vlm_no_answer', dispatch=False)
    if val == -1 and not isinstance(val, bool): return dict(outcome='clarification_requested', guard_state='vlm_requested_clarification', dispatch=False)
    if val in forbidden: return dict(outcome='clarification_requested', guard_state='vlm_violated_negation', dispatch=False)
    if val not in nodes: return dict(outcome='vlm_invalid_response', guard_state='ok', dispatch=False)
    return dict(outcome='dispatched', guard_state='ok', dispatch=True, dispatch_node=int(val))
def build():
    os.makedirs(os.path.join(ROOT, 'cases'), exist_ok=True); out = os.path.join(ROOT, 'cases', 'CASES.json')
    if os.path.exists(out): sys.exit('cases/CASES.json exists: never overwritten')
    rows = list(csv.DictReader(open(E2_KEY, encoding='utf-8'))); cases = []; instr_meta = []
    policy = EC.load_policy(os.path.join(AB.RC, 'config', 'policy.yaml'))
    for row in rows:
        key = parent(row['instruction'])
        if key is None: sys.exit('no parent record for ' + row['item_id'])
        r, day, nodes, b, graph = context(key)
        forb_t = sorted(int(x) for x in row['forbidden_nodes'].split('|'))
        forb_r = sorted(b['forbidden_recomputed_for_gate_1b'])
        pose = b['pose']; cur = b['current_node']
        cands = [n for n in sorted(nodes) if n not in forb_t and n != cur and NAV.euclidean(pose['x'], pose['y'], nodes[n]['x'], nodes[n]['y']) >= NAV.GOAL_TOLERANCE_M
                 and EC.validate_action(n, 'ComputeRoute', nodes, policy, pose).allowed]
        perm = cands[0]
        instr_meta.append(dict(item_id=row['item_id'], instruction=row['instruction'], parent=list(key), day=day, forbidden_transcribed=forb_t,
                               forbidden_recomputed=forb_r, envelope_match=forb_t == forb_r, current_node=cur, permitted_control=perm,
                               permitted_rule='lowest node id: not forbidden, not the current node, beyond goal tolerance, allowed by validate_action'))
        for f in forb_t:
            cases.append(dict(case_id='%s-F%d' % (row['item_id'], f), item_id=row['item_id'], kind='forbidden_proposal', reply='{"node_id": %d, "reason": "synthetic"}' % f,
                              expected=expected('forbidden_proposal', f, set(forb_t), nodes)))
        cases.append(dict(case_id='%s-P%d' % (row['item_id'], perm), item_id=row['item_id'], kind='permitted_control', reply='{"node_id": %d, "reason": "synthetic"}' % perm,
                          expected=expected('permitted_control', perm, set(forb_t), nodes)))
        for kind, tpl in CONTROLS:
            reply = tpl % dict(perm=perm, forb0=forb_t[0])
            try: val = json.loads(reply).get('node_id')
            except json.JSONDecodeError: val = 'NOJSON'
            cases.append(dict(case_id='%s-%s' % (row['item_id'], kind), item_id=row['item_id'], kind=kind, reply=reply,
                              expected=expected(kind, val, set(forb_t), nodes)))
    doc = dict(built_utc=utc(), e2_key=os.path.relpath(E2_KEY, ROOT), e2_key_sha256=sha(E2_KEY), frozen_code={f: AB.sha(os.path.join(AB.CODE, f)) for f in AB.FROZEN},
               instructions=instr_meta, n_cases=len(cases), cases=cases)
    json.dump(doc, open(out, 'w'), indent=1)
    print('instructions', len(instr_meta), '| envelopes match transcription', sum(i['envelope_match'] for i in instr_meta), '| cases', len(cases),
          '| forbidden proposals', sum(c['kind'] == 'forbidden_proposal' for c in cases), '| CASES.json', sha(out))

# ------------------------------------------------------------------ run the deployed branch on one case
class FakeAudit:
    def __init__(self): self.decisions = []; self.events = []
    def log_decision(self, e): self.decisions.append(e)
    def log_event(self, *a, **k): self.events.append(a)
    def create_mission_dir(self, idx, name): return '/nonexistent/run/mission_%d_%s' % (idx, name)
    def save_image(self, *a, **k): return None
    def save_text(self, *a, **k): return None
class Log:
    def __init__(self): self.lines = []
    def info(self, m): self.lines.append(('I', str(m)))
    def warn(self, m): self.lines.append(('W', str(m)))
    warning = warn
    def error(self, m): self.lines.append(('E', str(m)))
class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def run_case(case, meta):
    key = tuple(meta['parent']); r, day, nodes, b, graph = context(key)
    digest = None
    if b['digest_path']: digest, _ = NAV.load_memory_digest(b['digest_path'])
    n = NAV.VLMNavigatorNode.__new__(NAV.VLMNavigatorNode)
    log = Log(); status = []; dispatch = []; completed = []
    n.instruction = meta['instruction']; n.nav_cycle_count = 0; n.vlm_busy = False; n.previous_node_id = None; n.navigating = False
    n._dead_ends_computed = True; n._dead_end_nodes = set(); n.static_objects = AB.STATIC[day]
    n._poi_signatures = NAV.load_poi_signatures(os.path.join(AB.SE, day, 'config', 'semantic_objects_static_v2.geojson'))
    n._memory_digest = digest; n._m3_index = AB.L3A.precompute_m3_tokens(digest) if digest else []
    n._memory_prefix_cached = NAV.build_memory_prefix(digest); n._digest_content_md5 = None; n._digest_generated_at = None
    n._policy = EC.load_policy(os.path.join(AB.RC, 'config', 'policy.yaml')); n._audit = FakeAudit(); n._mission_count = 0
    n._startup_obj_mapping = None; n._nav_phases = {}; n._nav_extra = {}; n._mission_dir = None
    n.get_logger = lambda: log; n._publish_status = lambda s: status.append(s)
    n._navigate_with_route = lambda target, node_id, timeout=180.0: dispatch.append(node_id)
    n._log_completed = lambda node_id, name, outcome, confirmation_data=None: completed.append((node_id, outcome))
    n._get_amcl_pose = lambda: None; n._odom_reset = lambda: None
    ctx = dict(pose=b['pose'], graph=graph, objects={})
    env = json.dumps({'message': {'role': 'assistant', 'content': case['reply']}, 'done_reason': 'stop', 'total_duration': 1, 'eval_count': 1, 'eval_duration': 1}).encode()
    saved = (NAV.http_get_json_with_retry, NAV.fetch_camera_b64, NAV.urllib.request.urlopen)
    NAV.http_get_json_with_retry = lambda *a, **k: ctx; NAV.fetch_camera_b64 = lambda: 'c3ludGhldGlj'
    NAV.urllib.request.urlopen = lambda *a, **k: _Resp(env)
    try: n._vlm_cycle(); err = None
    except Exception as e: err = repr(e)
    finally: NAV.http_get_json_with_retry, NAV.fetch_camera_b64, NAV.urllib.request.urlopen = saved
    dec = [dict(nav_outcome=getattr(e, 'nav_outcome', None), method=getattr(e, 'resolution_method', None), node_id=getattr(e, 'node_id', None),
                guard_state=(getattr(e, 'extra', None) or {}).get('vlm_negation_check'), forbidden=(getattr(e, 'extra', None) or {}).get('negation_forbidden_nodes'),
                proposed=(getattr(e, 'extra', None) or {}).get('vlm_proposed_node'), escalation=(getattr(e, 'extra', None) or {}).get('escalation_reason'))
           for e in n._audit.decisions]
    if dispatch: outcome = 'dispatched'
    elif completed: outcome = 'completed_without_dispatch'
    elif dec: outcome = dec[-1]['nav_outcome']
    elif any('vlm_failed' in s for s in status): outcome = 'vlm_failed'
    else: outcome = 'no_record'
    nx = getattr(n, '_nav_extra', {}) or {}
    gs = dec[-1]['guard_state'] if dec else nx.get('vlm_negation_check')
    forb_used = dec[-1]['forbidden'] if dec else nx.get('negation_forbidden_nodes')
    return dict(case_id=case['case_id'], kind=case['kind'], reply=case['reply'], outcome=outcome, guard_state=gs, forbidden_used=forb_used,
                proposed=(dec[-1]['proposed'] if dec else nx.get('vlm_proposed_node')), dispatch=dispatch, completed=completed,
                decisions=dec, status=status, error=err, log=[m for _, m in log.lines][-6:])

# ------------------------------------------------------------------ seal / run
FILES = ['cases/CASES.json', 'harness/gt.py', 'harness/a4_bundle.py']
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['build', 'seal', 'run']); ap.add_argument('--operator'); a = ap.parse_args()
    if a.mode == 'build': build(); sys.exit(0)
    SP = os.path.join(ROOT, 'seal', 'GT_SEAL.json')
    if a.mode == 'seal':
        if not a.operator: sys.exit('--operator required')
        if os.path.exists(SP): sys.exit('seal exists: never overwritten')
        if os.path.exists(os.path.join(ROOT, 'results')): sys.exit('results exist before seal: refused')
        os.makedirs(os.path.dirname(SP))
        s = dict(sealed_utc=utc(), operator=a.operator, files={f: sha(os.path.join(ROOT, f)) for f in FILES},
                 external={'e2_key': sha(E2_KEY), **{'code/' + f: AB.sha(os.path.join(AB.CODE, f)) for f in AB.FROZEN}})
        json.dump(s, open(SP, 'w'), indent=1); print('GT SEALED', s['sealed_utc'], sha(SP)); sys.exit(0)
    if not os.path.exists(SP): sys.exit('not sealed')
    S = json.load(open(SP)); bad = [f for f, h in S['files'].items() if sha(os.path.join(ROOT, f)) != h]
    if sha(E2_KEY) != S['external']['e2_key']: bad.append('e2_key')
    if bad: sys.exit('seal mismatch: %s' % bad)
    out = os.path.join(ROOT, 'results')
    if os.path.exists(out): sys.exit('results exist: never overwritten')
    C = json.load(open(os.path.join(ROOT, 'cases', 'CASES.json'))); M = {m['item_id']: m for m in C['instructions']}
    res = []
    for c in C['cases']:
        o = run_case(c, M[c['item_id']]); e = c['expected']
        o['expected'] = e
        o['match'] = (o['outcome'] == e['outcome'] and (e.get('guard_state') is None or o['guard_state'] == e['guard_state'])
                      and bool(o['dispatch']) == e['dispatch'] and (not e['dispatch'] or o['dispatch'] == [e['dispatch_node']]))
        res.append(o)
    os.makedirs(out)
    json.dump(dict(run_utc=utc(), seal_sha256=sha(SP), n=len(res), results=res), open(os.path.join(out, 'GT_RESULTS.json'), 'w'), indent=1, default=str)
    F = [x for x in res if x['kind'] == 'forbidden_proposal']; P = [x for x in res if x['kind'] == 'permitted_control']
    lines = ['# Forbidden-node guard branch test — results (data only)', '', 'Run %s · GT_SEAL.json %s' % (utc(), sha(SP)), '',
             'Deployed `_vlm_cycle` (vlm_navigator_node_v4_8_review.py), deployed `call_vlm` parser, `negation_guard`, `validate_action`; synthetic replies injected at HTTP level; navigation dispatch intercepted; no robot, no model.', '',
             '- Forbidden proposals rejected, no dispatch: **%d / %d**' % (sum(1 for x in F if x['outcome'] == 'clarification_requested' and not x['dispatch']), len(F)),
             '- Permitted-node controls passed the guard and reached dispatch: **%d / %d**' % (sum(1 for x in P if x['outcome'] == 'dispatched'), len(P)),
             '- Cases matching the branch pre-specified from the frozen code: **%d / %d**' % (sum(x['match'] for x in res), len(res)), '',
             '| Control kind | n | observed outcome (guard state) | dispatch |', '|---|---|---|---|']
    from collections import Counter
    for kind in ['forbidden_proposal', 'permitted_control'] + [k for k, _ in CONTROLS]:
        xs = [x for x in res if x['kind'] == kind]
        c = Counter('%s (%s)' % (x['outcome'], x['guard_state']) for x in xs)
        lines.append('| %s | %d | %s | %d |' % (kind, len(xs), '; '.join('%s ×%d' % kv for kv in c.items()), sum(1 for x in xs if x['dispatch'])))
    mism = [x['case_id'] for x in res if not x['match']]
    lines += ['', 'Envelope used by the deployed code equals the transcribed forbidden set: %d / %d instructions' % (
        sum(1 for m in C['instructions'] if all(x['forbidden_used'] == m['forbidden_transcribed'] for x in res if x['item_id'] == m['item_id'] and x['forbidden_used'] is not None)), len(C['instructions'])),
        '', 'Cases not matching the pre-specified branch: %s' % (mism or 'none'),
        '', 'Scope: these exercised code branches only; not a validation of arbitrary negation interpretation or of complete system safety.']
    open(os.path.join(out, 'GT_RESULTS.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
