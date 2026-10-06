"""C5 M3 Decision-Boundary Challenge — matcher comparison on the sealed set (C5_CONSTRUCTION_RULE.md §2, §6).
Refuses to run unless C5_SEAL.json exists and every sealed file still matches. Uses the frozen public A2 reimplementation
(build_index / rank_instruction / classify) and sas_text unchanged, with their own floating-point arithmetic.
Writes results/ (per_item.csv, summary.csv, RESULTS_C5.md). Data only, no conclusions."""
import csv, json, os, sys, hashlib, importlib.util, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
A2 = os.path.join(HERE, '..', '..', 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1', 'analysis', 'session_e', 'A2_m3_sensitivity')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
SP = os.path.join(HERE, 'C5_SEAL.json')
if not os.path.exists(SP): sys.exit('C5_SEAL.json missing: run c5_seal.py first')
seal = json.load(open(SP)); bad = [f for f, h in seal['files'].items() if sha(os.path.join(HERE, f)) != h]
bad += [f for f, h in seal['rc1_inputs'].items() if sha(os.path.join(A2, f)) != h]
if bad: sys.exit('sealed files changed: %s' % bad)
if os.path.exists(os.path.join(HERE, 'results', 'per_item.csv')): sys.exit('results/ already written; never overwritten')
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st = load('sas_text', os.path.join(A2, 'inputs', 'sas_text.py')); A = load('a2', os.path.join(A2, 'analyze_A2_m3_sensitivity.py'))
Hd = json.load(open(os.path.join(A2, 'inputs', 'memory_digest_standard.json'), encoding='utf-8'))
Cd = json.load(open(os.path.join(HERE, 'challenge_index_C.json'), encoding='utf-8'))
IDX = {'H': A.build_index(Hd, st), 'H+C': A.build_index({'l3a_promotions_ready': Hd['l3a_promotions_ready'] + Cd['l3a_promotions_ready']}, st)}
EX = {'H': [(p['node_id'], e) for p in Hd['l3a_promotions_ready'] for e in p['instruction_examples']]}
EX['H+C'] = EX['H'] + [(p['node_id'], e) for p in Cd['l3a_promotions_ready'] for e in p['instruction_examples']]
def exact(text, ix):
    if st.detect_negation(text)[0]: return 'abstain_negation', None
    nodes = {int(n) for n, e in EX[ix] if st.normalize(e) == st.normalize(text)}
    if len(nodes) == 1: return 'accept', nodes.pop()
    return ('abstain_ambiguous_exact' if nodes else 'abstain_no_exact'), None
def outcome(label, status, node):
    if status != 'accept': return 'correct_abstention' if label == 'abstain' else 'abstention'
    return 'correct_accept' if label == 'node:%d' % node else 'wrong_accept'
MATCHERS = [('EXACT', None, None), ('JACCARD_0.75_0.10', 0.75, 0.10), ('JACCARD_0.60_0.10_ref', 0.60, 0.10)]
items = list(csv.DictReader(open(os.path.join(HERE, 'items.csv'), encoding='utf-8'))); rows = []
for it in items:
    rk = A.rank_instruction(it['instruction'], IDX[it['index']], st)
    for m, thr, mar in MATCHERS:
        s, n = exact(it['instruction'], it['index']) if m == 'EXACT' else A.classify(rk, thr, mar)
        rows.append(dict(item_id=it['item_id'], family=it['family'], band=it['band'], label_final=it['label_final'], matcher=m, status=s,
                         node='' if n is None else n, outcome=outcome(it['label_final'], s, n),
                         float_top=rk['top_score'], float_runner=rk['runner_up_score'], float_gap=rk['gap'], exact_gap=it['gap'], exact_top=it['top'],
                         n3_index_note='N3' if it['related'] == 'C:N3' else ''))
os.makedirs(os.path.join(HERE, 'results'))
with open(os.path.join(HERE, 'results', 'per_item.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
OUT = ['correct_accept', 'wrong_accept', 'abstention', 'correct_abstention']
summ = []
for m, _, _ in MATCHERS:
    for fam in ['F1', 'F2', 'F3', 'ALL']:
        sub = [r for r in rows if r['matcher'] == m and (fam == 'ALL' or r['family'] == fam)]
        c = Counter(r['outcome'] for r in sub); summ.append(dict(matcher=m, family=fam, n=len(sub), **{o: c[o] for o in OUT}))
with open(os.path.join(HERE, 'results', 'summary.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
fl = [r for r in rows if r['matcher'] == 'JACCARD_0.75_0.10' and r['band'] in ('gap=1/10', 'J=3/4')]
L = ['# C5 — M3 Decision-Boundary Challenge: results (data only)', '', 'Run %s · sealed set C5_SEAL.json sha256 %s' % (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), sha(SP)), '',
     'Diagnostic set constructed with access to similarity scores; labels assigned before each candidate was scored and reviewed on sheets without scores or decisions. Reported separately from A4; not pooled.', '',
     '| Matcher | Family | n | correct accept | wrong accept | abstention (label = node) | correct abstention (label = abstain) |', '|---|---|---|---|---|---|---|']
L += ['| %s | %s | %d | %d | %d | %d | %d |' % (s['matcher'], s['family'], s['n'], s['correct_accept'], s['wrong_accept'], s['abstention'], s['correct_abstention']) for s in summ]
L += ['', '## Boundary bands — floating-point check (JACCARD 0.75/0.10, as implemented)', '', '| Item | Band | exact top | float top | exact gap | float gap | status |', '|---|---|---|---|---|---|---|']
L += ['| %s | %s | %s | %r | %s | %r | %s |' % (r['item_id'], r['band'], r['exact_top'], r['float_top'], r['exact_gap'], r['float_gap'], r['status']) for r in fl]
L += ['', 'N3 items (C053, C054) use a challenge-index association whose node is semantically questionable (Amendment 02, B2): flagged in per_item.csv (`n3_index_note`).']
open(os.path.join(HERE, 'results', 'RESULTS_C5.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('C5 results written:', len(rows), 'rows')
