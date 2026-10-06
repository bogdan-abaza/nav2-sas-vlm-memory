"""Analysis of the A4 semantic comparison (protocol a4_semantic_comparison_20261005, s.10). Data only; no conclusions.
  python3 -B sc_analyze.py --run-S ../runs/S/run_<tag> [--run-H ../runs/H/run_<tag>] [--out ../results]
Refuses runs that are incomplete, invalid, not referencing the current input seal (seal/SEAL.json), or whose schedule / bundles / harness differ from it.
Unit: instruction-context item; seeds are repeated observations. Bootstrap: stratified paired item bootstrap, 10,000 resamples, seed 20261005."""
import os, sys, json, csv, math, random, argparse, hashlib, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sc_schedule as SCH
ARMS = 'ABC'; STRATA = ['FAMILIAR_ASSOCIATION', 'UNSEEN_FORMULATION', 'CLARIFICATION_REQUIRED']
CONTRASTS = [('A', 'B'), ('B', 'C'), ('A', 'C')]
CLASSES = ['acceptable', 'incorrect_executable', 'clarification', 'model_or_parser_failure']
NBOOT, BSEED = 10000, 20261005
STAGES = ['resolver_ns', 'image_ns', 'prompt_ns', 'serialize_ns', 'api_ns', 'decode_ns', 'parse_ns', 'guard_validation_ns', 'decision_ns']
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def NA(x): return 'not applicable' if x is None else x
def frac(k, n): return None if n == 0 else k / n
def wilson(k, n, z=1.959963984540054):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))
def sign_test(better, worse):
    n = better + worse
    if n == 0: return None
    k = min(better, worse); p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)
def q(xs, p):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * p; f = math.floor(k); c = math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)
def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs: return dict(n=0, median=None, q1=None, q3=None, mean=None, min=None, max=None)
    return dict(n=len(xs), median=round(q(xs, .5), 3), q1=round(q(xs, .25), 3), q3=round(q(xs, .75), 3), mean=round(sum(xs) / len(xs), 3), min=round(min(xs), 3), max=round(max(xs), 3))

def load_run(d, cond):
    H = json.load(open(os.path.join(d, 'RUN_HEADER.json'))); R = [json.loads(l) for l in open(os.path.join(d, 'records.jsonl'), encoding='utf-8')]
    probs = []
    if not H.get('completed') or not H.get('valid'): probs.append('run not completed/valid')
    if H['condition'] != cond: probs.append('condition mismatch')
    sched = SCH.schedule(cond)
    if sha(os.path.join(ROOT, 'schedule', 'SCHEDULE_%s.csv' % cond)) != H['schedule_sha256']: probs.append('schedule hash differs from header')
    if sha(os.path.join(ROOT, 'bundles', 'BUNDLES.sha256')) != H['bundles_sha256']: probs.append('bundles hash differs from header')
    cur = {f: sha(os.path.join(HERE, f)) for f in H['harness_sha256']}
    if cur.get('sc_harness.py') != H['harness_sha256'].get('sc_harness.py'): probs.append('sc_harness.py differs from header')
    seal = os.path.join(ROOT, 'seal', 'SEAL.json')
    if not os.path.exists(seal): probs.append('input seal missing')
    else:
        if H.get('seal_sha256_before_measurement') != sha(seal) or H.get('seal_sha256_before_qualification') != sha(seal): probs.append('run header does not reference the current SEAL.json')
        S = json.load(open(seal))['files']
        for k, v in [('harness/sc_harness.py', H['harness_sha256'].get('sc_harness.py')), ('schedule/SCHEDULE_%s.csv' % cond, H['schedule_sha256']), ('bundles/BUNDLES.sha256', H['bundles_sha256'])]:
            if S.get(k) != v: probs.append('%s differs from SEAL.json' % k)
    keys = [(r['item_id'], r['arm'], int(r['seed_base'])) for r in R]
    if sorted(keys) != sorted((s['item_id'], s['arm'], s['seed_base']) for s in sched): probs.append('records != schedule keys')
    if len(set(keys)) != len(keys): probs.append('duplicate records')
    sd = {(s['item_id'], s['arm'], s['seed_base']): s['seed'] for s in sched}
    if any(r['seed'] != sd[(r['item_id'], r['arm'], int(r['seed_base']))] for r in R): probs.append('seed mismatch')
    if any('runtime_prep' not in r for r in R): probs.append('missing runtime preparation evidence')
    if any(r['path'] == 'L3b' and not r.get('api_envelope') for r in R): probs.append('missing API envelope')
    return H, R, probs

def per_item(R):
    I = defaultdict(lambda: defaultdict(list))
    for r in R: I[r['item_id']][r['arm']].append(r)
    return I
def item_stratum(I, iid): return next(iter(I[iid].values()))[0]['stratum']
def correct_seeds(I, iid, arm): return sum(1 for r in I[iid][arm] if r['correct'])
def vlm_calls(I, iid, arm): return sum(1 for r in I[iid][arm] if r['path'] == 'L3b')
def item_median_ms(I, iid, arm, field='decision_ns'):
    xs = [r[field] for r in I[iid][arm] if r.get(field) is not None]
    return q(xs, .5) / 1e6 if xs else None

def bootstrap(items_by_stratum, stat, rng):
    """stratified paired item bootstrap: resample items with replacement within each stratum; each item keeps all its arm/seed records"""
    out = []
    for _ in range(NBOOT):
        sample = [rng.choice(its) for its in items_by_stratum.values() for _ in its]
        v = stat(sample)
        if v is not None: out.append(v)
    return (round(q(out, .025), 4), round(q(out, .975), 4)) if out else (None, None)

def analyze(cond, R):
    I = per_item(R); rng = random.Random(BSEED); T = defaultdict(list)
    scopes = STRATA + ['ALL']
    def its(scope): return sorted(i for i in I if scope == 'ALL' or item_stratum(I, i) == scope)
    def strat(items):
        d = defaultdict(list)
        for i in items: d[item_stratum(I, i)].append(i)
        return d
    for scope in scopes:
        items = its(scope)
        if not items: continue
        for arm in ARMS:
            obs = [r for i in items for r in I[i][arm]]
            c = Counter(r['outcome'] for r in obs); ncorr = sum(1 for i in items if correct_seeds(I, i, arm) >= 2)
            wex = [r for r in obs if r['outcome'] == 'incorrect_executable']
            l3a = [r for r in obs if r['path'] == 'L3a']; l3a_wrong = [r for r in l3a if r['outcome'] == 'incorrect_executable']
            clar_obs = [r for r in obs if r['stratum'] == 'CLARIFICATION_REQUIRED']
            T['outcomes'].append(dict(condition=cond, scope=scope, arm=arm, items=len(items), observations=len(obs), **{k: c[k] for k in CLASSES},
                                      items_correct=ncorr, item_correctness=round(ncorr / len(items), 4), wilson95=wilson(ncorr, len(items)),
                                      wrong_exec_obs=len(wex), wrong_exec_items_any=len({r['item_id'] for r in wex}),
                                      wrong_exec_items_2of3=sum(1 for i in items if sum(1 for r in I[i][arm] if r['outcome'] == 'incorrect_executable') >= 2),
                                      parser_failure_items=len({r['item_id'] for r in obs if r['outcome'] == 'model_or_parser_failure'}),
                                      clarification_mechanisms=dict(Counter(r['outcome_sub'].split(':')[0] for r in obs if r['outcome'] == 'clarification'))))
            T['routing'].append(dict(condition=cond, scope=scope, arm=arm, observations=len(obs), vlm_calls=sum(1 for r in obs if r['path'] == 'L3b'),
                                     vlm_items=len({r['item_id'] for r in obs if r['path'] == 'L3b'}), l3a_resolved=len(l3a),
                                     l3a_coverage=NA(frac(len(l3a), len(obs))), resolution_steps=dict(Counter(str(r.get('resolution_step')) for r in l3a)),
                                     fast_path_error_incidence=NA(frac(len(l3a_wrong), len(obs))), fast_path_conditional_error=NA(frac(len(l3a_wrong), len(l3a))),
                                     l3a_error_on_clarification_required=NA(frac(sum(1 for r in l3a_wrong if r['stratum'] == 'CLARIFICATION_REQUIRED'), len(clar_obs))) if clar_obs else 'not applicable',
                                     fast_path_counts='%d/%d/%d' % (len(l3a_wrong), len(l3a), len(obs))))
            same_cls = sum(1 for i in items if len({r['outcome'] for r in I[i][arm]}) == 1); same_node = sum(1 for i in items if len({r['node_id'] for r in I[i][arm]}) == 1)
            T['seed_agreement'].append(dict(condition=cond, scope=scope, arm=arm, items=len(items), same_class_3of3=same_cls, same_node_3of3=same_node))
            for f in ('decision_ns', 'resolver_ns'):
                if f == 'resolver_ns' and arm == 'C':
                    T['timing'].append(dict(condition=cond, scope=scope, arm=arm, measure='resolver_ms', population='all', **{k: 'not applicable' for k in ('n', 'median', 'q1', 'q3', 'mean', 'min', 'max')})); continue
                T['timing'].append(dict(condition=cond, scope=scope, arm=arm, measure=f.replace('_ns', '_ms'), population='all observations', **summ([r[f] / 1e6 for r in obs if r.get(f) is not None])))
                T['timing'].append(dict(condition=cond, scope=scope, arm=arm, measure=f.replace('_ns', '_ms'), population='item medians', **summ([item_median_ms(I, i, arm, f) for i in items])))
            T['timing'].append(dict(condition=cond, scope=scope, arm=arm, measure='decision_ms', population='VLM path only (conditional, descriptive)', **summ([r['decision_ns'] / 1e6 for r in obs if r['path'] == 'L3b'])))
            for f in STAGES[1:-1]:
                T['stages'].append(dict(condition=cond, scope=scope, arm=arm, stage=f.replace('_ns', '_ms'), **summ([r[f] / 1e6 for r in obs if r.get(f) is not None])))
            api = [r for r in obs if r['path'] == 'L3b']
            T['api'].append(dict(condition=cond, scope=scope, arm=arm, vlm_calls=len(api),
                                 prompt_eval_ms=summ([r['api_prompt_eval_duration'] / 1e6 for r in api if isinstance(r.get('api_prompt_eval_duration'), int)]),
                                 total_duration_ms=summ([r['api_total_duration'] / 1e6 for r in api if isinstance(r.get('api_total_duration'), int)]),
                                 load_duration_ms=summ([r['api_load_duration'] / 1e6 for r in api if isinstance(r.get('api_load_duration'), int)]),
                                 prompt_eval_count=summ([r['api_prompt_eval_count'] for r in api if isinstance(r.get('api_prompt_eval_count'), int)]),
                                 eval_count=summ([r['api_eval_count'] for r in api if isinstance(r.get('api_eval_count'), int)]),
                                 cached_count_field=dict(Counter(str(r.get('api_prompt_eval_cached_count')) for r in api))))
        for x, y in CONTRASTS:
            d = [correct_seeds(I, i, x) - correct_seeds(I, i, y) for i in items]
            b, w = sum(1 for v in d if v > 0), sum(1 for v in d if v < 0)
            ic = lambda s: (sum(1 for i in s if correct_seeds(I, i, x) >= 2) - sum(1 for i in s if correct_seeds(I, i, y) >= 2)) / len(s)
            vc = lambda s: (sum(vlm_calls(I, i, x) for i in s) - sum(vlm_calls(I, i, y) for i in s)) / (3 * len(s))
            S_ = strat(items)
            T['contrasts'].append(dict(condition=cond, scope=scope, contrast='%s_vs_%s' % (x, y), items=len(items), better=b, worse=w, tied=len(items) - b - w,
                                       mean_diff_correct_seeds=round(sum(d) / len(d), 4), sign_test_p_descriptive=sign_test(b, w),
                                       diff_item_correctness=round(ic(items), 4), diff_item_correctness_boot95=bootstrap(S_, ic, rng),
                                       diff_vlm_call_fraction=round(vc(items), 4), diff_vlm_call_fraction_boot95=bootstrap(S_, vc, rng),
                                       wrong_exec_obs='%d vs %d' % tuple(sum(1 for i in items for r in I[i][a] if r['outcome'] == 'incorrect_executable') for a in (x, y)),
                                       wrong_exec_items='%d vs %d' % tuple(len({i for i in items for r in I[i][a] if r['outcome'] == 'incorrect_executable'}) for a in (x, y))))
            pd = [(item_median_ms(I, i, x), item_median_ms(I, i, y)) for i in items]
            diffs = [a_ - b_ for a_, b_ in pd if a_ is not None and b_ is not None]
            ratios = [b_ / a_ for a_, b_ in pd if a_ and b_ is not None and a_ > 0]
            md = lambda s: q([item_median_ms(I, i, x) - item_median_ms(I, i, y) for i in s], .5)
            mr = lambda s: q([item_median_ms(I, i, y) / item_median_ms(I, i, x) for i in s if item_median_ms(I, i, x)], .5)
            T['timing_contrasts'].append(dict(condition=cond, scope=scope, contrast='%s_vs_%s' % (x, y), items=len(items),
                                              median_paired_diff_ms='%s - %s' % (x, y), value_diff=round(q(diffs, .5), 3) if diffs else None, diff_boot95=bootstrap(S_, md, rng),
                                              mean_paired_diff_ms=round(sum(diffs) / len(diffs), 3) if diffs else None,
                                              ratio_name='%s/%s (>1 means %s faster)' % (y, x, x), median_paired_ratio=round(q(ratios, .5), 4) if ratios else None,
                                              ratio_boot95=bootstrap(S_, mr, rng), undefined_ratios=len(items) - len(ratios)))
    per = []
    for i in sorted(I):
        for arm in ARMS:
            rs = sorted(I[i][arm], key=lambda r: r['seed_base'])
            per.append(dict(condition=cond, item_id=i, stratum=item_stratum(I, i), arm=arm, correct_seeds=correct_seeds(I, i, arm), outcomes='|'.join(r['outcome'] for r in rs),
                            nodes='|'.join(str(r['node_id']) for r in rs), paths='|'.join(r['path'] for r in rs), median_decision_ms=round(item_median_ms(I, i, arm), 3),
                            median_resolver_ms=round(item_median_ms(I, i, arm, 'resolver_ns'), 6) if arm != 'C' else 'not applicable'))
    T['per_item'] = per
    T['positions'] = [dict(condition=cond, arm=arm, position=p, observations=sum(1 for r in R if r['arm'] == arm and r.get('position') == p)) for arm in ARMS for p in (0, 1, 2)]
    T['timeline'] = [dict(condition=cond, seq=r.get('seq'), arm=r['arm'], position=r.get('position'), item_id=r['item_id'], path=r['path'],
                          prep_utc=(r.get('runtime_prep') or {}).get('t_utc'), decision_ms=round(r['decision_ns'] / 1e6, 3),
                          api_ms=round(r['api_ns'] / 1e6, 3) if r.get('api_ns') is not None else None) for r in sorted(R, key=lambda r: r.get('seq', 0))]
    return T

def compare_sh(RS, RH):
    IS, IH = per_item(RS), per_item(RH); common = sorted(set(IS) & set(IH)); out = []
    for scope in ['UNSEEN_FORMULATION', 'CLARIFICATION_REQUIRED', 'ALL']:
        items = [i for i in common if scope == 'ALL' or item_stratum(IS, i) == scope]
        for arm in ARMS:
            cs = {i: correct_seeds(IS, i, arm) >= 2 for i in items}; ch = {i: correct_seeds(IH, i, arm) >= 2 for i in items}
            node_change = sum(1 for i in items for a, b in zip(sorted(IS[i][arm], key=lambda r: r['seed_base']), sorted(IH[i][arm], key=lambda r: r['seed_base'])) if a['node_id'] != b['node_id'])
            out.append(dict(scope=scope, arm=arm, items=len(items), correct_S=sum(cs.values()), correct_H=sum(ch.values()), items_correctness_changed=sum(1 for i in items if cs[i] != ch[i]),
                            observations_node_changed=node_change, outcomes_S=dict(Counter(r['outcome'] for i in items for r in IS[i][arm])),
                            outcomes_H=dict(Counter(r['outcome'] for i in items for r in IH[i][arm])),
                            vlm_calls_S=sum(vlm_calls(IS, i, arm) for i in items), vlm_calls_H=sum(vlm_calls(IH, i, arm) for i in items)))
        for x, y in CONTRASTS:
            for cond, I in (('S', IS), ('H', IH)):
                d = [correct_seeds(I, i, x) - correct_seeds(I, i, y) for i in items]
                out.append(dict(scope=scope, contrast='%s_vs_%s' % (x, y), condition=cond, better=sum(1 for v in d if v > 0), worse=sum(1 for v in d if v < 0), tied=sum(1 for v in d if v == 0)))
    return out

def write(T, d, cond, header, probs):
    os.makedirs(d, exist_ok=True)
    for k, rows in T.items():
        if not rows: continue
        with open(os.path.join(d, '%s.csv' % k), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(dict(condition=cond, run=header.get('run_tag'), header_started=header.get('started_utc'), header_ended=header.get('ended_utc'),
                   seal_sha256=header.get('seal_sha256_before_measurement'), qualification=header.get('qualification'), thermal=header.get('thermal'),
                   validity_problems=probs, bootstrap=dict(resamples=NBOOT, seed=BSEED, scheme='stratified paired item bootstrap'),
                   files={f: sha(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith('.csv')}), open(os.path.join(d, 'ANALYSIS_META.json'), 'w'), indent=1, default=str)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--run-S', required=True); ap.add_argument('--run-H'); ap.add_argument('--out', default=os.path.join(ROOT, 'results'))
    ap.add_argument('--allow-invalid', action='store_true', help='tests only')
    a = ap.parse_args(); runs = {}
    for cond, p in (('S', a.run_S), ('H', a.run_H)):
        if not p: continue
        H, R, probs = load_run(p, cond)
        if probs and not a.allow_invalid: sys.exit('%s run invalid: %s' % (cond, probs))
        runs[cond] = R; T = analyze(cond, R); write(T, os.path.join(a.out, cond), cond, H, probs)
        print(cond, 'analysis written', len(R), 'records; validity problems:', probs or 'none')
    if 'S' in runs and 'H' in runs:
        rows = compare_sh(runs['S'], runs['H']); d = os.path.join(a.out, 'S_vs_H'); os.makedirs(d, exist_ok=True)
        json.dump(rows, open(os.path.join(d, 'S_vs_H.json'), 'w'), indent=1); print('S vs H written', len(rows), 'rows')
