"""Separately identified external semantic-reference sensitivity for the A4 semantic comparison (protocol s.10.4 / s.13 item 5).

Rescores the frozen S/H records of the E7 items against an independent evaluator's judgments (C3 analysis output). It does not
change requests, routing, timings, the original key or any frozen file, and it reads only:
  - runs/{S,H}/run_primary/records.jsonl (frozen; hashes checked against results/RESULT_FREEZE.json);
  - 07_adjudication/analysis/per_cell_<evaluator>.csv (columns cell, sealed, evaluator).
Rules (same outcome semantics as the harness):
  - model/parser failure stays failure and is never correct;
  - a dispatched node is acceptable if it is in the evaluator's node set; if the evaluator gave no node, any node is incorrect executable;
  - an explicit clarification is correct only where the evaluator gave no node.
Item correctness = >= 2 of 3 seeds correct (as in the primary analysis).
  python3 -B sc_reference_sensitivity.py --per-cell <per_cell_x.csv> --out <dir>"""
import os, sys, json, csv, argparse, hashlib
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def nodes(s): return None if s == 'no_node' else {int(x) for x in s.split('|') if x.strip()}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--per-cell', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
    fz = json.load(open(os.path.join(ROOT, 'results', 'RESULT_FREEZE.json')))
    key = {}; sealed = {}
    for r in csv.DictReader(open(a.per_cell, encoding='utf-8')):
        key['E7-' + r['cell']] = nodes(r['evaluator']); sealed['E7-' + r['cell']] = nodes(r['sealed'])
    os.makedirs(a.out, exist_ok=True); summary = dict(script_sha256=sha(os.path.abspath(__file__)), per_cell_sha256=sha(a.per_cell),
                                                     result_freeze_sha256=sha(os.path.join(ROOT, 'results', 'RESULT_FREEZE.json')), conditions={})
    rows_out = []
    for c in 'SH':
        rp = 'runs/%s/run_primary/records.jsonl' % c
        if sha(os.path.join(ROOT, rp)) != fz['files'][rp]: sys.exit('records differ from the result freeze: ' + rp)
        R = [json.loads(l) for l in open(os.path.join(ROOT, rp), encoding='utf-8')]
        per = defaultdict(list)
        for r in R:
            if r['item_id'] not in key: continue
            k = key[r['item_id']]
            if r['outcome'] == 'model_or_parser_failure': cls = 'model_or_parser_failure'; ok = False
            elif r['outcome'] == 'clarification': cls = 'clarification'; ok = k is None
            else:
                n = r['node_id']; cls = 'acceptable' if (k is not None and n in k) else 'incorrect_executable'; ok = cls == 'acceptable'
            per[(r['item_id'], r['arm'])].append((ok, r['correct'], cls, r['outcome']))
        cond = {}
        for arm in 'ABC':
            items = sorted(i for (i, ar) in per if ar == arm)
            ev = {i: sum(x[0] for x in per[(i, arm)]) >= 2 for i in items}
            sk = {i: sum(x[1] for x in per[(i, arm)]) >= 2 for i in items}
            obs = Counter(x[2] for i in items for x in per[(i, arm)]); obs0 = Counter(x[3] for i in items for x in per[(i, arm)])
            cond[arm] = dict(e7_items=len(items), correct_items_sealed_key=sum(sk.values()), correct_items_evaluator_key=sum(ev.values()),
                             changed_items=sorted(i for i in items if ev[i] != sk[i]),
                             observations_sealed_key=dict(obs0), observations_evaluator_key=dict(obs))
            for i in items:
                rows_out.append(dict(condition=c, arm=arm, item_id=i, sealed_key='|'.join(map(str, sorted(sealed[i]))) if sealed[i] else 'no_node',
                                     evaluator_key='|'.join(map(str, sorted(key[i]))) if key[i] else 'no_node',
                                     correct_seeds_sealed=sum(x[1] for x in per[(i, arm)]), correct_seeds_evaluator=sum(x[0] for x in per[(i, arm)]),
                                     item_correct_sealed=sk[i], item_correct_evaluator=ev[i]))
        # paired arm contrasts under the evaluator key (correct-seed counts)
        cs = {(r['item_id'], r['arm']): r['correct_seeds_evaluator'] for r in rows_out if r['condition'] == c}
        its = sorted({i for (i, _) in cs})
        for x, y in (('A', 'B'), ('B', 'C'), ('A', 'C')):
            d = [cs[(i, x)] - cs[(i, y)] for i in its]
            cond['%s_vs_%s' % (x, y)] = dict(better=sum(v > 0 for v in d), worse=sum(v < 0 for v in d), tied=sum(v == 0 for v in d))
        summary['conditions'][c] = cond
    with open(os.path.join(a.out, 'reference_sensitivity_per_item.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0])); w.writeheader(); w.writerows(rows_out)
    json.dump(summary, open(os.path.join(a.out, 'REFERENCE_SENSITIVITY.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(summary['conditions'], indent=1))

if __name__ == '__main__':
    main()
