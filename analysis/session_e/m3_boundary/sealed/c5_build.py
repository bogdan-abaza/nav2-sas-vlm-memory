"""C5 construction: exact-fraction scoring of authoring batches and band assignment (C5_CONSTRUCTION_RULE.md).
Computes ONLY token-set fractions (top / runner-up over distinct nodes, gap) with the frozen sas_text.tokenize.
Never computes EXACT or JACCARD matcher decisions, never reads labels for selection.
Usage: python3 -B c5_build.py batch_001.csv [batch_002.csv ...]   (batches in authorship order; each must match its .sha256)"""
import csv, json, sys, os, hashlib, importlib.util
from fractions import Fraction as F
HERE = os.path.dirname(os.path.abspath(__file__))
RC1 = os.path.join(HERE, '..', '..', 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1', 'analysis', 'session_e', 'A2_m3_sensitivity', 'inputs')
EXP = {'sas_text.py': 'aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1',
       'memory_digest_standard.json': '1fe64ed09a96343bac5abd0cae476545bd0100dd496dc25122b1ca4a2cd7c3ab'}
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
for f, h in EXP.items(): assert sha(os.path.join(RC1, f)) == h, 'RC1.1 input hash mismatch: ' + f
assert sha(os.path.join(HERE, 'C5_CONSTRUCTION_RULE.md')) == open(os.path.join(HERE, 'C5_CONSTRUCTION_RULE.sha256')).read().split()[0]
assert sha(os.path.join(HERE, 'challenge_index_C.json')) == open(os.path.join(HERE, 'challenge_index_C.sha256')).read().split()[0]
spec = importlib.util.spec_from_file_location('sas_text', os.path.join(RC1, 'sas_text.py')); st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
def index(path, tag):
    d = json.load(open(path, encoding='utf-8')); out = []
    for i, p in enumerate(d['l3a_promotions_ready']):
        for ex in p['instruction_examples']:
            t = st.tokenize(ex)
            if t: out.append(dict(node=int(p['node_id']), ex=ex, tok=t, ref='%s:%s' % (tag, p.get('pair', i))))
    return out
H = index(os.path.join(RC1, 'memory_digest_standard.json'), 'H'); C = index(os.path.join(HERE, 'challenge_index_C.json'), 'C')
HREF = {'h14': 0, 'h0a': 1, 'h4': 2, 'h8': 3, 'h0b': 4, 'h9': 5}          # authoring tags -> position in H
def fr(a, b): return F(len(a & b), len(a | b)) if (a | b) else F(0)
def rank(tok, idx):
    best = {}
    for e in idx:                                   # per-node maximum, first-appearance order (as rank_instruction)
        s = fr(tok, e['tok'])
        if e['node'] not in best or s > best[e['node']][0]: best[e['node']] = (s, e['ex'])
    r = sorted(best.items(), key=lambda kv: -kv[1][0])
    return r
BANDS12 = [('J=1', lambda t: t == 1), ('(3/4,1)', lambda t: F(3, 4) < t < 1), ('J=3/4', lambda t: t == F(3, 4)), ('[1/2,3/4)', lambda t: F(1, 2) <= t < F(3, 4))]
BANDS3 = [('gap<1/10', lambda g: g < F(1, 10)), ('gap=1/10', lambda g: g == F(1, 10)), ('gap(1/10,1/4]', lambda g: F(1, 10) < g <= F(1, 4))]
QUOTA = {('F1', 'J=1'): 3, ('F1', '(3/4,1)'): 4, ('F1', 'J=3/4'): 3, ('F1', '[1/2,3/4)'): 6,
         ('F2', 'J=1'): 3, ('F2', '(3/4,1)'): 4, ('F2', 'J=3/4'): 3, ('F2', '[1/2,3/4)'): 6,
         ('F3', 'gap<1/10'): 6, ('F3', 'gap=1/10'): 4, ('F3', 'gap(1/10,1/4]'): 6}
log, filled, per_ex = [], {k: 0 for k in QUOTA}, {}
for b in sys.argv[1:]:
    bp = os.path.join(HERE, 'authoring', b)
    assert sha(bp) == open(bp.replace('.csv', '.sha256')).read().split()[0], 'batch hash mismatch ' + b
    for r in csv.DictReader(open(bp, encoding='utf-8')):
        fam, ins = r['family'], r['instruction']; tok = st.tokenize(ins); neg = st.detect_negation(ins)[0]
        idx = H if fam in ('F1', 'F2') else H + C
        rk = rank(tok, idx); (tn, (ts, tex)) = rk[0]; (rn, (rs, rex)) = rk[1] if len(rk) > 1 else (None, (F(0), None))
        gap = ts - rs
        ident = any(st.normalize(ins) == st.normalize(e['ex']) for e in idx)
        rel = r['related']; jrel = fr(tok, H[HREF[rel]]['tok']) if rel in HREF else None
        band, status = None, 'unused'
        if neg: status = 'excluded_negation'
        elif ident and fam in ('F1', 'F2'): status = 'excluded_identical_after_normalize'
        else:
            if fam in ('F1', 'F2'): band = next((n for n, f in BANDS12 if f(ts)), 'out_of_bands')
            else: band = next((n for n, f in BANDS3 if f(gap)), 'out_of_bands') if ts >= F(3, 4) else 'top<3/4'
            k = (fam, band)
            if k in QUOTA:
                if filled[k] >= QUOTA[k]: status = 'surplus'
                elif fam in ('F1', 'F2') and per_ex.get((fam, rel), 0) >= 4: status = 'surplus_spread_limit'
                else: status = 'selected'; filled[k] += 1; per_ex[(fam, rel)] = per_ex.get((fam, rel), 0) + 1
        log.append(dict(batch=b, cand_id=r['cand_id'], family=fam, instruction=ins, related=rel, n_tokens=len(tok), tokens=' '.join(sorted(tok)),
                        negation=neg, identical_after_normalize=ident,
                        top_node=tn, top_num=ts.numerator, top_den=ts.denominator, top_example=tex,
                        runner_node=rn, runner_num=rs.numerator, runner_den=rs.denominator,
                        gap_num=gap.numerator, gap_den=gap.denominator,
                        j_related=('%d/%d' % (jrel.numerator, jrel.denominator)) if jrel is not None else '',
                        band=band, status=status))
# ---- Amendment 01 (C5_AMENDMENT_01_20261005.md): coverage repair after chronological filling
def covered(rows): return {r['related'] for r in rows if r['status'] == 'selected' and r['family'] in ('F1', 'F2') and r['related'] in HREF}
for ex in [e for e in HREF if e not in covered(log)]:
    cand = next((r for r in log if r['related'] == ex and r['family'] in ('F1', 'F2') and (r['family'], r['band']) in QUOTA
                 and r['status'] in ('surplus', 'surplus_spread_limit')), None)
    if cand is None: print('coverage repair: no eligible candidate for', ex); continue
    same = [r for r in log if r['status'] == 'selected' and r['family'] == cand['family'] and r['band'] == cand['band']]
    for out in reversed(same):
        others = [r for r in log if r is not out and r['status'] == 'selected']
        if out['related'] in covered(others) and sum(1 for r in others if r['family'] == cand['family'] and r['related'] == ex) < 4:
            out['status'] = 'replaced_coverage_repair'; cand['status'] = 'selected'
            print('coverage repair: %s -> %s (%s, %s, %s)' % (out['cand_id'], cand['cand_id'], cand['family'], cand['band'], ex)); break
    else: print('coverage repair: no replaceable item for', ex)
with open(os.path.join(HERE, 'candidates_log.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(log[0])); w.writeheader(); w.writerows(log)
fin = {k: sum(1 for r in log if r['status'] == 'selected' and (r['family'], r['band']) == k) for k in QUOTA}
print('filled:'); [print('  %-4s %-14s %d/%d' % (k[0], k[1], fin[k], QUOTA[k])) for k in QUOTA]
print('selected total:', sum(fin.values()))
print('H examples covered in F1+F2:', sorted(covered(log)), 'missing:', sorted(set(HREF) - covered(log)))
