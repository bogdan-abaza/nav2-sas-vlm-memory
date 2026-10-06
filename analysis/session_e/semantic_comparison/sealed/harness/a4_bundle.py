"""A4 bundle constructor + gates 1 / 1a / 1b.  No model calls.  Run: python -B a4_bundle.py
Inputs: RC1.1 public data (PUBLIC_REPO_WORK/RC1) + frozen protected code copy (Outputs/data/session_e/day2_20260821/code).
Outputs: bundles/{S,H}/<item>.json + .prompt.txt, bundles/BUNDLES.sha256, gates/GATE_1*.{json,md}."""
import sys, os, json, glob, csv, hashlib, types, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); A4 = os.path.dirname(HERE)
ART = os.path.abspath(os.path.join(A4, '..', '..'))
RC = os.path.join(ART, 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1'); SE = os.path.join(RC, 'data', 'session_e')
CODE = os.path.join(ART, 'Review_14.05.2026', 'Outputs', 'data', 'session_e', 'day2_20260821', 'code')
FROZEN = {'vlm_navigator_node_v4_8_review.py': '1646542e', 'sas_l3a.py': '38b6910f', 'sas_text.py': 'aa211dc7',
          'negation_guard.py': '3b598ffe', 'executive_contract.py': '7683f52f', 'visual_confirmation_v2.py': '2c3a3ddb'}
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def shas(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
for f, h in FROZEN.items():
    if not sha(os.path.join(CODE, f)).startswith(h): sys.exit('FROZEN CODE MISMATCH ' + f)
# ---- ROS stubs (import only; nothing ROS is executed)
class _Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Any
for m in ['rclpy', 'rclpy.node', 'rclpy.action', 'rclpy.qos', 'geometry_msgs', 'geometry_msgs.msg', 'nav_msgs', 'nav_msgs.msg',
          'std_msgs', 'std_msgs.msg', 'nav2_msgs', 'nav2_msgs.action', 'sensor_msgs', 'sensor_msgs.msg']:
    mod = types.ModuleType(m); mod.__getattr__ = lambda n: _Any; sys.modules[m] = mod
sys.path.insert(0, CODE)
import vlm_navigator_node_v4_8_review as NAV
import negation_guard as NEG
import sas_l3a as L3A

DAYS = ('day1_20260820', 'day2_20260821')
NODES = {d: NAV.extract_graph_nodes(json.load(open(os.path.join(SE, d, 'config', 'route_graph_fiir.geojson')))) for d in DAYS}
STATIC = {d: NAV.load_static_objects(os.path.join(SE, d, 'config', 'semantic_objects_static_v2.geojson')) for d in DAYS}
def content_md5(d):
    c = {k: v for k, v in d.items() if k not in ('generated_at', 'content_md5')}
    return hashlib.md5(json.dumps(c, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
DIGEST_FILES = {'0fd61f9e82e8fe6991f0311014384e0c': os.path.join(SE, 'day1_20260820', 'config', 'memory_digest.json'),
                '5b3f14bc71a1896da5b29a4e655479fa': os.path.join(SE, 'day2_20260821', 'memory', 'digest_E4b', 'memory_digest.json')}
for k, p in DIGEST_FILES.items():
    if content_md5(json.load(open(p))) != k: sys.exit('DIGEST MISMATCH ' + p)
def digest_for(md5):
    if not md5: return None, None
    d, st = NAV.load_memory_digest(DIGEST_FILES[md5]); return d, DIGEST_FILES[md5]

# ---- records
REC = {}
for f in sorted(glob.glob(os.path.join(SE, 'day*', 'logs', 'audit_*.jsonl'))):
    day = f.split(os.sep)[-3]; run = os.path.basename(f)[6:-6]
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r.get('_type') == 'decision':
            r['_day'] = day; r['_run'] = run; r['_audit'] = os.path.relpath(f, RC)
            REC[(run, str(r['_seq']))] = r

OBJ = re.compile(r'^  - (.+?) "([^"]+)"(?: \[(.*?)\])? \((.*?)\) -> node (\d+) \(([\d.]+)m from robot\)$')
def parse_dynamic(prompt):
    yolo, dynconf = [], {}
    for ln in prompt.splitlines():
        m = OBJ.match(ln)
        if not m: continue
        cls, oid, attrs, stag, nn, dist = m.groups()
        if stag.startswith('yolo'):
            yolo.append(dict(class_name=cls, obj_id=oid, confidence=float(stag.split('conf=')[1].split(')')[0].split(',')[0]),
                             nearest_node_id=int(nn), printed_distance_m=float(dist)))
        mm = re.search(r'currently detected \(conf=([\d.]+)\)', stag)
        if mm and not stag.startswith('yolo'): dynconf[oid] = float(mm.group(1))
    return yolo, dynconf

PPOSE = re.compile(r'Robot pose: x=([-\d.]+), y=([-\d.]+), yaw=([-\d.]+) rad')
def _dists_ok(prompt, pose, day, nodes):
    """all static object distances printed in the prompt must be reproduced by this pose"""
    stat = {o['obj_id']: o for o in STATIC[day]}
    for ln in prompt.splitlines():
        m = OBJ.match(ln)
        if m and not m.group(4).startswith('yolo') and m.group(2) in stat:
            o = stat[m.group(2)]
            if f"{NAV.euclidean(pose['x'], pose['y'], o['x'], o['y']):.1f}" != m.group(6): return False
    return True
def pose_of(r):
    """Prompt-equivalent decision-time context pose. For records with a same-cycle prompt it is reconstructed from the prompt: the printed
    pose is rounded to 0.01 m, so we search the rounding cell for a point that reproduces every printed static
    distance (the prompt is same-cycle evidence; nothing else is inferred). Without a prompt: audit start_pose."""
    p = r['extra'].get('vlm_prompt_full')
    if p:
        m = PPOSE.search(p); px, py, pyaw = map(float, m.groups())
        day = r['_day']; nodes = NODES[day]; best = None; nfeas = 0
        steps = [i * 0.00025 for i in range(-20, 21)]
        for dx in steps:
            for dy in steps:
                cand = {'x': px + dx, 'y': py + dy, 'yaw': pyaw}
                if f"{cand['x']:.2f}" != m.group(1) or f"{cand['y']:.2f}" != m.group(2): continue
                if _dists_ok(p, cand, day, nodes):
                    nfeas += 1; d2 = dx * dx + dy * dy
                    if best is None or d2 < best[0]: best = (d2, cand)
        if best: return best[1], 'prompt_equivalent_decision_time_pose (feasible grid points in the 0.01 m rounding cell: %d; not a unique reconstruction of the AMCL state)' % nfeas
        return {'x': px, 'y': py, 'yaw': pyaw}, 'same_cycle_prompt_rounded (no feasible point)'
    sp = r['extra'].get('start_pose')
    if sp: return {'x': sp[0], 'y': sp[1], 'yaw': sp[2]}, 'audit.extra.start_pose'
    return None, 'missing'

def mapping(day, nodes, dynamic=None, dynconf=None, pose=None):
    m = NAV.compute_object_node_mapping(STATIC[day], nodes)
    for e in m:
        if dynconf and e['obj_id'] in dynconf: e['dynamic_confidence'] = dynconf[e['obj_id']]
    for y in (dynamic or []):
        # distance-preserving placeholder: the same-cycle pose is the item pose, so (px+d, py) reproduces the printed
        # distance exactly; it is NOT a claim about the object's position (L3a never reads it, see context audit)
        n = y['nearest_node_id']
        m.append(dict(obj_id=y['obj_id'], class_name=y['class_name'], source='yolo', confidence=y['confidence'], attributes={},
                      x=pose['x'] + y['printed_distance_m'], y=pose['y'], nearest_node_id=n, nearest_node_name=nodes[n]['name'],
                      placeholder_xy=True))
    return m

def negation(r, instr, nodes, mp, pose, m3_index, recompute):
    """Frozen safety envelope: forbidden_nodes = historical audit value (item-context field, identical across arms).
    recompute=True is used ONLY by GATE 1B to verify provenance; arms never re-estimate it."""
    ex = r['extra']
    _, _, det = L3A.try_deterministic_resolve(instr, nodes, mp, pose, m3_index)
    if det.get('escalation_reason') != 'negation_detected':
        return '', [], det
    markers = det.get('negation_markers', [])
    if recompute:
        forb, _ = NEG.identify_negated_targets(instr, nodes, mp, pose, m3_index, L3A.try_deterministic_resolve)
    else:
        forb = ex.get('negation_forbidden_nodes', []) or []
    intent = NEG.classify_negation_intent(instr)
    return NEG.build_negation_notice(instr, markers, forb, nodes, intent=intent), sorted(forb), det

def build(r, mode):
    day = r['_day']; nodes = NODES[day]; instr = r['instruction']; ex = r['extra']
    pose, pose_src = pose_of(r)
    digest, dpath = digest_for(ex.get('digest_content_md5'))
    prefix = NAV.build_memory_prefix(digest)
    m3_index = L3A.precompute_m3_tokens(digest) if digest else None
    if mode == 'H':
        yolo, dynconf = parse_dynamic(ex['vlm_prompt_full'])
        mp = mapping(day, nodes, yolo, dynconf, pose)
    else:
        yolo, dynconf = [], {}
        mp = mapping(day, nodes)
    notice, forb, det = negation(r, instr, nodes, mp, pose, m3_index, recompute=False)
    _, forb_check, _ = negation(r, instr, nodes, mp, pose, m3_index, recompute=True)
    prompt = NAV.build_vlm_prompt(instr, pose, nodes, mp, memory_prefix=prefix, negation_notice=notice)
    neg = det.get('escalation_reason') == 'negation_detected'
    cur = min(nodes, key=lambda n: NAV.euclidean(pose['x'], pose['y'], nodes[n]['x'], nodes[n]['y']))
    return dict(prompt=prompt, pose=pose, pose_source=pose_src, digest_path=dpath, forbidden=forb, yolo=yolo, dynconf=dynconf,
                notice=notice, intent=(NEG.classify_negation_intent(instr) if neg else None), current_node=cur,
                forbidden_recomputed_for_gate_1b=forb_check, negation_markers=det.get('negation_markers', []) if det.get('escalation_reason') == 'negation_detected' else [])

def project_S(p):
    """canonical S projection of a historical prompt: drop YOLO object lines, drop 'currently detected' marks,
    drop zone blocks that become empty."""
    out = []; lines = p.split('\n'); i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("ZONE '"):
            j = i + 1; body = []
            while j < len(lines) and lines[j] != '': body.append(lines[j]); j += 1
            kept = []
            for b in body:
                m = OBJ.match(b)
                if m and m.group(4).startswith('yolo'): continue
                kept.append(re.sub(r', currently detected \(conf=[\d.]+\)', '', b))
            if kept: out += [ln] + kept + ['']
            i = j + 1; continue
        out.append(ln); i += 1
    return '\n'.join(out)

def mission_prompt_file(r):
    img = (r.get('images') or {}).get('start')
    if not img: return None
    p = os.path.join(SE, r['_day'], 'logs', os.path.dirname(img), 'vlm_decision_prompt.txt')
    return p if os.path.isfile(p) else None

def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i, a[max(0, i-60):i+60], b[max(0, i-60):i+60]
    return min(len(a), len(b)), a[-80:], b[-80:]

if __name__ == '__main__':
    G = os.path.join(A4, 'gates'); os.makedirs(G, exist_ok=True)
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # ---------- GATE 1
    g1 = dict(gate='GATE_1_prompt_constructor', generated_utc=now, cases=[], copy_check=[])
    for k, r in sorted(REC.items()):
        hist = r['extra'].get('vlm_prompt_full')
        if hist is None: continue
        b = build(r, 'H'); ok = b['prompt'] == hist
        c = dict(record=k[0] + '#' + k[1], method=r['resolution_method'], pose_source=b['pose_source'], n_yolo=len(b['yolo']), pass_=ok)
        if not ok: c['first_diff'] = first_diff(b['prompt'], hist)
        g1['cases'].append(c)
        if r['resolution_method'] == 'L3b_vlm':
            mf = mission_prompt_file(r)
            g1['copy_check'].append(dict(record=c['record'], file=os.path.relpath(mf, RC) if mf else None,
                                         pass_=bool(mf) and open(mf, encoding='utf-8').read() == hist))
    g1['n'] = len(g1['cases']); g1['n_pass'] = sum(c['pass_'] for c in g1['cases'])
    g1['copy_n'] = len(g1['copy_check']); g1['copy_pass'] = sum(c['pass_'] for c in g1['copy_check'])
    g1['by_method'] = {m: [sum(c['pass_'] for c in g1['cases'] if c['method'] == m), sum(c['method'] == m for c in g1['cases'])]
                       for m in sorted({c['method'] for c in g1['cases']})}
    g1['verdict'] = 'PASS' if g1['n_pass'] == g1['n'] and g1['copy_pass'] == g1['copy_n'] else 'FAIL'
    json.dump(g1, open(os.path.join(G, 'GATE_1_prompt_constructor.json'), 'w'), indent=1, default=str)
    print('GATE 1', g1['verdict'], g1['n_pass'], '/', g1['n'], g1['by_method'], '| copies', g1['copy_pass'], '/', g1['copy_n'])
    for c in g1['cases']:
        if not c['pass_']: print('  FAIL', c['record'], c['method'], c['pose_source'], repr(c['first_diff'])[:400]); break

    # ---------- items, GATE 1a, GATE 1b, bundles
    items = list(csv.DictReader(open(os.path.join(A4, 'manifest_candidate', 'A4_items_candidate.csv'), encoding='utf-8')))
    B = os.path.join(A4, 'bundles')
    for c in ('S', 'H'): os.makedirs(os.path.join(B, c), exist_ok=True)
    def ref(p): return dict(path=os.path.relpath(p, RC).replace(os.sep, '/'), sha256=sha(p))
    g1a = dict(gate='GATE_1A_S_projection', generated_utc=now, cases=[], extended_105=[])
    g1b = dict(gate='GATE_1B_negation', generated_utc=now, cases=[])
    written = []
    for it in items:
        r = REC[(it['parent_run_id'], it['parent_record_seq'])]
        hist = r['extra'].get('vlm_prompt_full')
        hist_forb = sorted(r['extra'].get('negation_forbidden_nodes') or [])
        for cond in ('S', 'H'):
            if cond == 'H' and it['eligible_H'] != 'yes': continue
            b = build(r, cond)
            if cond == 'S' and hist is not None:
                exp = project_S(hist); ok = b['prompt'] == exp
                cc = dict(item=it['item_id'], pass_=ok)
                if not ok: cc['first_diff'] = first_diff(b['prompt'], exp)
                g1a['cases'].append(cc)
            if cond == 'S':
                g1b['cases'].append(dict(item=it['item_id'], frozen=hist_forb, recomputed_S=b['forbidden_recomputed_for_gate_1b'],
                                         pass_=b['forbidden_recomputed_for_gate_1b'] == hist_forb and b['forbidden'] == hist_forb))
            day = r['_day']; img = os.path.join(SE, it['image_start'][len('data/session_e/'):])
            pf = os.path.join(B, cond, it['item_id'] + '.prompt.txt')
            open(pf, 'w', encoding='utf-8', newline='').write(b['prompt'])
            bundle = dict(
                item_id=it['item_id'], condition=cond, stratum=it['stratum'], key_ref=it['key_ref'],
                data_reference='github.com/bogdan-abaza/nav2-sas-vlm-memory @ ras-revision-rc1.1 (cde9307)',
                parent=dict(run_id=it['parent_run_id'], record_seq=it['parent_record_seq'], audit=ref(os.path.join(RC, r['_audit'])),
                            timestamp_utc=it['parent_timestamp_utc'], platform=it['parent_platform']),
                instruction=r['instruction'], pose=b['pose'], pose_source=b['pose_source'],
                route_graph=ref(os.path.join(SE, day, 'config', 'route_graph_fiir.geojson')),
                static_objects=ref(os.path.join(SE, day, 'config', 'semantic_objects_static_v2.geojson')),
                memory_digest=(dict(ref(b['digest_path']), content_md5=r['extra'].get('digest_content_md5')) if b['digest_path'] else None),
                image_start=dict(ref(img), md5=it['image_start_md5']),
                dynamic=('empty (standardized post-reset state)' if cond == 'S' else
                         dict(source='same-cycle L3b prompt (audit.extra.vlm_prompt_full)', yolo_objects=b['yolo'],
                              static_currently_detected=b['dynconf'],
                              note='prompt-context replay: YOLO entries and printed same-cycle distances replayed from the archived prompt; per-cycle YOLO geometry was not archived and is not reconstructed')),
                current_node=dict(node_id=b['current_node'], derived_from='frozen context pose (this bundle: %s)' % b['pose_source'].split(' (')[0]),
                negation_envelope=dict(
                    active=bool(b['negation_markers']), negation_markers=b['negation_markers'], intent=b['intent'],
                    forbidden_nodes=b['forbidden'], rendered_notice=b['notice'], rendered_notice_sha256=shas(b['notice']),
                    provenance='frozen before arm execution; forbidden_nodes = parent audit negation_forbidden_nodes; markers and intent from the '
                               'frozen lexical negation detector; notice rendered once by the frozen build_negation_notice. Identical in arms A, B, C; '
                               'arms neither rebuild it nor run M3 to derive it. GATE 1B validates its provenance by recomputation under the historical digest.'),
                l3b_prompt=dict(file=os.path.basename(pf), sha256=shas(b['prompt']),
                                historical_reference=('byte-identical to audit prompt (gate 1)' if (cond == 'H' and hist) else
                                                      ('canonical S projection of audit prompt (gate 1a)' if hist else 'none: contract-only'))),
                frozen_code={f: sha(os.path.join(CODE, f)) for f in FROZEN})
            bf = os.path.join(B, cond, it['item_id'] + '.json')
            json.dump(bundle, open(bf, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
            written += [bf, pf]
    for k, r in sorted(REC.items()):
        hist = r['extra'].get('vlm_prompt_full')
        if hist is None: continue
        g1a['extended_105'].append(dict(record=k[0] + '#' + k[1], pass_=build(r, 'S')['prompt'] == project_S(hist)))
    for g in (g1a, g1b):
        g['n'] = len(g['cases']); g['n_pass'] = sum(c['pass_'] for c in g['cases'])
    g1a['extended_n'] = len(g1a['extended_105']); g1a['extended_pass'] = sum(c['pass_'] for c in g1a['extended_105'])
    g1a['verdict'] = 'PASS' if g1a['n_pass'] == g1a['n'] else 'FAIL'
    g1b['verdict'] = 'PASS' if g1b['n_pass'] == g1b['n'] else 'FAIL'
    json.dump(g1a, open(os.path.join(G, 'GATE_1A_S_projection.json'), 'w'), indent=1, default=str)
    json.dump(g1b, open(os.path.join(G, 'GATE_1B_negation.json'), 'w'), indent=1, default=str)
    with open(os.path.join(B, 'BUNDLES.sha256'), 'w') as f:
        for p in sorted(written): f.write('%s  %s\n' % (sha(p), os.path.relpath(p, B).replace(os.sep, '/')))
    print('GATE 1a', g1a['verdict'], g1a['n_pass'], '/', g1a['n'], '| extended', g1a['extended_pass'], '/', g1a['extended_n'])
    print('GATE 1b', g1b['verdict'], g1b['n_pass'], '/', g1b['n'])
    for c in g1a['cases'] + g1b['cases']:
        if not c['pass_']: print('  FAIL', c)
    print('bundles', len(written) // 2)
