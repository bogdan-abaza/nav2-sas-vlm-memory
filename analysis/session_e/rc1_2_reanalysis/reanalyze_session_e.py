#!/usr/bin/env python3
"""
reanalyze_session_e.py -- RC1.2 reanalysis layer for Session E.

Derives corrected descriptive figures from the RC1.1 Session E records without modifying
them. The RC1.1 dataset, the core analyzer (analysis/session_e/core/analyze_session_e.py)
and its published output (results_E.json) are read only; their hashes are checked before
anything is computed, and the published figures that remain valid are reconciled.

Sections of the output:
  e7_outcome_taxonomy      the 28 sealed E7 cells, first observation, classified into
                           mutually exclusive terminal decision classes; abstention-expected
                           cells are scored correct only by an explicit clarification
                           request (a parse failure is never counted as an abstention).
  e7_fast_path             false-fast-resolution incidence over the 28 cells, and the error
                           rate among the cells resolved on the deterministic fast path.
  e7_g3_context_evidence   documentary evidence on the context available to cell G-3
                           (deterministic decision; its per-cycle context was not persisted).
  navigation_denominators  terminal outcomes of the protocol-valid runs and three measures
                           of navigation failure, each with its own denominator.

Usage (from the repository root):
  PYTHONPATH=data/session_e/public_code \\
  python3 analysis/session_e/rc1_2_reanalysis/reanalyze_session_e.py \\
      --dataset data/session_e --core analysis/session_e/core --outdir <dir>
Requires: numpy, scipy (as the core analyzer).
"""
import argparse, csv, hashlib, json, os, re, sys
from collections import Counter, OrderedDict

# RC1.1 inputs this layer is defined on. A mismatch stops the analysis.
RC1_1_SHA256 = {
    'core/analyze_session_e.py': 'a69324ce3dde64677178f90441d47fefebd8f98df3764188d53511fd3f5d6d4b',
    'core/results_E.json':       '12e9ff2e4b664baef2ee60206cb309b5458f2d11fed0f83ac9a73b69b08d430e',
    'dataset/missions.csv':      '7759648cf0014de914aae5b87f27edfefdde66e1cb9b0d49f8ffe760884d970a',
    'dataset/day2_20260821/session/E7_sealed_set_v2.csv':
                                 '587e7b3644de731b1c4d0e3392002ea27e65a66dbcd559a3d02df768f4ab8704',
}
DISPATCHED = {'mission_complete', 'mission_complete_fallback', 'missed'}   # a navigation goal was sent
ARRIVED = {'mission_complete', 'mission_complete_fallback'}
E7_CLASSES = ['acceptable_selection', 'incorrect_executable', 'executable_where_abstention_expected',
              'model_response_parse_failure', 'clarification_request']
G3_CELL, G3_OBJECT = 'G-3', 'stop sign_8'


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


class PublicChecksums:
    """Every dataset file this layer reads is verified against CHECKSUMS_PUBLIC.md5."""
    def __init__(self, root):
        self.root, self.ref, self.used = root, {}, []
        for line in open(os.path.join(root, 'CHECKSUMS_PUBLIC.md5'), encoding='utf-8'):
            h, _, rel = line.rstrip('\n').partition('  ')
            if rel:
                self.ref[rel.strip()] = h.strip()

    def path(self, rel):
        p = os.path.join(self.root, rel)
        if self.ref.get(rel) != md5(p):
            sys.exit('INPUT NOT VALID: %s does not match CHECKSUMS_PUBLIC.md5' % rel)
        self.used.append(rel)
        return p


def node_id(v):
    s = str(v).strip()
    return int(s) if re.fullmatch(r'-?\d+', s) else None


# ------------------------------------------------------------------------------------------
# E7
# ------------------------------------------------------------------------------------------

def classify_e7(m, spec):
    """Terminal decision class of one E7 record. Order matters and is exhaustive."""
    nid = node_id(m['node_id'])
    if m['nav_outcome'] == 'clarification_requested':
        return 'clarification_request'
    if m['nav_outcome'] == 'vlm_failed' and nid is None:
        return 'model_response_parse_failure'
    if nid is None or nid < 0:
        sys.exit('UNCLASSIFIABLE E7 record: %s %s' % (m['semantic_intent_id'], m['nav_outcome']))
    if spec['abstention_expected']:
        return 'executable_where_abstention_expected'
    return 'acceptable_selection' if nid in spec['acceptable'] else 'incorrect_executable'


def e7(d, A):
    recs = [m for m in d.missions if m['experiment_id'] == 'E7']
    first, repeats = OrderedDict(), []
    for m in sorted(recs, key=lambda r: r['timestamp_utc']):
        if m[A.CLUSTER_KEY] in first:
            repeats.append(m)
        else:
            first[m[A.CLUSTER_KEY]] = m
    missing = sorted(set(d.e7) - set(first)); extra = sorted(set(first) - set(d.e7))
    if missing or extra:
        sys.exit('E7 cells do not match the sealed set: missing %s, extra %s' % (missing, extra))
    rows = []
    for cid in sorted(first):
        m, spec = first[cid], d.e7[cid]
        cls = classify_e7(m, spec)
        nid = node_id(m['node_id'])
        rows.append(OrderedDict(
            cell=cid, level=spec['level'], instruction=spec['instruction'],
            abstention_expected=spec['abstention_expected'],
            sealed_acceptable='-1' if spec['abstention_expected'] else '|'.join(map(str, sorted(spec['acceptable']))),
            sealed_flagged_wrong='|'.join(map(str, sorted(spec['wrong']))),
            resolution_method=m['resolution_method'], resolution_step=m['resolution_step'],
            fast_path=m['_fast'], node_id='' if nid is None else nid, node_name=m['node_name'],
            chose_flagged_wrong=(nid in spec['wrong']) if nid is not None else False,
            nav_outcome=m['nav_outcome'], outcome_class=cls,
            correct=(cls == 'acceptable_selection'
                     or (cls == 'clarification_request' and spec['abstention_expected'])),
            run_id=m['run_id'], platform_id=m['platform_id'], timestamp_utc=m['timestamp_utc']))
    n = len(rows)
    dist = Counter(r['outcome_class'] for r in rows)
    fast = [r for r in rows if r['fast_path']]
    fast_wrong = [r for r in fast if not r['correct']]
    W = A.wilson
    taxonomy = OrderedDict(
        unit='sealed cell, first observation (the scoring unit of the RC1.1 core analysis)',
        cells=n, records_in_block=len(recs),
        classes=OrderedDict((c, OrderedDict(n=dist.get(c, 0),
                                            cells=[r['cell'] for r in rows if r['outcome_class'] == c]))
                            for c in E7_CLASSES),
        correct=W(sum(r['correct'] for r in rows), n),
        scoring_rule=('acceptable_selection is correct; for an abstention-expected cell only an '
                      'explicit clarification request is correct. A model-response parse failure '
                      'is never scored as an abstention.'),
        definitions=OrderedDict(
            acceptable_selection='executable node in the sealed acceptable set',
            incorrect_executable='executable node outside the sealed acceptable set, abstention not expected',
            executable_where_abstention_expected='executable node for a cell whose sealed acceptable set is -1',
            model_response_parse_failure=('L3b escalation that returned a model response the parser '
                                          'could not decode (nav_outcome = vlm_failed, no node)'),
            clarification_request='nav_outcome = clarification_requested'),
        abstention_expected_cells=OrderedDict(
            n=sum(r['abstention_expected'] for r in rows),
            clarification_requested=sum(r['abstention_expected'] and r['outcome_class'] == 'clarification_request'
                                        for r in rows)),
        nav_outcome_of_scored_executable_records=dict(Counter(
            r['nav_outcome'] for r in rows if r['outcome_class'] not in
            ('model_response_parse_failure', 'clarification_request'))),
        additional_records_not_scored=[OrderedDict(
            cell=m[A.CLUSTER_KEY], run_id=m['run_id'], record_seq=m['record_seq'],
            same_run_as_scored_record=(m['run_id'] == first[m[A.CLUSTER_KEY]]['run_id']),
            node_id=m['node_id'], same_node_as_scored_record=(m['node_id'] == first[m[A.CLUSTER_KEY]]['node_id']),
            nav_outcome=m['nav_outcome']) for m in repeats])
    fastpath = OrderedDict(
        false_fast_resolution_incidence=W(len(fast_wrong), n),
        error_among_fast_path_decisions=W(len(fast_wrong), len(fast)),
        fast_path_correctness=W(len(fast) - len(fast_wrong), len(fast)),
        fast_path_cells=[r['cell'] for r in fast], false_fast_cells=[r['cell'] for r in fast_wrong],
        definition=('fast path = resolved deterministically at L3a, with no VLM call. False fast '
                    'resolution = a fast-path decision that is not correct under the scoring rule.'),
        note='Small denominators; both figures are reported with their Wilson 95% intervals.')
    return rows, taxonomy, fastpath


def e7_reconciliation(rows, taxonomy, fastpath, res):
    """Compare with the published RC1.1 figures, located by section title."""
    sec = next(v for v in res['points'].values()
               if v.get('title') == 'Fast-path rate and the distribution it was measured on')
    e = sec['metrics']['e7_sealed_set']
    pub_abst = {r['cell'] for r in e['per_cell'] if r['abstained']}
    parse = set(taxonomy['classes']['model_response_parse_failure']['cells'])
    out = OrderedDict(
        published_correct=e['correct'], reanalysis_correct=taxonomy['correct'],
        correct_count_unchanged=(e['correct']['k'] == taxonomy['correct']['k']
                                 and e['correct']['n'] == taxonomy['correct']['n']),
        published_false_fast_incidence=e['false_fast_resolution']['incidence'],
        published_fast_path_correctness=e['fast_path_correctness'],
        fast_path_figures_unchanged=(
            e['false_fast_resolution']['incidence']['k'] == fastpath['false_fast_resolution_incidence']['k']
            and e['fast_path_correctness']['k'] == fastpath['fast_path_correctness']['k']
            and e['fast_path_correctness']['n'] == fastpath['fast_path_correctness']['n']),
        published_abstained_field_true=sorted(pub_abst),
        published_abstained_cells_are_parse_failures=(pub_abst == parse),
        note=('In the RC1.1 output, abstained = (no node). The cells carrying abstained = true '
              'are the model-response parse failures; no E7 record is a clarification request. '
              'The RC1.1 files are unchanged; this layer reports the corrected classification.'))
    if not out['correct_count_unchanged'] or not out['fast_path_figures_unchanged']:
        sys.exit('RECONCILIATION FAILED: %s' % json.dumps(out)[:400])
    return out


def g3_evidence(d, A, pc, rows):
    """Documentary evidence on the context available to G-3. No resolver code is executed."""
    g3 = next(r for r in rows if r['cell'] == G3_CELL)
    plat, day = g3['platform_id'], 'day2_20260821'
    t0 = g3['timestamp_utc']
    prompts = []
    for m in d.missions:
        if m['day'] != day or m['platform_id'] != plat or not m['image_start']:
            continue
        rel = os.path.join(os.path.dirname(m['image_start']), 'vlm_decision_prompt.txt').replace(os.sep, '/')
        if not os.path.exists(os.path.join(d.root, rel)):
            continue
        txt = open(pc.path(rel), encoding='utf-8').read()
        lines = [l.strip() for l in txt.splitlines() if '"%s"' % G3_OBJECT in l]
        prompts.append(OrderedDict(timestamp_utc=m['timestamp_utc'], cell=m[A.CLUSTER_KEY], run_id=m['run_id'],
                                   prompt_file=rel, contains_object=bool(lines),
                                   object_line=lines[0] if lines else ''))
    prompts.sort(key=lambda p: p['timestamp_utc'])
    before = [p for p in prompts if p['timestamp_utc'] < t0]
    after = [p for p in prompts if p['timestamp_utc'] > t0]
    last_before, first_after = (before[-1] if before else None), (after[0] if after else None)
    archives = []
    adir = os.path.join(d.root, day, 'dynamic_graph_archive')
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith('.geojson'):
            continue
        rel = '%s/dynamic_graph_archive/%s' % (day, fn)
        g = json.load(open(pc.path(rel), encoding='utf-8'))
        for ft in g.get('features', []):
            p = ft.get('properties', {})
            if p.get('obj_id') == G3_OBJECT:
                archives.append(OrderedDict(archive=rel, obj_id=p['obj_id'], class_name=p.get('class_name'),
                                            confidence=p.get('confidence'), first_seen=p.get('first_seen'),
                                            last_seen=p.get('last_seen'), xy=ft['geometry']['coordinates']))
    static_rel = '%s/config/semantic_objects_static_v2.geojson' % day
    static_classes = sorted({ft['properties'].get('class_name') for ft in
                             json.load(open(pc.path(static_rel), encoding='utf-8'))['features']})
    conf_values = sorted({re.search(r'conf=([0-9.]+)', p['object_line']).group(1)
                          for p in prompts if p['contains_object']})
    return OrderedDict(
        cell=G3_CELL, instruction=g3['instruction'], sealed_acceptable=g3['sealed_acceptable'],
        decision=OrderedDict(resolution_method=g3['resolution_method'], resolution_step=g3['resolution_step'],
                             node_id=g3['node_id'], node_name=g3['node_name'],
                             node_in_sealed_flagged_wrong=g3['chose_flagged_wrong'],
                             platform_id=plat, timestamp_utc=t0, run_id=g3['run_id']),
        static_object_classes_day2=static_classes,
        static_class_stop_sign_present=('stop sign' in static_classes),
        dynamic_archives_containing_object=archives,
        l3b_prompts_same_platform_day=OrderedDict(
            n=len(prompts), n_containing_object=sum(p['contains_object'] for p in prompts),
            confidence_values_in_prompts=conf_values,
            last_before_g3=last_before, first_after_g3=first_after),
        status=('reconstruction from the surrounding context, not direct per-cycle provenance: G-3 '
                'was resolved deterministically (no VLM call), and its exact per-cycle context was '
                'not persisted.'),
        prompts=prompts)


# ------------------------------------------------------------------------------------------
# Navigation denominators
# ------------------------------------------------------------------------------------------

def navigation(d, A):
    from scipy import stats
    runs = [r for r in d.runs if r['experiment_id'] not in A.EXCLUDED_FROM_RATES
            and r['audit_file'] not in A.INVALIDATED_RUNS]
    plats = sorted({r['platform_id'] for r in runs})
    for r in runs:
        r['_dispatched'] = any(x['nav_outcome'] in DISPATCHED for x in r['records'])
        r['_arrived'] = r['terminal_outcome'] in ARRIVED

    def group(p=None):
        return [r for r in runs if p is None or r['platform_id'] == p]

    term = OrderedDict([('total', dict(Counter(r['terminal_outcome'] for r in runs)))] +
                       [(p, dict(Counter(r['terminal_outcome'] for r in group(p)))) for p in plats])
    term['runs'] = OrderedDict([('total', len(runs))] + [(p, len(group(p))) for p in plats])
    disp = lambda g: [r for r in g if r['_dispatched']]
    defs = OrderedDict(
        terminal_miss_all_valid_runs=(lambda g: g, lambda r: r['terminal_outcome'] == 'missed',
                                      'terminal miss / all protocol-valid runs'),
        terminal_miss_dispatched_runs=(disp, lambda r: r['terminal_outcome'] == 'missed',
                                       'terminal miss / runs with at least one dispatched navigation goal'),
        non_arrival_dispatched_runs=(disp, lambda r: not r['_arrived'],
                                     'no arrival / runs with at least one dispatched navigation goal'))
    measures = OrderedDict()
    for name, (den, ev, text) in defs.items():
        row = OrderedDict(definition=text, total=A.wilson(sum(map(ev, den(runs))), len(den(runs))))
        for p in plats:
            g = den(group(p)); row[p] = A.wilson(sum(map(ev, g)), len(g))
        if len(plats) == 2:
            t = [[row[p]['k'], row[p]['n'] - row[p]['k']] for p in plats]
            row['fisher_exact_two_sided'] = OrderedDict(comparison='%s vs %s' % tuple(plats), table=t,
                                                        p=float('%.4f' % stats.fisher_exact(t)[1]))
        measures[name] = row
    non_arrival = [OrderedDict(audit_file=r['audit_file'], platform_id=r['platform_id'], block=r['experiment_id'],
                               intent=r['semantic_intent_id'], instruction=r['instruction_text'],
                               record_outcomes=[x['nav_outcome'] for x in r['records']],
                               record_methods=[x['resolution_method'] for x in r['records']],
                               xy_error_m=[x['xy_error_m'] for x in r['records']],
                               terminal_outcome=r['terminal_outcome'])
                   for r in runs if r['_dispatched'] and not r['_arrived']]
    return OrderedDict(
        unit='run (terminal record = last decision record of the run)',
        basis=('protocol-valid runs: block E0 and the run invalidated by the session protocol are '
               'excluded, as in RC1.1'),
        dispatched_definition='a run with at least one record whose nav_outcome is in %s' % sorted(DISPATCHED),
        arrival_definition='terminal nav_outcome in %s' % sorted(ARRIVED),
        terminal_outcomes=term,
        dispatched_runs=OrderedDict([('total', sum(r['_dispatched'] for r in runs))] +
                                    [(p, sum(r['_dispatched'] for r in group(p))) for p in plats]),
        measures=measures, non_arrival_runs=non_arrival,
        note='Few events; the Fisher tests are descriptive and have almost no power.')


def nav_reconciliation(nav, res):
    sec = next(v for v in res['points'].values()
               if v.get('title') == 'Semantic reasoning vs physical execution, at run level')
    pv = sec['metrics']['terminal_failures_protocol_valid']
    m = nav['measures']['terminal_miss_all_valid_runs']['total']
    out = OrderedDict(published_terminal_failures_protocol_valid=OrderedDict(n=pv['n'], runs=pv['runs']),
                      reanalysis=OrderedDict(n=m['k'], runs=m['n']),
                      unchanged=(pv['n'] == m['k'] and pv['runs'] == m['n']))
    if not out['unchanged']:
        sys.exit('RECONCILIATION FAILED: %s' % json.dumps(out))
    return out


# ------------------------------------------------------------------------------------------
# Output
# ------------------------------------------------------------------------------------------

def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader()
        for r in rows:
            w.writerow({k: ('|'.join(map(str, v)) if isinstance(v, list) else v) for k, v in r.items()})


def fmt(w):
    return '%d/%d (%.3f-%.3f)' % (w['k'], w['n'], w['low'], w['high'])


def render(out):
    t, fp = out['e7_outcome_taxonomy'], out['e7_fast_path']
    g, nv = out['e7_g3_context_evidence'], out['navigation_denominators']
    L = ['# Session E -- RC1.2 reanalysis layer', '',
         'Derived from the RC1.1 Session E records, which are unchanged. Generated by '
         '`reanalyze_session_e.py`; do not edit by hand. Intervals are Wilson 95%.', '',
         '## E7 sealed set: terminal decision classes (%d cells, first observation)' % t['cells'], '',
         '| Class | Cells | Which |', '|---|---|---|']
    L += ['| %s | %d | %s |' % (c, v['n'], ', '.join(v['cells']) or '--') for c, v in t['classes'].items()]
    L += ['', '- Correct: %s.' % fmt(t['correct']),
          '- Scoring rule: %s' % t['scoring_rule'],
          '- Abstention-expected cells: %d; clarification requested in %d.' % (
              t['abstention_expected_cells']['n'], t['abstention_expected_cells']['clarification_requested']),
          '- nav_outcome of the scored executable records: %s.' % ', '.join(
              '%s %d' % kv for kv in sorted(t['nav_outcome_of_scored_executable_records'].items())),
          '- Records in the block: %d. Additional records, not scored: %s.' % (
              t['records_in_block'], '; '.join(
                  '%s record %s (%s run, %s node %s, %s)' % (
                      r['cell'], r['record_seq'], 'same' if r['same_run_as_scored_record'] else 'different',
                      'same' if r['same_node_as_scored_record'] else 'different', r['node_id'], r['nav_outcome'])
                  for r in t['additional_records_not_scored']) or 'none'), '',
          '## E7 fast path', '',
          '- False-fast-resolution incidence: %s; cells: %s.' % (
              fmt(fp['false_fast_resolution_incidence']), ', '.join(fp['false_fast_cells'])),
          '- Error among fast-path decisions: %s; fast-path cells: %s.' % (
              fmt(fp['error_among_fast_path_decisions']), ', '.join(fp['fast_path_cells'])),
          '- Fast-path correctness (complement): %s.' % fmt(fp['fast_path_correctness']), '',
          '## E7 cell G-3: context evidence', '',
          '- Instruction: "%s"; sealed acceptable set: %s.' % (g['instruction'], g['sealed_acceptable']),
          '- Decision: %s, step %s, node %s (%s); node in the sealed flagged-wrong set: %s.' % (
              g['decision']['resolution_method'], g['decision']['resolution_step'], g['decision']['node_id'],
              g['decision']['node_name'], g['decision']['node_in_sealed_flagged_wrong']),
          '- Static object classes (day 2): %s; a static `stop sign` class is present: %s.' % (
              ', '.join(g['static_object_classes_day2']), g['static_class_stop_sign_present'])]
    for a in g['dynamic_archives_containing_object']:
        L.append('- Dynamic-graph archive `%s`: `%s` (class %s), confidence %s, first seen %s, last seen %s.' % (
            a['archive'].split('/')[-1], a['obj_id'], a['class_name'], a['confidence'],
            a['first_seen'], a['last_seen']))
    lp = g['l3b_prompts_same_platform_day']
    L.append('- L3b decision prompts on %s, day 2: %d, of which %d list `%s` (confidence values shown: %s).' % (
        g['decision']['platform_id'], lp['n'], lp['n_containing_object'], G3_OBJECT,
        ', '.join(lp['confidence_values_in_prompts'])))
    if lp['last_before_g3']:
        b = lp['last_before_g3']
        L.append('- Last L3b prompt before G-3: %s, cell %s; lists the object: %s -- `%s`' % (
            b['timestamp_utc'], b['cell'], b['contains_object'], b['object_line']))
    if lp['first_after_g3']:
        a = lp['first_after_g3']
        L.append('- First L3b prompt after G-3: %s, cell %s; lists the object: %s.' % (
            a['timestamp_utc'], a['cell'], a['contains_object']))
    L += ['- Status: %s' % g['status'], '',
          '## Navigation: terminal outcomes and denominators', '', 'Basis: %s.' % nv['basis'], '']
    plats = [k for k in nv['terminal_outcomes'] if k not in ('total', 'runs')]
    outs = sorted({o for k in ['total'] + plats for o in nv['terminal_outcomes'][k]})
    L += ['| Terminal outcome | Total | ' + ' | '.join(plats) + ' |', '|---|---|' + '---|' * len(plats)]
    L += ['| %s | %d | ' % (o, nv['terminal_outcomes']['total'].get(o, 0))
          + ' | '.join(str(nv['terminal_outcomes'][p].get(o, 0)) for p in plats) + ' |' for o in outs]
    L += ['| **runs** | %d | ' % nv['terminal_outcomes']['runs']['total']
          + ' | '.join(str(nv['terminal_outcomes']['runs'][p]) for p in plats) + ' |', '',
          'Runs with at least one dispatched navigation goal: %d (%s).' % (
              nv['dispatched_runs']['total'], ', '.join('%s %d' % (p, nv['dispatched_runs'][p]) for p in plats)), '',
          '| Measure | Total | ' + ' | '.join(plats) + ' | Fisher p |', '|---|---|' + '---|' * len(plats) + '---|']
    for name, m in nv['measures'].items():
        L.append('| %s | %s | ' % (m['definition'], fmt(m['total']))
                 + ' | '.join('%d/%d' % (m[p]['k'], m[p]['n']) for p in plats)
                 + ' | %s |' % m.get('fisher_exact_two_sided', {}).get('p', ''))
    L += ['', 'Dispatched runs that did not end in arrival:', '']
    for r in nv['non_arrival_runs']:
        L.append('- `%s` (%s, block %s, "%s"): record outcomes %s; xy error %s m; terminal %s.' % (
            r['audit_file'].split('/')[-1], r['platform_id'], r['block'], r['instruction'],
            ' -> '.join(r['record_outcomes']), ' / '.join(str(x) for x in r['xy_error_m']), r['terminal_outcome']))
    rec = out['reconciliation']
    L += ['', nv['note'], '', '## Reconciliation with RC1.1', '',
          '- E7 correct count unchanged: %s; fast-path figures unchanged: %s.' % (
              rec['e7']['correct_count_unchanged'], rec['e7']['fast_path_figures_unchanged']),
          '- RC1.1 cells with `abstained = true` (%s) are exactly the parse failures: %s.' % (
              ', '.join(rec['e7']['published_abstained_field_true']),
              rec['e7']['published_abstained_cells_are_parse_failures']),
          '- Terminal failures on protocol-valid runs unchanged: %s.' % rec['navigation']['unchanged']]
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--core', required=True)
    ap.add_argument('--outdir', required=True)
    a = ap.parse_args()
    for key, h in RC1_1_SHA256.items():
        base, rel = key.split('/', 1)
        if sha256(os.path.join(a.core if base == 'core' else a.dataset, rel)) != h:
            sys.exit('INPUT NOT VALID: %s is not the RC1.1 file' % key)
    sys.path.insert(0, os.path.abspath(a.core))
    sys.dont_write_bytecode = True
    import analyze_session_e as A
    pc = PublicChecksums(a.dataset)
    for rel in ('missions.csv', 'sessions.csv', 'day2_20260821/session/E7_sealed_set_v2.csv',
                'day2_20260821/config/route_graph_fiir.geojson'):
        pc.path(rel)
    d = A.Dataset(a.dataset)
    res = json.load(open(os.path.join(a.core, 'results_E.json'), encoding='utf-8'))
    rows, tax, fp = e7(d, A)
    g3 = g3_evidence(d, A, pc, rows)
    nav = navigation(d, A)
    out = OrderedDict(
        meta=OrderedDict(script='analysis/session_e/rc1_2_reanalysis/reanalyze_session_e.py',
                         script_sha256=sha256(os.path.abspath(__file__)),
                         rc1_1_inputs_sha256=RC1_1_SHA256,
                         dataset_files_verified_against_CHECKSUMS_PUBLIC=len(set(pc.used))),
        e7_outcome_taxonomy=tax, e7_fast_path=fp, e7_g3_context_evidence=g3,
        navigation_denominators=nav,
        reconciliation=OrderedDict(e7=e7_reconciliation(rows, tax, fp, res),
                                   navigation=nav_reconciliation(nav, res)))
    os.makedirs(a.outdir, exist_ok=True)
    json.dump(out, open(os.path.join(a.outdir, 'rc1_2_reanalysis_results.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    write_csv(os.path.join(a.outdir, 'e7_taxonomy_per_cell.csv'), rows)
    write_csv(os.path.join(a.outdir, 'e7_g3_prompt_timeline.csv'), g3['prompts'])
    write_csv(os.path.join(a.outdir, 'navigation_non_arrival_runs.csv'), nav['non_arrival_runs'])
    open(os.path.join(a.outdir, 'RC1_2_REANALYSIS.md'), 'w', encoding='utf-8').write(render(out))
    print('written to', a.outdir)


if __name__ == '__main__':
    main()
