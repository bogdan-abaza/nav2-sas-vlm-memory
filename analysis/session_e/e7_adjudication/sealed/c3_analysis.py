#!/usr/bin/env python3
"""
c3_analysis.py -- prespecified analysis of the blind E7 adjudication (post-hoc sensitivity).

Fixed before any response is received; sealed together with the packet. Descriptive only.
The sealed E7 result (17/28) remains the primary historical result; this analysis never replaces it.

Usage:
  python3 -B c3_analysis.py --responses returned/<evaluator>/response_form.csv [--responses ...] --out analysis/
  python3 -B c3_analysis.py --self-test
Per evaluator:
  1. form validation (all 28 codes, request text identical to the packet, node ids 0-23, either nodes or
     no_node_appropriate, never both, confidence high/medium/low) and the independence declaration in
     evaluator.txt next to the form (name given, confirmed = yes); every evaluator judges all 28 cells;
  2. verdict agreement with the sealed key (node set vs no-node);
  3. for cells where both give nodes: identical / evaluator subset / evaluator superset / partial overlap / disjoint,
     and the Jaccard index of the two sets;
  4. rescoring of the scored SAS decision (first observation per cell) against the evaluator key:
     correct = node in the evaluator set; for an evaluator no-node verdict, correct only on an explicit
     clarification request; a parse failure is never correct. The same rule applied to the sealed key must
     give 17/28, otherwise the analysis stops;
  5. cells whose correctness differs between the sealed and the evaluator key;
  6. SAS choices the evaluator marked clearly wrong.
With two or more evaluators, additionally: pairwise verdict agreement and set relation, and the rescoring
under a strict key (node acceptable to every evaluator) and a lenient key (acceptable to any evaluator);
no-node in the strict/lenient key only if every / any evaluator chose no-node and no node remains.
"""
import argparse, csv, hashlib, json, os, sys, tempfile
from collections import Counter, OrderedDict
from itertools import combinations

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SE = os.path.join(ROOT, 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1', 'data', 'session_e')
PINNED = OrderedDict([
    ('day2_20260821/session/E7_sealed_set_v2.csv', '587e7b3644de731b1c4d0e3392002ea27e65a66dbcd559a3d02df768f4ab8704'),
    ('missions.csv', '7759648cf0014de914aae5b87f27edfefdde66e1cb9b0d49f8ffe760884d970a'),
])
NODES = set(range(24))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def fail(m):
    sys.exit('C3 ANALYSIS REFUSED: ' + m)


def ids(s):
    out = set()
    for x in (s or '').replace(',', '|').split('|'):
        x = x.strip()
        if x:
            if not x.lstrip('-').isdigit():
                raise ValueError('not a node id: %r' % x)
            out.add(int(x))
    return out


def load_sources(code_map_path, build_record_path):
    for rel, h in PINNED.items():
        if sha(os.path.join(SE, rel)) != h:
            fail('%s is not the RC1.1 file' % rel)
    rec = json.load(open(build_record_path, encoding='utf-8'))
    if sha(code_map_path) != rec['code_map_sha256']:
        fail('CODE_MAP.csv does not match BUILD_RECORD.json')
    cmap = {r['code']: r['cell_id'] for r in csv.DictReader(open(code_map_path, encoding='utf-8'))}
    ip = os.path.join(HERE, 'packets_blind', rec['packet'], 'items.csv')
    if sha(ip) != rec['packet_files']['items.csv']:
        fail('packet items.csv does not match BUILD_RECORD.json')
    items = {r['code']: r['request'] for r in csv.DictReader(open(ip, encoding='utf-8'))}
    key = {}
    for r in csv.DictReader(open(os.path.join(SE, 'day2_20260821/session/E7_sealed_set_v2.csv'), encoding='utf-8')):
        acc = ids(r['acceptabil'])
        key[r['cell_id']] = dict(no_node=(-1 in acc or not acc), nodes={n for n in acc if n >= 0})
    first = {}
    for m in sorted((m for m in csv.DictReader(open(os.path.join(SE, 'missions.csv'), encoding='utf-8'))
                     if m['experiment_id'] == 'E7'), key=lambda m: m['timestamp_utc']):
        first.setdefault(m['semantic_intent_id'], m)
    sas = {}
    for c, m in first.items():
        n = m['node_id'].strip()
        sas[c] = dict(node=int(n) if n.lstrip('-').isdigit() and int(n) >= 0 else None,
                      clarification=(m['nav_outcome'] == 'clarification_requested'),
                      parse_failure=(m['nav_outcome'] == 'vlm_failed' and not n))
    if set(cmap.values()) != set(key) or set(sas) != set(key) or len(cmap) != 28:
        fail('code map, sealed key and SAS records do not cover the same 28 cells')
    return cmap, key, sas, items


def load_declaration(path):
    d = os.path.join(os.path.dirname(os.path.abspath(path)), 'evaluator.txt')
    if not os.path.exists(d):
        fail('%s: evaluator.txt (independence declaration) missing next to the form' % path)
    kv = {}
    for line in open(d, encoding='utf-8-sig'):
        k, sep, v = line.partition(':')
        if sep:
            kv[k.strip().lower()] = v.strip()
    if not kv.get('name'):
        fail('%s: evaluator name missing in evaluator.txt' % path)
    if kv.get('confirmed (yes/no)', '').lower() != 'yes':
        fail('%s: independence confirmation is not "yes" in evaluator.txt' % path)
    return OrderedDict(name=kv['name'], affiliation_role=kv.get('affiliation/role', ''), date=kv.get('date', ''),
                       evaluator_txt_sha256=sha(d))


def load_response(path, cmap, items):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    codes = [r['code'].strip() for r in rows]
    if sorted(codes) != sorted(cmap):
        fail('%s: codes are not exactly the 28 packet codes' % path)
    out = {}
    for r in rows:
        try:
            acc, wrong = ids(r['acceptable_nodes']), ids(r.get('clearly_wrong_nodes', ''))
        except ValueError as e:
            fail('%s %s: %s' % (path, r['code'], e))
        if (r.get('request') or '').strip() != items[r['code'].strip()].strip():
            fail('%s %s: request text differs from the packet' % (path, r['code']))
        conf = (r.get('confidence') or '').strip().lower()
        if conf not in ('high', 'medium', 'low'):
            fail('%s %s: confidence must be high, medium or low' % (path, r['code']))
        nn = (r['no_node_appropriate'] or '').strip().lower()
        if nn not in ('', 'yes', 'no'):
            fail('%s %s: no_node_appropriate must be yes/no/empty' % (path, r['code']))
        no_node = nn == 'yes'
        if (acc - NODES) or (wrong - NODES):
            fail('%s %s: node id outside 0-23' % (path, r['code']))
        if no_node == bool(acc):
            fail('%s %s: give either acceptable nodes or no_node_appropriate = yes (exactly one)' % (path, r['code']))
        if acc & wrong:
            fail('%s %s: a node is both acceptable and clearly wrong' % (path, r['code']))
        out[cmap[r['code'].strip()]] = dict(no_node=no_node, nodes=acc, wrong=wrong,
                                           confidence=conf)
    return out


def correct(sas, k):
    if sas['parse_failure']:
        return False
    if k['no_node']:
        return sas['clarification']
    return sas['node'] is not None and sas['node'] in k['nodes']


def relation(a, b):
    if a == b: return 'identical'
    if a < b: return 'evaluator_subset'
    if a > b: return 'evaluator_superset'
    if a & b: return 'partial_overlap'
    return 'disjoint'


def per_evaluator(name, resp, key, sas):
    cells = []
    for c in sorted(key):
        k, e = key[c], resp[c]
        rel = jac = None
        if not k['no_node'] and not e['no_node']:
            rel = relation(e['nodes'], k['nodes']); jac = round(len(e['nodes'] & k['nodes']) / len(e['nodes'] | k['nodes']), 3)
        cells.append(OrderedDict(cell=c, sealed='no_node' if k['no_node'] else '|'.join(map(str, sorted(k['nodes']))),
                                 evaluator='no_node' if e['no_node'] else '|'.join(map(str, sorted(e['nodes']))),
                                 verdict_agree=(k['no_node'] == e['no_node']), set_relation=rel, jaccard=jac,
                                 sas_node='' if sas[c]['node'] is None else sas[c]['node'],
                                 sas_correct_sealed=correct(sas[c], k), sas_correct_evaluator=correct(sas[c], e),
                                 sas_choice_marked_wrong=(sas[c]['node'] in e['wrong']), confidence=e['confidence']))
    n_sealed = sum(r['sas_correct_sealed'] for r in cells)
    if n_sealed != 17:
        fail('sealed-key rescoring gives %d/28, not 17/28' % n_sealed)
    both = [r for r in cells if r['set_relation']]
    return OrderedDict(
        evaluator=name, cells=28,
        verdict_agreement=sum(r['verdict_agree'] for r in cells),
        verdict_disagreements=[r['cell'] for r in cells if not r['verdict_agree']],
        both_node_cells=len(both), set_relation=dict(Counter(r['set_relation'] for r in both)),
        mean_jaccard_both_node_cells=round(sum(r['jaccard'] for r in both) / len(both), 3) if both else None,
        sas_correct_sealed_key=n_sealed, sas_correct_evaluator_key=sum(r['sas_correct_evaluator'] for r in cells),
        correctness_changed=[r['cell'] for r in cells if r['sas_correct_sealed'] != r['sas_correct_evaluator']],
        sas_choices_marked_clearly_wrong=[r['cell'] for r in cells if r['sas_choice_marked_wrong']],
        confidence=dict(Counter(r['confidence'] for r in cells)), per_cell=cells)


def combined(resps, key, sas):
    out = OrderedDict()
    names = sorted(resps)
    out['pairwise'] = []
    for a, b in combinations(names, 2):
        ra, rb = resps[a], resps[b]
        agree = sum(ra[c]['no_node'] == rb[c]['no_node'] for c in key)
        rel = Counter(relation(ra[c]['nodes'], rb[c]['nodes']) for c in key if not ra[c]['no_node'] and not rb[c]['no_node'])
        out['pairwise'].append(OrderedDict(pair='%s vs %s' % (a, b), verdict_agreement=agree, set_relation=dict(rel)))
    for mode in ('strict', 'lenient'):
        k2 = {}
        for c in key:
            sets = [resps[n][c]['nodes'] for n in names]
            nodes = set.intersection(*sets) if mode == 'strict' else set.union(*sets)
            nn = [resps[n][c]['no_node'] for n in names]
            k2[c] = dict(nodes=nodes, no_node=(not nodes) and (all(nn) if mode == 'strict' else any(nn)))
        sc = [c for c in key if correct(sas[c], k2[c])]
        out['%s_key' % mode] = OrderedDict(sas_correct=len(sc), cells_without_any_verdict=[c for c in key if not k2[c]['nodes'] and not k2[c]['no_node']])
    return out


def run(responses, out_dir, code_map, build_record):
    cmap, key, sas, items = load_sources(code_map, build_record)
    decl = OrderedDict((os.path.basename(os.path.dirname(os.path.abspath(p))) or p, load_declaration(p)) for p in responses)
    resps = OrderedDict((os.path.basename(os.path.dirname(os.path.abspath(p))) or p, load_response(p, cmap, items)) for p in responses)
    res = OrderedDict(script_sha256=sha(os.path.abspath(__file__)), status='post-hoc sensitivity analysis; the sealed 17/28 remains primary',
                      declarations=decl, evaluators=[per_evaluator(n, r, key, sas) for n, r in resps.items()])
    if len(resps) > 1:
        res['combined'] = combined(resps, key, sas)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(res, open(os.path.join(out_dir, 'C3_ADJUDICATION_RESULTS.json'), 'w', encoding='utf-8'), indent=1)
    for ev in res['evaluators']:
        with open(os.path.join(out_dir, 'per_cell_%s.csv' % ev['evaluator']), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, list(ev['per_cell'][0].keys())); w.writeheader(); w.writerows(ev['per_cell'])
    return res


def self_test():
    code_map = os.path.join(HERE, 'internal', 'CODE_MAP.csv'); build = os.path.join(HERE, 'internal', 'BUILD_RECORD.json')
    cmap, key, sas, items = load_sources(code_map, build)
    inv = {v: k for k, v in cmap.items()}
    GOOD_DECL = 'name: Test Evaluator\naffiliation/role: test\ndate: 2026-10-04\nconfirmed (yes/no): yes\n'
    tmp = tempfile.mkdtemp(prefix='c3_selftest_')
    def form(name, fn, decl=GOOD_DECL, conf='high', req=None):
        d = os.path.join(tmp, name); os.makedirs(d)
        p = os.path.join(d, 'response_form.csv')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['code', 'request', 'acceptable_nodes', 'no_node_appropriate', 'clearly_wrong_nodes', 'confidence', 'comment'])
            for c in sorted(key):
                w.writerow([inv[c], (req or items)[inv[c]] if not callable(req) else req(inv[c])] + fn(c) + [conf, ''])
        if decl is not None:
            open(os.path.join(d, 'evaluator.txt'), 'w', encoding='utf-8').write(decl)
        return p
    same = form('evalSame', lambda c: ['', 'yes', ''] if key[c]['no_node'] else ['|'.join(map(str, sorted(key[c]['nodes']))), '', ''])
    allno = form('evalAllNo', lambda c: ['', 'yes', ''])
    res = []
    def t(name, ok): res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name)
    r = run([same], os.path.join(tmp, 'o1'), code_map, build)['evaluators'][0]
    t('identical key: verdict agreement 28/28', r['verdict_agreement'] == 28)
    t('identical key: all both-node cells identical, Jaccard 1', r['set_relation'] == {'identical': r['both_node_cells']} and r['mean_jaccard_both_node_cells'] == 1.0)
    t('identical key: rescoring 17/28, no change', r['sas_correct_evaluator_key'] == 17 and not r['correctness_changed'])
    r = run([allno], os.path.join(tmp, 'o2'), code_map, build)['evaluators'][0]
    t('all no-node: rescoring 0/28 (no E7 clarification request exists)', r['sas_correct_evaluator_key'] == 0)
    t('all no-node: verdict agreement = number of sealed no-node cells', r['verdict_agreement'] == sum(k['no_node'] for k in key.values()))
    c2 = run([same, allno], os.path.join(tmp, 'o3'), code_map, build)['combined']
    t('two evaluators: strict key 0/28, lenient key 17/28', c2['strict_key']['sas_correct'] == 0 and c2['lenient_key']['sas_correct'] == 17)
    import subprocess
    def refuses(name, fn, **kw):
        p = form(name, fn, **kw)
        cp = subprocess.run([sys.executable, '-B', os.path.abspath(__file__), '--responses', p, '--out', os.path.join(tmp, 'x_' + name)], capture_output=True, text=True)
        return cp.returncode != 0 and 'REFUSED' in (cp.stdout + cp.stderr)
    t('refuses: nodes and no-node together', refuses('bad1', lambda c: ['1', 'yes', '']))
    t('refuses: neither nodes nor no-node', refuses('bad2', lambda c: ['', '', '']))
    t('refuses: node id 99', refuses('bad3', lambda c: ['99', '', '']))
    t('refuses: node both acceptable and wrong', refuses('bad4', lambda c: ['3', '', '3']))
    ok_fn = lambda c: ['', 'yes', ''] if key[c]['no_node'] else ['|'.join(map(str, sorted(key[c]['nodes']))), '', '']
    t('refuses: request text edited', refuses('bad6', ok_fn, req=lambda code: items[code] + ' (edited)'))
    t('refuses: confidence missing', refuses('bad7', ok_fn, conf=''))
    t('refuses: confidence not in high/medium/low', refuses('bad8', ok_fn, conf='sure'))
    t('refuses: declaration file missing', refuses('bad9', ok_fn, decl=None))
    t('refuses: independence not confirmed', refuses('bad10', ok_fn, decl=GOOD_DECL.replace('yes\n', 'no\n')))
    t('refuses: evaluator name empty', refuses('bad11', ok_fn, decl=GOOD_DECL.replace('Test Evaluator', '')))
    d = os.path.join(tmp, 'bad5'); os.makedirs(d); p = os.path.join(d, 'response_form.csv')
    open(os.path.join(d, 'evaluator.txt'), 'w', encoding='utf-8').write(GOOD_DECL)
    rows = open(same, encoding='utf-8').read().splitlines()[:-1]; open(p, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    cp = subprocess.run([sys.executable, '-B', os.path.abspath(__file__), '--responses', p, '--out', os.path.join(tmp, 'x5')], capture_output=True, text=True)
    t('refuses: missing code', cp.returncode != 0 and 'REFUSED' in (cp.stdout + cp.stderr))
    n_pass = sum(o for _, o in res)
    json.dump(dict(analysis_sha256=sha(os.path.abspath(__file__)), n=len(res), n_pass=n_pass, tests=res),
              open(os.path.join(HERE, 'internal', 'SELF_TEST_RESULTS.json'), 'w', encoding='utf-8'), indent=1)
    print('C3 ANALYSIS SELF-TEST', 'PASS' if n_pass == len(res) else 'FAIL', n_pass, '/', len(res))
    return n_pass == len(res)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--responses', action='append'); ap.add_argument('--out', default=os.path.join(HERE, 'analysis'))
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if not a.responses:
        ap.error('--responses required')
    r = run(a.responses, a.out, os.path.join(HERE, 'internal', 'CODE_MAP.csv'), os.path.join(HERE, 'internal', 'BUILD_RECORD.json'))
    for e in r['evaluators']:
        print('%s: verdict agreement %d/28; SAS correct %d/28 (sealed key 17/28); changed: %s' % (
            e['evaluator'], e['verdict_agreement'], e['sas_correct_evaluator_key'], ', '.join(e['correctness_changed']) or 'none'))
