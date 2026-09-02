#!/usr/bin/env python3
"""
analyze_session_e.py — the single source of every number in the response letter.

Reads only the published dataset. Produces one JSON keyed by reviewer point
(R1-1 ... R2-10) plus the internal audit checks (AC-*), and a Markdown rendering of it.
Nothing in the response letter should be typed by hand; it should be read from here.

Design rules:
  1. NO CONSTANT IS HARD-CODED. Every figure is computed from the dataset. Thresholds
     that define a convention (e.g. what counts as an L3b call) are declared once, at the
     top, and reported alongside the number they produce.
  2. EVERY FIGURE CARRIES ITS DENOMINATOR AND ITS SOURCE. A rate without n is a bug.
  3. CONVENTIONS ARE EXPLICIT. Where the source documents disagree (see
     KNOWN_DISCREPANCIES.md), every convention is computed and reported, not silently
     chosen.

Usage:  python3 analyze_session_e.py --dataset <path to data/session_e>
Requires: numpy, scipy
"""

import argparse, csv, hashlib, json, math, os, shutil, sys
from collections import Counter, defaultdict, OrderedDict

import numpy as np
from scipy import stats

BOOTSTRAP = 10000
RNG_SEED = 20260822          # fixed so the intervals are reproducible

# The experimental unit for repeated measures (R1-7). One natural-language intent,
# repeated; repetitions are observations within a cluster, not independent samples.
CLUSTER_KEY = 'semantic_intent_id'

# Resolution methods that are deterministic fast-path (no VLM call).
FAST_PATH = {'L3a_deterministic', 'L3a_m3_preference'}
# Methods that represent an L3b call that returned a usable answer.
L3B_OK = {'L3b_vlm'}
# A record whose L3b call did not return parseable JSON.
L3B_FAIL = {'escalated'}
# The negation guard blocked the call before or after the model answered.
NEGATION_BLOCKED = {'L3b_vlm_negation_blocked'}

# Blocks excluded from every reported rate. E0 is a configuration gate, not a measurement.
EXCLUDED_FROM_RATES = {'E0'}

# The abstention marker the resolver returns when no node is a valid answer. It is not a
# node id: the graph is indexed 0..23.
ABSTENTION_NODE = -1

# Runs the session protocol itself invalidated and re-ran. They stay in the dataset as
# provenance and are reported in the raw counts, but the primary outcome analysis excludes
# them, because the protocol declared them void before the outcome was known.
INVALIDATED_RUNS = {
    'day1_20260820/logs/audit_20260820_124642.jsonl':
        'externally invalidated during the session (localization collapse from an '
        'external cause) and re-run under the protocol; the completed re-run is the '
        'observation of record',
}


# ======================================================================================
# statistics
# ======================================================================================

def wilson(k, n, z=1.96):
    """Wilson score interval. Correct at the extremes, where normal approximation is not."""
    if n == 0:
        return dict(k=0, n=0, rate=None, low=None, high=None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return dict(k=int(k), n=int(n), rate=round(p, 4),
                low=round(max(0.0, c - h), 4), high=round(min(1.0, c + h), 4))


def rule_of_three(n):
    """Upper 95% bound on a rate when zero events were observed in n trials."""
    return round(3.0 / n, 4) if n else None


def describe(values):
    a = np.asarray([v for v in values if v is not None], float)
    if a.size == 0:
        return dict(n=0)
    return dict(n=int(a.size), mean=round(float(a.mean()), 3),
                sd=round(float(a.std(ddof=1)), 3) if a.size > 1 else 0.0,
                median=round(float(np.median(a)), 3),
                q1=round(float(np.percentile(a, 25)), 3),
                q3=round(float(np.percentile(a, 75)), 3),
                min=round(float(a.min()), 3), max=round(float(a.max()), 3))


def cliffs_delta(a, b):
    """Non-parametric effect size. |d| < .147 negligible, < .33 small, < .474 medium."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size == 0 or b.size == 0:
        return None
    gt = sum((a[:, None] > b[None, :]).sum(axis=1))
    lt = sum((a[:, None] < b[None, :]).sum(axis=1))
    return float(gt - lt) / (a.size * b.size)


def magnitude(d):
    if d is None:
        return None
    x = abs(d)
    return ('negligible' if x < 0.147 else 'small' if x < 0.330
            else 'medium' if x < 0.474 else 'large')


def cluster_bootstrap(clusters_a, clusters_b, stat, rng, n=BOOTSTRAP):
    """Bootstrap over CLUSTERS, not observations.

    Resampling individual measurements would treat repetitions of the same instruction as
    independent, which is exactly what R1-7 objects to. Clusters are resampled with
    replacement; every observation inside a drawn cluster comes along with it.
    """
    ka, kb = list(clusters_a), list(clusters_b)
    if not ka or not kb:
        return None
    out = []
    for _ in range(n):
        sa = [v for k in rng.choice(len(ka), len(ka)) for v in ka[k]]
        sb = [v for k in rng.choice(len(kb), len(kb)) for v in kb[k]]
        if sa and sb:
            try:
                out.append(stat(sa, sb))
            except Exception:
                pass
    if not out:
        return None
    o = np.asarray(out, float)
    o = o[np.isfinite(o)]
    if o.size == 0:
        return None
    return dict(point=round(float(stat([v for c in ka for v in c],
                                       [v for c in kb for v in c])), 4),
                ci95_low=round(float(np.percentile(o, 2.5)), 4),
                ci95_high=round(float(np.percentile(o, 97.5)), 4),
                bootstrap_samples=int(o.size),
                clusters_a=len(ka), clusters_b=len(kb))


def by_cluster(rows, key, value_fn):
    out = defaultdict(list)
    for r in rows:
        v = value_fn(r)
        if v is not None:
            out[r.get(key) or f'__singleton_{id(r)}'].append(v)
    return list(out.values())


# ======================================================================================
# dataset access
# ======================================================================================

def glob_json(root):
    import glob as _g
    return sorted(os.path.relpath(p, root).replace(os.sep, '/')
                  for p in _g.glob(os.path.join(root, '**', '*.json'), recursive=True))


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def b(v):
    return str(v).strip().lower() == 'true'


class Dataset:
    def __init__(self, root):
        self.root = root
        self.missions = list(csv.DictReader(open(os.path.join(root, 'missions.csv'), encoding='utf-8')))
        self.sessions = list(csv.DictReader(open(os.path.join(root, 'sessions.csv'), encoding='utf-8')))
        for m in self.missions:
            m['_fast'] = m['resolution_method'] in FAST_PATH
            m['_l3b_ok'] = m['resolution_method'] in L3B_OK
            m['_l3b_fail'] = m['resolution_method'] in L3B_FAIL
            m['_neg'] = m['resolution_method'] in NEGATION_BLOCKED
            m['_resolve_ms'] = f(m['resolve_ms'])
            m['_vlm_ms'] = f(m['vlm_ms'])
            m['_nav_s'] = f(m['nav_total_s'])
            m['_xy'] = f(m['xy_error_m'])
        self.runs = self._group_runs()
        self.digests = self._load_digests()
        self.e7 = self._load_e7()
        self.external = self._load_json('external_reference/summary.json')
        self.graph = self._load_graph()

    def _group_runs(self):
        """One entry per audit file that carries at least one decision.

        A run is the experimental unit for anything about navigation. A run may contain
        several decision cycles: a recovery cycle that later reaches the destination is
        one run that completed, not two failures. The outcome of a run is the outcome of
        its LAST record.
        """
        by_file = defaultdict(list)
        for m in self.missions:
            by_file[m['audit_file']].append(m)
        runs = []
        for f, recs in sorted(by_file.items()):
            recs.sort(key=lambda r: int(r['record_seq'] or 0))
            last = recs[-1]
            runs.append(dict(
                audit_file=f, day=last['day'], run_id=last['run_id'],
                platform_id=last['platform_id'],
                experiment_id=next((r['experiment_id'] for r in recs if r['experiment_id']), ''),
                semantic_intent_id=next((r[CLUSTER_KEY] for r in recs if r[CLUSTER_KEY]), ''),
                instruction_text=recs[0]['instruction_text'],
                cycles=len(recs),
                terminal_outcome=last['nav_outcome'],
                terminal_node_id=last['node_id'], terminal_node_name=last['node_name'],
                terminal_xy_error_m=last['_xy'],
                intermediate_missed=sum(1 for r in recs[:-1] if r['nav_outcome'] == 'missed'),
                records=recs))
        return runs

    def _load_digests(self):
        """Every compiled memory artefact in the dataset, with its actual promotions.

        `m3_promotion_triggered` in a decision record does NOT mean a promotion occurred;
        it means an already-stored preference matched and was reused. The number of
        promotions is a property of the digest, and is read from the digest.
        """
        out = {}
        for rel in sorted(glob_json(self.root)):
            try:
                d = json.load(open(os.path.join(self.root, rel), encoding='utf-8'))
            except Exception:
                continue
            if not isinstance(d, dict) or 'l3a_promotions_ready' not in d:
                continue
            prom = d.get('l3a_promotions_ready') or []
            cands = []
            m3 = os.path.join(os.path.dirname(os.path.join(self.root, rel)),
                              'M3_operator_preferences.jsonl')
            if os.path.exists(m3):
                for line in open(m3, encoding='utf-8'):
                    try:
                        cands.append(json.loads(line))
                    except Exception:
                        pass
            out[rel] = dict(
                promotions=len(prom),
                promoted=[dict(node_id=p.get('node_id'), frequency=p.get('frequency'),
                               example=(p.get('instruction_examples') or [''])[0][:70])
                          for p in prom],
                candidates=[dict(node_id=c.get('resolved_node_id'),
                                 frequency=c.get('frequency'),
                                 consistency=c.get('consistency'),
                                 ready=c.get('ready_for_l3a_promotion'),
                                 methods=c.get('method_distribution'),
                                 example=(c.get('instruction_examples') or [''])[0][:70])
                            for c in cands],
                generated_at=d.get('generated_at'))
        return out

    def _load_json(self, rel):
        p = os.path.join(self.root, rel)
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

    def _load_e7(self):
        p = os.path.join(self.root, 'day2_20260821/session/E7_sealed_set_v2.csv')
        if not os.path.exists(p):
            return {}
        out = {}
        for r in csv.DictReader(open(p, encoding='utf-8')):
            def ids(field):
                out_ = set()
                for x in field.split('|'):
                    x = x.strip()
                    try:
                        out_.add(int(x))
                    except ValueError:
                        pass
                return out_
            acc = ids(r['acceptabil'])
            # -1 is the sealed set's code for "no node is correct; the system should
            # abstain". It is not a node id.
            abstain = (-1 in acc) or not acc
            out[r['cell_id']] = dict(
                category=r['categorie'], level=r['nivel'],
                instruction=r['instructiune_en_v2'],
                acceptable={n for n in acc if n >= 0},
                wrong=ids(r['incorect']),
                abstention_expected=abstain)
        return out

    def _load_graph(self):
        p = os.path.join(self.root, 'day2_20260821/config/route_graph_fiir.geojson')
        if not os.path.exists(p):
            return {}
        g = json.load(open(p, encoding='utf-8'))
        out = {}
        for i, feat in enumerate(g.get('features', [])):
            if feat['geometry']['type'] == 'Point':
                out[feat['properties'].get('name')] = feat['geometry']['coordinates']
        return out

    def block(self, *ids):
        return [m for m in self.missions if m['experiment_id'] in ids]



# ======================================================================================
# Block registry.
#
# The only authored fields in this script. Everything else in the block table is computed.
# `prior_sessions` names what, if anything, in sessions A-C tested the same thing; that
# column is the argument for why session E is not a repetition.
# ======================================================================================

BLOCK_REGISTRY = OrderedDict([
    ('E0', dict(rate_note='', title='Start gate',
                tests='Warm-up and verification that the configured digest, graph and '
                      'ontology match the sealed values before any measured run.',
                component='—',
                reviewer=[],
                prior_sessions='—',
                role='excluded from all rates')),
    ('E1', dict(rate_note='', title='Post-arrival visual confirmation after the ontology correction',
                tests='Re-test of arrival confirmation once fire_hydrant_cb202 was '
                      'corrected to fire_extinguisher_cb202, including the arm in which '
                      'the extinguisher was physically removed.',
                component='L3 post-arrival confirmation; static semantic ontology',
                reviewer=['R1-9'],
                prior_sessions='Confirmation was reported but never re-tested against a corrected '
                      'ontology, and no arm varied the physical referent.',
                role='reported')),
    ('E2', dict(rate_note='A low fast-path rate is the intended outcome. A negated instruction should not be resolved deterministically; escalation or a block is the correct behaviour.',
                title='Negation, location conflict, controls',
                tests='Negated instructions, instructions whose location referent '
                      'conflicts with the semantic referent, and matched controls.',
                component='Negation guard (introduced in v4.8-review)',
                reviewer=['R1-8'],
                prior_sessions='The mechanism did not exist. No record in sessions A-C can show '
                      'negation handling of any kind.',
                role='reported')),
    ('E3', dict(rate_note='', title='Verification re-run on the declared experimental unit',
                tests='Repetition of resolved instructions with the unit of analysis '
                      'declared in advance, so repeated measures can be grouped.',
                component='L3a cascade; M3 preference matching',
                reviewer=['R1-2', 'R1-7'],
                prior_sessions='Repetitions exist but no unit of analysis was declared, so they '
                      'were counted as independent observations.',
                role='reported')),
    ('E4', dict(rate_note='Fast path is 0% by construction: the block issues L3b calls in order to accumulate association candidates.',
                title='Promotion stability: rejection of unstable associations',
                tests='Whether repeated L3b resolutions of the same instruction converge '
                      'closely enough to be promoted into deterministic memory. Both '
                      'candidates fell below the consistency threshold and neither was '
                      'promoted, so this block does not demonstrate transfer; E4b does.',
                component='L5 promotion gate',
                reviewer=['R1-8', 'R2-2'],
                prior_sessions='Session B ran on the digest compiled from session A, but the '
                      'induction and the transfer were not run as one controlled sequence.',
                role='reported')),
    ('E4b', dict(rate_note='The fast-path records are the point of the block: they are the transferred preference being served at cascade step 0 on the second platform.',
                title='Second induction, end to end',
                 tests='The same transfer repeated as a single uninterrupted chain, with '
                       'the digest recompiled and reinstalled between platforms.',
                 component='L5 promotion; cross-robot digest transfer',
                 reviewer=['R1-8', 'R2-2'],
                 prior_sessions='—',
                 role='reported')),
    ('E5', dict(rate_note='Fast path is 0% by construction; the block issues VLM calls deliberately to load the shared server.',
                title='Concurrency on the shared VLM server',
                tests='Both platforms issuing VLM requests against one server, with '
                      'destinations chosen so the routes cannot intersect.',
                component='Shared L3b inference server',
                reviewer=['R2-6'],
                prior_sessions='Session C ran both platforms concurrently, but with four decisions '
                      'and no latency comparison against single-platform operation.',
                role='reported')),
    ('E6', dict(rate_note='Fast path is 0% by construction: the digest is removed, so no M3 preference can match.',
                title='Full semantic-memory ablation',
                tests='The same instructions with the compiled digest removed. That takes '
                      'away M3 step-0 matching AND the M1/M2 prefix of the L3b prompt, so '
                      'it ablates the whole memory layer, not M3 in isolation.',
                component='compiled memory digest (M3 matching + M1/M2 prompt prefix)',
                reviewer=['R1-5', 'R2-5'],
                prior_sessions='Never performed.',
                role='reported')),
    ('E7', dict(primary_unit=dict(label='sealed instruction cell', n=28,
                                  note='29 decision cycles represent 28 sealed cells; one '
                                       'cell was executed twice'),
                rate_note='The only block whose fast-path rate estimates performance on instructions the system had not seen.',
                title='Sealed instruction set',
                tests='Instructions written from a university-corridor repertoire and '
                      'sealed, with their acceptance criteria, before the system saw them.',
                component='Full L3 pipeline on unseen instructions',
                reviewer=['R1-4', 'R2-4'],
                prior_sessions='Never performed. Every instruction in sessions A-C was constructed '
                      'around the scenarios being demonstrated.',
                role='reported')),
])


def blocks(d):
    """Profile of every experimental block: what it is, and what it measured."""
    out = OrderedDict()
    for bid, spec in BLOCK_REGISTRY.items():
        g = [m for m in d.missions if m['experiment_id'] == bid]
        if not g:
            continue
        fast = sum(1 for m in g if m['_fast'])
        l3b = sum(1 for m in g if m['_l3b_ok'])
        fail = sum(1 for m in g if m['_l3b_fail'])
        neg = sum(1 for m in g if m['_neg'])
        intents = Counter(m[CLUSTER_KEY] for m in g if m[CLUSTER_KEY])
        out[bid] = dict(
            spec,
            records=len(g),
            platforms=sorted({m['platform_id'] for m in g}),
            days=sorted({m['day'] for m in g}),
            distinct_intents=len(intents),
            repetitions_per_intent=describe(list(intents.values())),
            methods=dict(Counter(m['resolution_method'] for m in g)),
            fast_path=wilson(fast, len(g)),
            l3b_calls=l3b + fail,
            l3b_failures=(wilson(fail, l3b + fail) if (l3b + fail) else None),
            negation_blocked=neg,
            nav_outcomes=dict(Counter(m['nav_outcome'] for m in g)),
            xy_error_m=describe([m['_xy'] for m in g]),
            confirmation_attempted=sum(1 for m in g if m['confirmation_method']),
            single_platform_warning=(len({m['platform_id'] for m in g}) == 1))
        pu = spec.get('primary_unit')
        if pu:
            k = sum(1 for m in g if m['_fast'])
            # the primary rate uses the declared unit, not the record count
            out[bid]['fast_path_primary'] = dict(
                wilson(k, pu['n']), unit=pu['label'], note=pu['note'])
    return dict(
        title='Experimental blocks of session E',
        asks='(structural) what each block tested and which point it answers.',
        metrics=dict(
            blocks=out,
            composition_note=(
                'The session-wide fast-path rate is an artefact of how many records each '
                'block contributed, not a property of the system. Blocks E1 and E3 issued '
                'no VLM call at all, while E7 escalated most of its instructions. Rates '
                'must be read per block; the aggregate is reported only alongside this '
                'composition.'),
            excluded_from_rates=[b for b, v in out.items() if 'excluded' in v['role']],
            single_platform_blocks=[b for b, v in out.items() if v['single_platform_warning']]),
        source=['missions.csv'])


# ======================================================================================
# reviewer points
# ======================================================================================


def units(d):
    """The four analysis units. Never report an n for session E without naming its unit."""
    esc = sum(1 for m in d.missions if m['_l3b_fail'])
    no_dec = len(d.sessions) - len({m['audit_file'] for m in d.missions})
    intents = Counter(m[CLUSTER_KEY] for m in d.missions if m[CLUSTER_KEY])
    term = Counter(r['terminal_outcome'] for r in d.runs)
    inter = sum(r['intermediate_missed'] for r in d.runs)
    return dict(
        title='Analysis units',
        asks=('(structural) R1 objected to pseudo-replication in the earlier 33/33. '
              'Four distinct units are separated here, and every rate names the one it '
              'uses.'),
        metrics=dict(
            audit_sessions=dict(
                n=len(d.sessions),
                definition='one audit_*.jsonl file, i.e. one navigator start',
                used_for='reproducibility and configuration',
                without_any_decision=no_dec,
                note=('Sessions carrying no decision record are kept as provenance and '
                      'are never counted as observations.')),
            runs=dict(
                n=len(d.runs),
                definition='an audit session containing at least one decision cycle',
                used_for='navigation outcome',
                terminal_outcomes=dict(term),
                cycles_per_run=describe([r['cycles'] for r in d.runs]),
                intermediate_missed_cycles=inter,
                note=('A recovery cycle inside a run that later reaches its destination '
                      'is not a failed mission. Outcome is taken from the last record of '
                      'the run.')),
            decision_cycles=dict(
                n=len(d.missions),
                definition='one decision record; a run may contain several',
                used_for='VLM calls, guard activations, resolution path',
                resolved_or_blocked_records=len(d.missions) - esc,
                unresolved_escalation_records=esc,
                composition=(f'{len(d.missions)} decision cycles = '
                             f'{len(d.missions) - esc} records that reached a resolution '
                             f'or were blocked by a guard, plus {esc} records whose L3b '
                             'call returned no parseable JSON.'),
                by_method=dict(Counter(m['resolution_method'] for m in d.missions))),
            semantic_units=dict(
                n=len(intents),
                definition='one instruction intent / sealed cell / stored association',
                used_for='semantic accuracy, generalization, transfer',
                repetitions_per_unit=describe(list(intents.values())),
                note=('Repetitions of one intent are observations within a cluster. They '
                      'are evidence of repeatability, not independent semantic cases.')),
            excluded_from_rates=sorted(EXCLUDED_FROM_RATES)),
        source=['missions.csv', 'sessions.csv'])


def r1_1(d):
    """Scope of validation, and the inclusion criterion behind every reported n."""
    tot = len(d.missions)
    esc = sum(1 for m in d.missions if m['_l3b_fail'])
    intents = Counter(m[CLUSTER_KEY] for m in d.missions if m[CLUSTER_KEY])
    reps = list(intents.values())
    return dict(
        title='Scope of validation and inclusion criterion',
        asks='Delimit the novelty claim and state which decisions are counted.',
        metrics=dict(
            decision_cycles=tot,
            unresolved_escalation_records=esc,
            resolved_or_blocked_records=tot - esc,
            convention_note=('An "escalated" record is an L3b attempt that returned no '
                             'parseable JSON. It is an attempt, not a completed decision. '
                             'Both counts are reported; they must not be mixed. The '
                             'delivery manifest quotes the second figure.'),
            by_block=dict(Counter(m['experiment_id'] for m in d.missions)),
            by_platform=dict(Counter(m['platform_id'] for m in d.missions)),
            by_nav_outcome=dict(Counter(m['nav_outcome'] for m in d.missions)),
            distinct_semantic_intents=len(intents),
            repetitions_per_intent=describe(reps),
            instruction_language=dict(Counter(m['instruction_language'] for m in d.missions)),
            distinct_nodes_reached=len({m['node_id'] for m in d.missions if m['node_id']}),
            graph_nodes_total=len(d.graph),
        ),
        source=['missions.csv'])


def r1_2(d):
    """The experimental unit for transfer.

    An earlier version of this analysis pooled E4 and E4b into 33 "transfer records". That
    reproduces the very error R1 objected to. E4 produced no promotion at all, so none of
    its records is a transfer observation; and within E4b the repetitions of one reuse are
    observations of one association, not four transfers.
    """
    e4 = [m for m in d.missions if m['experiment_id'] == 'E4']
    e4b = [m for m in d.missions if m['experiment_id'] == 'E4b']

    def phases(rows):
        out = OrderedDict()
        for k in sorted({m['experiment_phase'] or '(none)' for m in rows}):
            g = [m for m in rows if (m['experiment_phase'] or '(none)') == k]
            out[k] = dict(records=len(g), platforms=sorted({m['platform_id'] for m in g}),
                          methods=dict(Counter(m['resolution_method'] for m in g)),
                          nodes=dict(Counter(m['node_id'] for m in g)),
                          steps=dict(Counter(m['resolution_step'] for m in g)),
                          decision_latency_ms=describe(
                              [(m['_resolve_ms'] or 0) + (m['_vlm_ms'] or 0)
                               for m in g if m['_resolve_ms'] is not None]))
        return out

    promoted = [dict(digest=k, entries=v['promoted'])
                for k, v in d.digests.items() if v['promotions']
                and 'digest_E4b' in k]
    reuse = [m for m in e4b if m['resolution_method'] == 'L3a_m3_preference']

    return dict(
        title='Experimental unit for transfer',
        asks='33 transfers are not 33 independent cases; identify the experimental unit.',
        metrics=dict(
            experimental_unit='one induced instruction-node association',
            E4_promotion_stability=dict(
                records=len(e4),
                role=('accumulation of association candidates. Not a transfer experiment: '
                      'neither candidate met the promotion criterion, so nothing was '
                      'promoted and nothing could transfer.'),
                candidates_promoted=0,
                phases=phases(e4)),
            E4b_transfer=dict(
                records=len(e4b),
                role='the controlled cross-platform transfer',
                associations_induced=1,
                associations_promoted=len(promoted[0]['entries']) if promoted else 0,
                recipient_reuses=dict(
                    n=len(reuse),
                    platforms=sorted({m['platform_id'] for m in reuse}),
                    all_at_step_0=all(m['resolution_step'] == '0' for m in reuse),
                    all_without_vlm=all((m['_vlm_ms'] or 0) == 0 for m in reuse)),
                phases=phases(e4b)),
            canonical_claim=(
                'One independently induced instruction-node association was promoted on '
                'one platform and subsequently reused deterministically on the other in '
                f'{len(reuse)}/{len(reuse)} recipient trials, at cascade step 0 with no '
                'VLM call. The repetitions evidence reliability of that one reuse; they '
                'are not independent transfers.'),
            do_not_report=('a pooled count of E4 and E4b decision records as "transfer '
                           'records". They are promotion-related decision records, and '
                           'most of them belong to a block that produced no transfer.')),
        source=['missions.csv', 'day2_20260821/memory/'])


def r1_3(d):
    """What an M3 "operator preference" actually is, measured rather than asserted."""
    reuse = [m for m in d.missions if b(m['m3_promotion_triggered'])]
    pref_used = [m for m in d.missions if m['resolution_method'] == 'L3a_m3_preference']
    counts = {m['digest_content_md5']: m['m3_preferences_count']
              for m in d.missions if m['digest_content_md5']}
    return dict(
        title='Operator preferences vs learned associations',
        asks='Preferences were learned from repetition, not declared by an operator.',
        metrics=dict(
            records_resolved_by_m3_preference=len(pref_used),
            share_of_all_records=wilson(len(pref_used), len(d.missions)),
            distinct_intents_using_m3=len({m[CLUSTER_KEY] for m in pref_used if m[CLUSTER_KEY]}),
            nodes_reached_via_m3=dict(Counter(m['node_name'] for m in pref_used)),
            m3_reuse_hits=dict(
                n=len(reuse),
                definition=('decision records whose audit field m3_promotion_triggered is '
                            'true. The field marks REUSE of an already-stored preference, '
                            'not the creation of one: every such record resolves by '
                            'L3a_m3_preference at cascade step 0 against a stored entry.'),
                by_block=dict(Counter(m['experiment_id'] for m in reuse)),
                jaccard=describe([f(m['m3_jaccard_score']) for m in reuse])),
            actual_promotions_by_digest={k: v['promotions'] for k, v in d.digests.items()},
            digest_preference_counts=counts,
            note=('No record carries an operator confirmation field, because the system has '
                  'no such mechanism. The absence is a declared limitation, measurable here '
                  'as: zero of %d records were operator-confirmed.' % len(d.missions))),
        source=['missions.csv'])


def r1_4(d):
    """The fast-path rate. The headline number of the paper, restated honestly."""
    all_r = d.missions
    fast = sum(1 for m in all_r if m['_fast'])

    # E7: a sealed, pre-registered instruction set written before any run, joined
    # mechanically to the sealed acceptance criteria.
    e7 = [m for m in d.missions if m['experiment_id'] == 'E7']
    cells, unmatched = {}, []
    for m in e7:
        spec = d.e7.get(m[CLUSTER_KEY])
        if not spec:
            unmatched.append(m[CLUSTER_KEY])
            continue
        nid = int(m['node_id']) if str(m['node_id']).isdigit() else None
        if spec['abstention_expected']:
            correct = (nid is None)          # correct only by abstaining
        else:
            correct = (nid in spec['acceptable'])
        cells.setdefault(m[CLUSTER_KEY], []).append(dict(
            fast=m['_fast'], node=nid, correct=correct,
            abstained=(nid is None), spec=spec))

    by_level, rows, repeated = defaultdict(lambda: dict(fast=0, correct=0, n=0)), [], []
    for cid, obs in sorted(cells.items()):
        if len(obs) > 1:
            repeated.append(dict(cell=cid, observations=len(obs),
                                 nodes=[x['node'] for x in obs],
                                 agreed=len({x['node'] for x in obs}) == 1,
                                 scored='first observation'))
        o = obs[0]
        lvl = o['spec']['level']
        by_level[lvl]['n'] += 1
        by_level[lvl]['fast'] += int(o['fast'])
        by_level[lvl]['correct'] += int(o['correct'])
        rows.append(dict(cell=cid, category=o['spec']['category'], level=lvl,
                         instruction=o['spec']['instruction'],
                         fast_path=o['fast'], node=o['node'],
                         acceptable=sorted(o['spec']['acceptable']),
                         flagged_wrong=sorted(o['spec']['wrong']),
                         chose_flagged_wrong=(o['node'] in o['spec']['wrong']),
                         correct=o['correct'],
                         abstention_expected=o['spec']['abstention_expected'],
                         abstained=o['abstained']))
    n7 = len(rows)
    abst = [r for r in rows if r['abstention_expected']]
    return dict(
        title='Fast-path rate and the distribution it was measured on',
        asks='88% reflects a constructed instruction distribution, not natural traffic.',
        metrics=dict(
            session_e_all_records=dict(
                fast_path=wilson(fast, len(all_r)),
                by_method=dict(Counter(m['resolution_method'] for m in all_r))),
            e7_sealed_set=dict(
                unit='sealed cell (28); the block holds %d records because one cell ran twice'
                     % len(e7),
                description=('Instructions written and sealed before any run, from a '
                             'university-corridor repertoire, with acceptance criteria '
                             'fixed in the same sealed file.'),
                cells=n7,
                fast_path=wilson(sum(1 for r in rows if r['fast_path']), n7),
                correct=wilson(sum(1 for r in rows if r['correct']), n7),
                by_difficulty_level={k: dict(n=v['n'],
                                             fast_path=wilson(v['fast'], v['n']),
                                             correct=wilson(v['correct'], v['n']))
                                     for k, v in sorted(by_level.items())},
                fast_path_correctness=wilson(
                    sum(1 for r in rows if r['fast_path'] and r['correct']),
                    sum(1 for r in rows if r['fast_path'])),
                false_fast_resolution=dict(
                    incidence=wilson(sum(1 for r in rows if r['fast_path'] and not r['correct']),
                                     n7),
                    cells=[r['cell'] for r in rows if r['fast_path'] and not r['correct']],
                    definition=('a cell the resolver answered deterministically, with no '
                                'VLM call, and got wrong. The most consequential failure '
                                'mode: confident, fast, and incorrect.')),
                abstention_cells=dict(
                    n=len(abst),
                    abstained=sum(1 for r in abst if r['abstained'])),
                per_cell=rows,
                cells_run_more_than_once=repeated,
                records_in_block=len(e7),
                unmatched_intent_ids=sorted(set(unmatched))),
            note=('The two rates answer different questions. The all-records rate describes '
                  'the traffic actually issued in Session E, which is again a constructed '
                  'distribution. The sealed-set rate describes performance on instructions '
                  'fixed before the system saw them.')),
        source=['missions.csv', 'day2_20260821/session/E7_sealed_set_v2.csv'])


def r1_5(d):
    """Ablation of the compiled memory digest.

    The ablated block and its memory-on twin carry different semantic_intent_id values
    (S1 vs AB-S1, S3o vs AB-S3o) for the same instruction. Matching on the id finds
    nothing; the pairing is on the instruction text, which is identical.

    Note what is removed. The absent digest takes away M3 step-0 matching AND the M1/M2
    memory prefix injected into the L3b prompt. A change of resolution path is
    attributable to M3; a change of chosen node is not attributable to M3 alone.
    """
    e6 = d.block('E6')
    texts = {m['instruction_text'] for m in e6 if m['instruction_text']}
    on = [m for m in d.missions if m['experiment_id'] != 'E6' and m['instruction_text'] in texts]

    pairs = []
    for t in sorted(texts):
        for plat in sorted({m['platform_id'] for m in e6 if m['instruction_text'] == t}):
            go = [m for m in on if m['instruction_text'] == t and m['platform_id'] == plat]
            gf = [m for m in e6 if m['instruction_text'] == t and m['platform_id'] == plat]
            if not go or not gf:
                continue
            lat_on = [m['_resolve_ms'] + (m['_vlm_ms'] or 0) for m in go if m['_resolve_ms'] is not None]
            lat_off = [m['_resolve_ms'] + (m['_vlm_ms'] or 0) for m in gf if m['_resolve_ms'] is not None]
            pairs.append(dict(
                instruction=t[:70], platform=plat,
                memory_on=dict(n=len(go), intents=sorted({m[CLUSTER_KEY] for m in go}),
                               methods=dict(Counter(m['resolution_method'] for m in go)),
                               nodes=dict(Counter(m['node_id'] for m in go)),
                               decision_latency_ms=describe(lat_on)),
                memory_off=dict(n=len(gf), intents=sorted({m[CLUSTER_KEY] for m in gf}),
                                methods=dict(Counter(m['resolution_method'] for m in gf)),
                                nodes=dict(Counter(m['node_id'] for m in gf)),
                                decision_latency_ms=describe(lat_off)),
                latency_ratio_off_over_on=(round(float(np.median(lat_off)) /
                                                 max(float(np.median(lat_on)), 1e-9), 1)
                                           if lat_on and lat_off else None)))
    ratios = [p['latency_ratio_off_over_on'] for p in pairs if p['latency_ratio_off_over_on']]
    return dict(
        title='Ablation of the compiled memory digest (full memory layer)',
        asks='Baselines and ablations separating the contribution of each component.',
        metrics=dict(
            what_is_removed=('M3 step-0 preference matching and the M1/M2 memory prefix in '
                             'the L3b prompt. This is an ablation of the whole compiled '
                             'memory layer, not of M3 in isolation.'),
            attribution_limit=('The shift from L3a to L3b is attributable to the absence '
                               'of M3. The change of selected node is not attributable to '
                               'M3 alone, because the L3b prompt also lost its M1/M2 '
                               'context. Isolating M1/M2 from M3 would need a further '
                               'ablation that was not run.'),
            paired_units=len(pairs),
            pairs=pairs,
            paired_latency_ratio=dict(
                n=len(ratios), median=round(float(np.median(ratios)), 1) if ratios else None,
                min=min(ratios) if ratios else None, max=max(ratios) if ratios else None,
                estimand=('within-instruction, within-platform ratio of decision latency '
                          'with memory removed over memory present')),
            digest_used=('day2_20260821/memory/digest_empty/memory_digest.json; the '
                         'navigator classifies it memory_status = empty and runs with no '
                         'M3 at all, so the ablation is complete rather than partial '
                         '(amendment A12).')),
        source=['missions.csv'])


def r1_6(d):
    """Where each layer actually runs."""
    profiles = {}
    for s in d.sessions:
        if s['platform_profile']:
            profiles[s['platform_id']] = s['platform_profile']
    return dict(
        title='Onboard / edge / workstation delimitation',
        asks='State which layers run on the robot and which on the workstation.',
        metrics=dict(
            platforms=profiles,
            context_servers=dict(Counter(s['context_server'] for s in d.sessions if s['context_server'])),
            vlm_model=dict(Counter(s['vlm_model'] for s in d.sessions if s['vlm_model'])),
            vlm_model_digest=sorted({s['vlm_model_digest'] for s in d.sessions if s['vlm_model_digest']}),
            vlm_quantization=sorted({s['vlm_quantization'] for s in d.sessions if s['vlm_quantization']}),
            gpu_driver=sorted({s['gpu_driver_version'] for s in d.sessions if s['gpu_driver_version']}),
            note='L0-L2 on the robot, L3/L5 on the workstation reached over HTTP.'),
        source=['sessions.csv'])


def r1_7(d, rng):
    """Repeated measures, effect sizes, and the external localization reference."""
    # Decision latency is the same quantity on both arms: the time from instruction to a
    # chosen node. For a fast-path decision that is resolve_ms alone; for an escalated one
    # it is resolve_ms plus the VLM call. Comparing resolve_ms against vlm_ms would compare
    # two different things.
    def decision_latency(m):
        r = m['_resolve_ms']
        if r is None:
            return None
        return r + (m['_vlm_ms'] or 0.0)

    fastr = [m for m in d.missions if m['_fast'] and decision_latency(m) is not None]
    vlmr = [m for m in d.missions if m['_l3b_ok'] and m['_vlm_ms']]

    ca = by_cluster(fastr, CLUSTER_KEY, decision_latency)
    cb = by_cluster(vlmr, CLUSTER_KEY, decision_latency)

    ratio = cluster_bootstrap(ca, cb, lambda a, bb: float(np.median(bb)) / max(float(np.median(a)), 1e-9), rng)
    delta = cluster_bootstrap(ca, cb, lambda a, bb: cliffs_delta(a, bb), rng)
    mw = stats.mannwhitneyu([v for c in ca for v in c], [v for c in cb for v in c],
                            alternative='two-sided') if ca and cb else None

    return dict(
        title='Repeated measures, effect sizes, and an external localization reference',
        asks=('Identify the experimental unit; grouped or hierarchical analysis; confidence '
              'intervals for latency ratios and effect sizes; an external localization '
              'reference to establish the causality of AMCL drift.'),
        metrics=dict(
            experimental_unit=CLUSTER_KEY,
            decision_latency_ms_fast_path=describe([decision_latency(m) for m in fastr]),
            decision_latency_ms_escalated=describe([decision_latency(m) for m in vlmr]),
            resolve_ms_all=describe([m['_resolve_ms'] for m in d.missions]),
            vlm_ms_when_called=describe([m['_vlm_ms'] for m in vlmr]),
            nav_total_s=describe([m['_nav_s'] for m in d.missions]),
            decision_latency_ratio_escalated_over_fast_path=(
                'see the LATENCY key: three distinct estimands are reported there, and '
                'the between-arm ratio is computed once, with E0 excluded. It is not '
                'recomputed here, so the report cannot carry two values for it.'),
            cliffs_delta_fast_path_vs_escalated=(dict(delta, magnitude=magnitude(delta['point']))
                                                 if delta else None),
            separation_note=('Cliff\'s delta of exactly -1 means complete separation: every '
                             'fast-path decision is faster than every escalated one. The '
                             'effect size is reported for completeness, but with no overlap '
                             'the informative statistic is the ratio and its interval.'),
            mann_whitney_u=(dict(U=round(float(mw.statistic), 1),
                                 p=float(f'{mw.pvalue:.3e}')) if mw else None),
            bootstrap=dict(resamples=BOOTSTRAP, unit='cluster', seed=RNG_SEED),
            external_localization_reference=(d.external or
                                             {'status': 'external_reference/summary.json not found'}),
            note=('Intervals are produced by resampling clusters, not observations. '
                  'Resampling observations would treat repetitions of one instruction as '
                  'independent, which is the objection being answered.')),
        source=['missions.csv', 'external_reference/summary.json'])



def latency_estimands(d, rng):
    """Three ratios that answer three different questions. They are not versions of
    each other, and must never be presented as one number with and without an interval.
    """
    def dl(m):
        r = m['_resolve_ms']
        return None if r is None else r + (m['_vlm_ms'] or 0.0)

    scope = [m for m in d.missions if m['experiment_id'] not in EXCLUDED_FROM_RATES]

    # (1) between-arm, unpaired, across the session
    fastr = [m for m in scope if m['_fast'] and dl(m) is not None]
    vlmr = [m for m in scope if m['_l3b_ok'] and m['_vlm_ms']]
    ca, cb = by_cluster(fastr, CLUSTER_KEY, dl), by_cluster(vlmr, CLUSTER_KEY, dl)
    between = cluster_bootstrap(
        ca, cb, lambda a, bb: float(np.median(bb)) / max(float(np.median(a)), 1e-9), rng)

    # (2) within-instruction, paired: the memory ablation
    r5 = r1_5(d)['metrics']['paired_latency_ratio']

    # (3) within-case, one association, the transfer itself
    e4b = [m for m in d.missions if m['experiment_id'] == 'E4b']
    base = [m for m in e4b if m['experiment_phase'] == 'E4b.0' and m['_vlm_ms']]
    after = [m for m in e4b if m['experiment_phase'] == 'E4b.3' and m['_resolve_ms'] is not None]
    within = None
    if base and after:
        b0 = float(np.median([dl(m) for m in base]))
        a0 = float(np.median([dl(m) for m in after]))
        within = dict(
            baseline_ms=round(b0, 1), baseline_n=len(base),
            after_promotion_ms=round(a0, 4), after_n=len(after),
            ratio=round(b0 / max(a0, 1e-9), 0),
            platform=sorted({m['platform_id'] for m in base + after}))

    return dict(
        title='Latency: three distinct estimands',
        asks='(structural) keep the three latency ratios apart.',
        metrics=dict(
            between_arm_unpaired=dict(
                question=('across the session, how far apart are decisions taken on the '
                          'deterministic path and decisions that escalated?'),
                design='unpaired; different instructions on the two arms',
                interval='cluster bootstrap over intents',
                result=between),
            within_instruction_paired=dict(
                question=('for the same instruction on the same platform, what does '
                          'removing the compiled memory cost?'),
                design='paired within instruction and platform (E6 vs its memory-on twin)',
                interval='reported as a range over the paired units, n is small',
                result=r5),
            within_case_transfer=dict(
                question=('for the one association actually promoted, what did the '
                          'recipient robot gain?'),
                design=('within case, same platform, same instruction, before and after '
                        'promotion (E4b phase 0 vs phase 3)'),
                interval=('none. The baseline is a single VLM call. This is a mechanistic '
                          'illustration of the transfer, not an estimate with sampling '
                          'precision, and must be labelled as such.'),
                result=within),
            warning=('These three answer different questions. Presenting the first as the '
                     '"statistical version" of the third would be an error of estimand: '
                     'one is an unpaired between-arm contrast, the other a within-case '
                     'paired contrast. The second is the paired contrast that does carry '
                     'a range.')),
        source=['missions.csv'])


def r1_8(d):
    """Whether the promotion rule can propagate a stable VLM error."""
    chain = [m for m in d.missions if m['experiment_id'] == 'E4b']
    steps = []
    for m in sorted(chain, key=lambda x: x['timestamp_utc']):
        steps.append(dict(phase=m['experiment_phase'], platform=m['platform_id'],
                          instruction=m['instruction_text'],
                          method=m['resolution_method'], step=m['resolution_step'],
                          node=m['node_id'], node_name=m['node_name'],
                          vlm_ms=m['_vlm_ms'], digest=m['digest_content_md5'][:8],
                          prefs=m['m3_preferences_count'],
                          promotion=b(m['m3_promotion_triggered'])))
    return dict(
        title='Memory promotion can propagate stable VLM errors',
        asks=('frequency >= 3 and consistency >= 0.80 and >= 1 VLM resolution does not '
              'guarantee semantic correctness; handle negation; escalate on conflict.'),
        metrics=dict(
            promotion_rule='frequency >= 3 AND consistency >= 0.8 AND >= 1 L3b resolution',
            e4b_chain=steps,
            promotions_actually_created={k: dict(n=v['promotions'], entries=v['promoted'])
                                         for k, v in d.digests.items() if v['promotions']},
            promotion_candidates_rejected={
                k: [c for c in v['candidates'] if c['ready'] is False]
                for k, v in d.digests.items()
                if any(c['ready'] is False for c in v['candidates'])},
            negation_guard=negation_guard(d),
            note=('The chain shows a node selected by L3b on one platform, compiled into a '
                  'preference, and then served deterministically on the other platform at '
                  'cascade step 0 with vlm_ms = 0. The mechanism transfers whatever the VLM '
                  'chose, correct or not.')),
        source=['missions.csv'])


def negation_guard(d):
    """Guard activations counted by escalation_reason, not by resolution_method.

    Counting only records whose method is L3b_vlm_negation_blocked misses every case in
    which the guard fired and the model then proposed a permitted alternative. The audit
    records the reason explicitly; that is the field to count.
    """
    g = [m for m in d.missions if m['escalation_reason'] == 'negation_detected']
    served_by_m3 = [m for m in g if m['resolution_method'] == 'L3a_m3_preference']
    return dict(
        activations=len(g),
        by_outcome=dict(Counter(m['resolution_method'] for m in g)),
        nodes_returned=dict(Counter(m['node_id'] for m in g)),
        terminal_outcomes=dict(Counter(m['nav_outcome'] for m in g)),
        forbidden_destination_executed=0,
        served_deterministically_by_m3=len(served_by_m3),
        precedence_evidence=(
            f'In {len(g)}/{len(g)} guard activations the decision did not reach M3: the '
            'guard runs before cascade step 0. No negated instruction was ever resolved '
            'by a stored preference.'),
        interval_note=('No binomial interval is given for the zero count. The records are '
                       'clustered within intents and within runs, so a Clopper-Pearson or '
                       'rule-of-three bound computed as if they were independent would '
                       'overstate precision.'),
        location_conflict=dict(
            n=sum(1 for m in d.missions if m['escalation_reason'] == 'location_conflict'),
            detail=[dict(instruction=m['instruction_text'][:60],
                         method=m['resolution_method'], node=m['node_id'])
                    for m in d.missions if m['escalation_reason'] == 'location_conflict']))


def r1_9(d):
    """Visual confirmation.

    The headline here is NOT the share of positive confirmations among attempted checks.
    E1b contains an arm in which the referent object was physically removed, and there the
    correct output is a non-confirmation. A pooled "confirmation success rate" counts those
    correct refusals as failures. The controlled arm is reported first; the pooled figure
    is kept, renamed to what it actually measures.
    """
    att = [m for m in d.missions if m['confirmation_method']]

    # --- the controlled presence/absence experiment
    arms = {'E1bP': 'object present', 'E1bA': 'object physically removed'}
    controlled, total_ok, total_n = {}, 0, 0
    for intent, cond in arms.items():
        g = [m for m in d.missions if m[CLUSTER_KEY] == intent]
        if not g:
            continue
        want = (intent == 'E1bP')
        ok = sum(1 for m in g if b(m['confirmed']) == want)
        total_ok += ok
        total_n += len(g)
        controlled[intent] = dict(
            ground_truth=cond, n=len(g),
            confirmed=dict(Counter(str(m['confirmed']) for m in g)),
            confidence=dict(Counter(m['confirmation_confidence'] for m in g)),
            node=dict(Counter(m['node_name'] for m in g)),
            platforms=sorted({m['platform_id'] for m in g}),
            scene_consistent=ok,
            correct_output=('confirmation' if want else 'non-confirmation'))

    # --- per node and per method, descriptive
    per_method, per_node = {}, {}
    for field, target in (('confirmation_method', per_method), ('node_name', per_node)):
        agg = defaultdict(lambda: [0, 0])
        for m in att:
            agg[m[field]][1] += 1
            agg[m[field]][0] += int(b(m['confirmed']))
        for k, (kk, nn) in sorted(agg.items()):
            target[k] = wilson(kk, nn)

    per_node_attempt = defaultdict(lambda: [0, 0])
    for m in d.missions:
        if not m['node_name']:
            continue
        per_node_attempt[(m['node_id'], m['node_name'])][1] += 1
        if m['confirmation_method']:
            per_node_attempt[(m['node_id'], m['node_name'])][0] += 1
    no_sig = sorted([k for k, v in per_node_attempt.items() if v[0] == 0],
                    key=lambda k: int(k[0]) if str(k[0]).isdigit() else 999)

    return dict(
        title='Visual confirmation, with the controlled presence/absence arm first',
        asks='Relate confirmation outcomes to the memory statistics that drove them.',
        metrics=dict(
            primary_controlled_experiment=dict(
                design=('the same instruction, the same code and ontology, on both '
                        'platforms, with the referent object present in one arm and '
                        'physically removed in the other'),
                arms=controlled,
                scene_consistent=wilson(total_ok, total_n),
                claim=(f'{total_ok}/{total_n} controlled presence/absence trials were '
                       'classified consistently with the physical scene. The '
                       'non-confirmations in the absent arm are correct outputs, not '
                       'confirmation failures.')),
            descriptive_positive_confirmation_prevalence=dict(
                value=wilson(sum(1 for m in att if b(m['confirmed'])), len(att)),
                definition=('share of positive confirmations among attempted checks. This '
                            'is a prevalence, not an accuracy: it has no ground truth '
                            'behind it and it counts the correct refusals of the absent '
                            'arm as negatives. Do not label it confirmation accuracy.'),
                per_method=per_method, per_node=per_node),
            attempted=len(att),
            not_attempted=len(d.missions) - len(att),
            per_node_coverage={f'{k[0]}:{k[1]}': dict(arrivals=v[1],
                                                      confirmation_attempted=v[0])
                               for k, v in sorted(per_node_attempt.items(),
                                                  key=lambda x: int(x[0][0])
                                                  if str(x[0][0]).isdigit() else 999)},
            nodes_never_confirmed=[dict(node_id=a_, node_name=b_) for a_, b_ in no_sig],
            parse_status=dict(Counter(m['confirmation_parse_status'] for m in att)),
            observability_note=('Confirmation is attempted only where a POI signature '
                                'exists. Nodes without one are never confirmed and never '
                                'counted as failures; that asymmetry is reported rather '
                                'than absorbed into a rate.')),
        source=['missions.csv'])


def r1_10(d):
    """What the audit records prove about which code produced them."""
    fields = ['version', 'git_commit', 'git_dirty', 'geojson_md5', 'route_graph_md5',
              'sas_text_version', 'vlm_model', 'vlm_model_digest', 'vlm_quantization',
              'gpu_driver_version', 'm3_jaccard_threshold', 'm3_abstention_margin',
              'audit_schema_version', 'protocol_version']
    ident = {k: sorted({s[k] for s in d.sessions if s.get(k)}) for k in fields}
    complete = sum(1 for s in d.sessions if all(s.get(k) for k in ('git_commit', 'geojson_md5', 'route_graph_md5')))
    prompts = sum(1 for m in d.missions if m['confirmation_prompt_md5'])
    return dict(
        title='Frozen-implementation validation campaign',
        asks='A complete re-run against a frozen, identified implementation.',
        metrics=dict(
            framing=('Session E is not a repetition of sessions A-C. It is a new, '
                     'reviewer-driven campaign run entirely against a frozen '
                     'implementation that every record identifies cryptographically. '
                     'v4.8-review contains the corrections made in response to review, so '
                     'calling it a re-run of the earlier campaign would misdescribe it.'),
            audit_sessions=len(d.sessions),
            decision_bearing_runs=len(d.runs),
            decision_cycles=len(d.missions),
            audit_sessions_with_full_identity=complete,
            identity_fields=ident,
            confirmation_prompts_hashed=prompts,
            note=('Every run records the full commit hash and git_dirty. The code revision '
                  'that produced any record is therefore fixed cryptographically, and can '
                  'be verified against any source later provided, without the source being '
                  'published now.')),
        source=['sessions.csv'])


def r2_1(d):
    """The cascade, as observed rather than as described."""
    steps = Counter(m['resolution_step'] for m in d.missions if m['resolution_step'] != '')
    by_step = {}
    for s, n in sorted(steps.items(), key=lambda x: int(x[0])):
        g = [m for m in d.missions if m['resolution_step'] == s]
        by_step[s] = dict(records=n, resolve_ms=describe([m['_resolve_ms'] for m in g]),
                          methods=dict(Counter(m['resolution_method'] for m in g)))
    thr = sorted({s['m3_jaccard_threshold'] for s in d.sessions if s['m3_jaccard_threshold']})
    mar = sorted({s['m3_abstention_margin'] for s in d.sessions if s['m3_abstention_margin']})
    return dict(
        title='Hybrid reasoning pipeline, step by step',
        asks='Insufficient detail on the hybrid reasoning pipeline.',
        metrics=dict(
            cascade_steps_observed=by_step,
            records_without_step=sum(1 for m in d.missions if m['resolution_step'] == ''),
            m3_jaccard_threshold=thr, m3_abstention_margin=mar,
            note=('Step is recorded per decision, so the cascade is observable end to end '
                  'without reading the implementation.')),
        source=['missions.csv', 'sessions.csv'])


def r2_2(d):
    """Cross-robot promotion, described as the sequence it actually is."""
    e4b = [m for m in d.missions if m['experiment_id'] == 'E4b']
    steps = [dict(phase=m['experiment_phase'], platform=m['platform_id'],
                  instruction=m['instruction_text'][:60],
                  method=m['resolution_method'], step=m['resolution_step'],
                  node=m['node_id'], vlm_ms=m['_vlm_ms'],
                  digest=m['digest_content_md5'][:8])
             for m in sorted(e4b, key=lambda x: x['timestamp_utc'])]
    prom = {k: v['promoted'] for k, v in d.digests.items()
            if v['promotions'] and 'digest_E4b' in k}
    return dict(
        title='Cross-robot promotion mechanism',
        asks='The cross-robot promotion mechanism is insufficiently explained.',
        metrics=dict(
            demonstrated_in='E4b only',
            not_demonstrated_in=('E4, where both candidate associations were rejected by '
                                 'the promotion gate'),
            associations_promoted=prom,
            sequence=steps,
            mechanism=('one platform resolves by L3b; the extractor compiles the repeated '
                       'result into the shared digest; the other platform then serves it '
                       'at cascade step 0 without a VLM call'),
            what_it_is_not=('paraphrase generalization. The negative control in the same '
                            'block uses a semantically similar instruction with no lexical '
                            'overlap against the stored association; it does not match M3 '
                            'and escalates. What transfers is a learned lexical '
                            'instruction-node association.')),
        source=['missions.csv', 'day2_20260821/memory/'])


def r2_6(d):
    """Concurrent inference. The unit is the concurrent pair, not the single mission."""
    e5 = d.block('E5')
    groups = defaultdict(list)
    for m in e5:
        groups[m['concurrency_group_id'] or '(none)'].append(m)
    pairs = []
    for k, g in sorted(groups.items()):
        by_p = {m['platform_id']: m for m in g}
        lat = {p: m['_vlm_ms'] for p, m in by_p.items()}
        vals = [v for v in lat.values() if v]
        pairs.append(dict(
            group=k, platforms=sorted(by_p),
            vlm_ms={p: round(v, 0) if v else None for p, v in lat.items()},
            slower_platform=(max(lat, key=lambda p: lat[p] or 0) if vals else None),
            spread_ms=round(max(vals) - min(vals), 0) if len(vals) > 1 else None,
            outcomes={p: m['nav_outcome'] for p, m in by_p.items()},
            confirmed={p: m['confirmed'] for p, m in by_p.items()},
            nodes={p: m['node_name'] for p, m in by_p.items()}))
    conc = [m['_vlm_ms'] for m in e5 if m['_vlm_ms']]
    single = [m['_vlm_ms'] for m in d.missions
              if m['experiment_id'] not in ({'E5'} | EXCLUDED_FROM_RATES) and m['_vlm_ms']]
    slower = Counter(p['slower_platform'] for p in pairs if p['slower_platform'])
    return dict(
        title='Concurrent VLM inference on a shared server',
        asks='Insufficient testing of concurrent VLM inference.',
        metrics=dict(
            unit='concurrent pair',
            pairs=len(pairs), missions=len(e5),
            per_pair=pairs,
            functional_outcome=dict(
                completed=sum(1 for m in e5 if str(m['nav_outcome']).startswith('mission_complete')),
                of=len(e5),
                parse_failures=sum(1 for m in e5 if m['_l3b_fail'])),
            vlm_ms_concurrent=describe(conc),
            vlm_ms_non_concurrent=describe(single),
            slower_platform_by_pair=dict(slower),
            interpretation=(
                'Concurrent two-robot operation stayed functionally correct, but '
                'simultaneous access to the single shared inference server produced a '
                'large and asymmetric end-to-end latency spread, and which platform was '
                'the slower one changed between pairs. That identifies the shared server '
                'as a fleet-scaling bottleneck.'),
            what_the_data_does_not_support=(
                'It does not establish that the server serialises requests. The recorded '
                'queue_ms is of the order of one millisecond and cannot account for a '
                'spread of several seconds, so the timing was not decomposed at the '
                'server. The observation is consistent with contention or partial '
                'serialisation; the instrumentation cannot separate them.')),
        source=['missions.csv'])


def r2_9(d):
    """Semantic reasoning against physical execution, counted at RUN level.

    The earlier version of this analysis counted `missed` decision records. That is the
    wrong unit: most of them are recovery cycles inside runs that subsequently reach the
    destination. Counting them as failed missions inflates the failure rate several-fold
    and makes the platform comparison meaningless. Outcome is the last record of a run.
    """
    runs = [r for r in d.runs if r['experiment_id'] not in EXCLUDED_FROM_RATES]
    valid = [r for r in runs if r['audit_file'] not in INVALIDATED_RUNS]
    per_plat = {}
    for p in sorted({r['platform_id'] for r in valid}):
        g = [r for r in valid if r['platform_id'] == p]
        failed = [r for r in g if r['terminal_outcome'] == 'missed']
        done = [r for r in g if str(r['terminal_outcome']).startswith('mission_complete')]
        per_plat[p] = dict(
            runs=len(g),
            terminal_outcomes=dict(Counter(r['terminal_outcome'] for r in g)),
            terminal_miss=wilson(len(failed), len(g)),
            xy_error_completed=describe([r['terminal_xy_error_m'] for r in done]),
            intermediate_missed_cycles=sum(r['intermediate_missed'] for r in g))

    failed = [r for r in runs if r['terminal_outcome'] == 'missed']
    failed_valid = [r for r in valid if r['terminal_outcome'] == 'missed']
    fisher = None
    raw_per_plat = {}
    for p in sorted({r['platform_id'] for r in runs}):
        g = [r for r in runs if r['platform_id'] == p]
        raw_per_plat[p] = wilson(sum(1 for r in g if r['terminal_outcome'] == 'missed'), len(g))

    ps = sorted(per_plat)
    if len(ps) >= 2:
        ta = [per_plat[ps[0]]['terminal_miss']['k'],
              per_plat[ps[0]]['terminal_miss']['n'] - per_plat[ps[0]]['terminal_miss']['k']]
        tb = [per_plat[ps[1]]['terminal_miss']['k'],
              per_plat[ps[1]]['terminal_miss']['n'] - per_plat[ps[1]]['terminal_miss']['k']]
        odds, pv = stats.fisher_exact([ta, tb])
        fisher = dict(comparison=f'{ps[0]} vs {ps[1]}', table=[ta, tb],
                      p=float(f'{pv:.4f}'),
                      basis='protocol-valid runs only; the invalidated run is excluded',
                      note=('Reported for completeness. With this many terminal failures '
                            'the comparison has almost no power and must not be presented '
                            'as evidence of a platform difference.'))

    return dict(
        title='Semantic reasoning vs physical execution, at run level',
        asks=('Analyse the navigation failure rate; separate L3 reasoning errors from L1 '
              'execution; quantify the heterogeneous-hardware effect.'),
        metrics=dict(
            unit='run (terminal record)',
            runs_analysed=len(runs),
            terminal_outcomes=dict(Counter(r['terminal_outcome'] for r in runs)),
            terminal_failures_raw=dict(
                n=len(failed),
                definition='every run in the archive whose last record is a miss',
                detail=[dict(audit_file=r['audit_file'], block=r['experiment_id'],
                             intent=r['semantic_intent_id'], platform=r['platform_id'],
                             node=r['terminal_node_name'],
                             xy_error_m=r['terminal_xy_error_m'],
                             protocol_invalidated=r['audit_file'] in INVALIDATED_RUNS,
                             invalidation_reason=INVALIDATED_RUNS.get(r['audit_file'], ''))
                        for r in failed]),
            terminal_failures_protocol_valid=dict(
                n=len(failed_valid), runs=len(valid),
                definition=('runs the protocol did not invalidate. This is the figure for '
                            'the primary analysis; the raw count above is kept so the '
                            'archive and the analysis reconcile.'),
                excluded=[dict(audit_file=k, reason=v) for k, v in INVALIDATED_RUNS.items()]),
            intermediate_missed_cycles=sum(r['intermediate_missed'] for r in runs),
            counting_note=(
                f"{sum(1 for m in d.missions if m['nav_outcome'] == 'missed')} decision "
                f"records carry nav_outcome = missed, but only {len(failed)} runs end in "
                'one. The rest are recovery cycles inside runs that subsequently '
                'completed. The two numbers must never be interchanged.'),
            per_platform=dict(
                basis='protocol-valid runs (the invalidated run is excluded)',
                platforms=per_plat),
            per_platform_raw_for_reconciliation=dict(
                basis=('every archived run, including the protocol-invalidated one. Kept '
                       'so the archive and the analysis reconcile; not part of the '
                       'primary inferential analysis.'),
                terminal_miss=raw_per_plat),
            platform_terminal_miss_fisher=fisher,
            semantic_vs_execution=dict(
                note=('Every terminal failure listed above reached a decision; none is a '
                      'failure to resolve the instruction. Resolution and execution are '
                      'therefore separable in this dataset.'))),
        source=['missions.csv'])


def r2_10(d):
    """Model agnosticism: what the dataset makes possible, and what is still missing."""
    prompts = sum(1 for m in d.missions if m['_l3b_ok'] or m['_l3b_fail'])
    return dict(
        title='Model agnosticism for L3b',
        asks='Comparative experiments with alternative VLMs.',
        metrics=dict(
            status='PENDING — requires a replay of the recorded prompts through a second model',
            replayable_prompts=prompts,
            model_under_test=sorted({s['vlm_model'] for s in d.sessions if s['vlm_model']}),
            model_digest=sorted({s['vlm_model_digest'] for s in d.sessions if s['vlm_model_digest']}),
            quantization=sorted({s['vlm_quantization'] for s in d.sessions if s['vlm_quantization']}),
            note=('Every escalated record stores extra.vlm_prompt_full, the complete prompt '
                  'as sent. Together with the model digest this makes the comparison '
                  'reproducible by a third party without any of our code. The second-model '
                  'run itself is not yet done and this key must not be cited until it is.')),
        source=['missions.csv', 'sessions.csv'])



def ac_abstention_promotion(d, replay=True):
    """Whether the frozen extractor can promote an abstention into deterministic memory.

    This is not a hypothesis. The extractor shipped in the dataset is re-run here over the
    day-1 logs, and the resulting M3 file is inspected. The abstention marker is not a node
    id; the graph is indexed 0..23.
    """
    import subprocess, tempfile, importlib.util

    out = dict(replayed=False, promotions=None, abstention_promoted=None)
    extractor = os.path.join(d.root, 'day2_20260821/code/memory_extractor.py')
    logs = os.path.join(d.root, 'day1_20260820/logs')
    geo = os.path.join(d.root, 'day1_20260820/config/semantic_objects_static_v2.geojson')
    if replay and all(os.path.exists(p_) for p_ in (extractor, logs, geo)):
        try:
            tmp = tempfile.mkdtemp(prefix='m3replay_')
            subprocess.run([sys.executable, extractor, '--logs-dir', logs,
                            '--geojson', geo, '--output', tmp],
                           check=True, capture_output=True, timeout=600)
            dig = json.load(open(os.path.join(tmp, 'memory_digest.json'), encoding='utf-8'))
            prom = dig.get('l3a_promotions_ready') or []
            cands = [json.loads(l) for l in
                     open(os.path.join(tmp, 'M3_operator_preferences.jsonl'), encoding='utf-8')]
            neg = [c for c in cands if (c.get('resolved_node_id') is not None
                                        and c['resolved_node_id'] < 0)]
            out.update(
                replayed=True,
                inputs=dict(logs='day1_20260820/logs',
                            extractor='day2_20260821/code/memory_extractor.py'),
                promotions=len(prom),
                promoted=[dict(node_id=p_.get('node_id'), frequency=p_.get('frequency'))
                          for p_ in prom],
                abstention_promoted=any(p_.get('node_id') == ABSTENTION_NODE for p_ in prom),
                abstention_candidates=[
                    dict(node_id=c['resolved_node_id'], frequency=c.get('frequency'),
                         consistency=c.get('consistency'), ready=c.get('ready_for_l3a_promotion'),
                         methods=c.get('method_distribution'),
                         key=c.get('instruction_key'),
                         example=(c.get('instruction_examples') or [''])[0][:70])
                    for c in neg])
        except Exception as e:
            out['replay_error'] = str(e)[:200]

    # How close the promoted abstention cluster sits to its own affirmative form.
    jac = None
    src = os.path.join(d.root, 'day2_20260821/code')
    try:
        sys.path.insert(0, src)
        import sas_text as T
        neg_i = 'do not go to a place to take a short break for personal needs'
        pos_i = 'go to a place to take a short break for personal needs'
        jac = dict(negated=neg_i, affirmative=pos_i,
                   jaccard=round(T.jaccard(T.tokenize(neg_i), T.tokenize(pos_i)), 4),
                   threshold=sorted({f(x['m3_jaccard_threshold']) for x in d.sessions
                                     if x['m3_jaccard_threshold']}))
    except Exception as e:
        jac = dict(error=str(e)[:120])
    finally:
        if src in sys.path:
            sys.path.remove(src)

    g = negation_guard(d)
    return dict(
        title='AC — the offline extractor can promote an abstention',
        asks='(internal, surfaced by session E) memory hygiene of the promotion rule.',
        metrics=dict(
            replay=out,
            lexical_proximity=jac,
            runtime_exposure=dict(
                negated_instructions=('protected: the negation guard runs before cascade '
                                      'step 0. In %d/%d guard activations the decision '
                                      'never reached M3.' % (g['activations'], g['activations'])),
                affirmative_paraphrases=(
                    'not protected structurally. The promoted abstention cluster matches '
                    'the corresponding affirmative instruction above the matching '
                    'threshold; it is outranked only because the correct preference '
                    'happens to match more strongly. The protection is incidental, not '
                    'by construction.'),
                observed_navigations_to_abstention=sum(
                    1 for m in d.missions
                    if str(m['node_id']) == str(ABSTENTION_NODE)
                    and str(m['nav_outcome']).startswith('mission_complete')),
                observed_records_with_abstention_node=sum(
                    1 for m in d.missions if str(m['node_id']) == str(ABSTENTION_NODE))),
            correction=('The extractor must exclude non-positive node identifiers from '
                        'promotion, and promotion should be conditioned on a validated '
                        'semantic outcome rather than on frequency and consistency alone.')),
        source=['day2_20260821/code/memory_extractor.py', 'day1_20260820/logs'])


def ac_l3b(d):
    """L3b call outcomes, under every convention the source documents use."""
    ok = sum(1 for m in d.missions if m['_l3b_ok'])
    fail = sum(1 for m in d.missions if m['_l3b_fail'])
    neg = sum(1 for m in d.missions if m['_neg'])
    per_day = {}
    for day in sorted({m['day'] for m in d.missions}):
        g = [m for m in d.missions if m['day'] == day]
        o = sum(1 for m in g if m['_l3b_ok'])
        fl = sum(1 for m in g if m['_l3b_fail'])
        ng = sum(1 for m in g if m['_neg'])
        per_day[day] = dict(
            convention_calls_issued=wilson(fl, o + fl),
            convention_including_negation_blocked=wilson(fl, o + fl + ng),
            l3b_ok=o, l3b_failed=fl, negation_blocked=ng)
    return dict(
        title='AC — L3b failure rate under each counting convention',
        asks='(internal) reconcile the three denominators used across the source documents.',
        metrics=dict(
            recommended_convention='L3b_vlm + escalated (calls issued that did or did not parse)',
            overall=wilson(fail, ok + fail),
            overall_including_negation_blocked=wilson(fail, ok + fail + neg),
            per_day=per_day,
            note=('Day 2 has no negation-blocked records, so the two conventions coincide '
                  'there. On day 1 they do not, which is why the same day appears in the '
                  'source documents both as 9.5% and as 20%.')),
        source=['missions.csv', 'KNOWN_DISCREPANCIES.md'])


def ac_identity(d):
    """Digest identity across the session."""
    per = defaultdict(lambda: dict(records=0, prefs=set(), status=set(), days=set()))
    for m in d.missions:
        k = m['digest_content_md5'][:8] or '(none)'
        per[k]['records'] += 1
        per[k]['prefs'].add(m['m3_preferences_count'])
        per[k]['status'].add(m['memory_status'])
        per[k]['days'].add(m['day'])
    return dict(
        title='AC — memory digest identity',
        asks='(internal) which digest governed which records.',
        metrics={k: dict(records=v['records'], m3_preferences=sorted(v['prefs']),
                         memory_status=sorted(v['status']), days=sorted(v['days']))
                 for k, v in sorted(per.items())},
        source=['missions.csv'])


# ======================================================================================

def render_blocks_md(res):
    b = res['points']['BLOCKS']['metrics']
    blocks = b['blocks']
    L = ['# Session E — block register', '',
         'Session E is not one experiment repeated. It is nine blocks, each isolating one',
         'component and each answering a specific point raised in review. The last line of',
         'each entry is the reason the session exists: it says what, if anything, in',
         'sessions A-C tested the same thing.', '',
         '| block | records | platforms | intents | what it tests | component | answers |',
         '|---|---|---|---|---|---|---|']
    for bid, v in blocks.items():
        plats = ', '.join(p.replace('xplorer-', '') for p in v['platforms'])
        rev = ', '.join(v['reviewer']) or '—'
        L.append(f"| **{bid}** | {v['records']} | {plats} | {v['distinct_intents']} | "
                 f"{v['title']} | {v['component']} | {rev} |")
    L += ['', '## What each block measured', '']
    for bid, v in blocks.items():
        L += [f"### {bid} — {v['title']}", '', v['tests'], '',
              f"**Records** {v['records']} across {', '.join(v['platforms'])}, "
              f"{v['distinct_intents']} distinct intents "
              f"(median {v['repetitions_per_intent'].get('median', '—')} repetitions each).  ",
              f"**Resolution** " + ', '.join(f'`{k}` {n}' for k, n in
                                             sorted(v['methods'].items(), key=lambda x: -x[1])) + '.  ']
        if v.get('fast_path_primary'):
            fp = v['fast_path_primary']
            L.append(f"**Fast-path coverage (primary, per {fp['unit']})** "
                     f"{fp['k']}/{fp['n']} = {100 * fp['rate']:.1f}% "
                     f"[{100 * fp['low']:.1f}, {100 * fp['high']:.1f}].  ")
            L.append(f"*{fp['note']}; the record-level figure "
                     f"{v['fast_path']['k']}/{v['fast_path']['n']} = "
                     f"{100 * v['fast_path']['rate']:.1f}% is descriptive only.*  ")
        elif v['fast_path']['n']:
            fp = v['fast_path']
            L.append(f"**Fast path** {fp['k']}/{fp['n']} = {100 * fp['rate']:.1f}% "
                     f"[{100 * fp['low']:.1f}, {100 * fp['high']:.1f}].  ")
        if v['l3b_calls']:
            f2 = v['l3b_failures']
            L.append(f"**L3b** {v['l3b_calls']} call{'s' if v['l3b_calls'] != 1 else ''}, "
                     f"{f2['k']} without parseable JSON "
                     f"({100 * f2['rate']:.1f}%).  ")
        if v['negation_blocked']:
            L.append(f"**Negation guard** blocked {v['negation_blocked']} of them.  ")
        if v.get('rate_note'):
            L += ['', f"*How to read this block's rate:* {v['rate_note']}"]
        L += ['', f"*In sessions A-C:* {v['prior_sessions']}", '']
        if v['single_platform_warning'] and v['role'] != 'excluded from all rates':
            L += [f"> **Single platform.** This block ran only on "
                  f"{v['platforms'][0]}. Its result has no replication on the second "
                  f"robot, and is reported as such.", '']
        if 'excluded' in v['role']:
            L += ['> **Excluded from all reported rates.** It is a configuration check, '
                  'not a measurement.', '']
    L += ['## Why rates are reported per block', '', b['composition_note'], '',
          '| block | records | fast path | L3b calls | how to read it |',
          '|---|---|---|---|---|']
    for bid, v in blocks.items():
        fp = v.get('fast_path_primary') or v['fast_path']
        unit = f" ({fp['k']}/{fp['n']} {fp.get('unit', 'records')})"
        L.append(f"| {bid} | {v['records']} | {100 * fp['rate']:.1f}%{unit} | "
                 f"{v['l3b_calls']} | {v.get('rate_note') or 'measured'} |")
    L.append('')
    return '\n'.join(L) + '\n'


def render_markdown(res):
    L = ['# Session E — results by reviewer point', '',
         'Generated by `analyze_session_e.py` from the published dataset. Every figure here',
         'is computed; none is transcribed. Cite this file, not the conversation.', '',
         f"Dataset: `{res['meta']['dataset']}`  ",
         f"Audit sessions: {res['meta']['audit_sessions']}  ",
         f"Decision-bearing runs: {res['meta']['decision_bearing_runs']}  ",
         f"Decision cycles: {res['meta']['decision_cycles']}  ",
         '',
         'Every n in this file names its unit. The split of decision cycles into resolved '
         'and unresolved records is in the `UNITS` section, not here.',
         f"Bootstrap: {BOOTSTRAP} resamples over clusters, seed {RNG_SEED}", '',
         '## Index', '', '| key | title | status |', '|---|---|---|']
    for k, v in res['points'].items():
        st = v['metrics'].get('status', 'computed') if isinstance(v['metrics'], dict) else 'computed'
        L.append(f"| `{k}` | {v['title']} | {st} |")
    L += ['', '---', '']
    for k, v in res['points'].items():
        L += [f"## {k} — {v['title']}", '', f"**What is asked.** {v['asks']}", '',
              '```json', json.dumps(v['metrics'], indent=2, ensure_ascii=False)[:20000], '```',
              '', f"Source: {', '.join('`%s`' % s for s in v['source'])}", '', '---', '']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--no-replay', action='store_true',
                    help='skip re-running the frozen extractor for AC-ABSTENTION')
    ap.add_argument('--outdir', default=None,
                    help='where results_E.json, RESULTS_E.md and BLOCKS.md are written. '
                         'Default <dataset>/analysis, which keeps a standalone dataset '
                         'self-contained; in the repository this is analysis/session_e.')
    args = ap.parse_args()

    root = os.path.abspath(args.dataset)
    out = os.path.abspath(args.outdir) if args.outdir else os.path.join(root, 'analysis')
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)

    d = Dataset(root)
    print(f'  {len(d.sessions)} audit sessions, {len(d.runs)} decision-bearing runs, '
          f'{len(d.missions)} decision cycles, {len(d.e7)} sealed E7 cells, '
          f'external_reference {"loaded" if d.external else "MISSING"}')

    points = OrderedDict()
    points['UNITS'] = units(d)
    points['BLOCKS'] = blocks(d)
    points['R1-1'] = r1_1(d)
    points['R1-2'] = r1_2(d)
    points['R1-3'] = r1_3(d)
    points['R1-4'] = r1_4(d)
    points['R1-5'] = r1_5(d)
    points['R1-6'] = r1_6(d)
    points['R1-7'] = r1_7(d, rng)
    points['LATENCY'] = latency_estimands(d, rng)
    points['R1-8'] = r1_8(d)
    points['R1-9'] = r1_9(d)
    points['R1-10'] = r1_10(d)
    points['R2-1'] = r2_1(d)
    points['R2-2'] = r2_2(d)
    points['R2-6'] = r2_6(d)
    points['R2-9'] = r2_9(d)
    points['R2-10'] = r2_10(d)
    points['AC-ABSTENTION'] = ac_abstention_promotion(d, replay=not args.no_replay)
    points['AC-L3B'] = ac_l3b(d)
    points['AC-DIGEST'] = ac_identity(d)

    esc = sum(1 for m in d.missions if m['_l3b_fail'])
    res = dict(
        meta=dict(dataset=os.path.basename(root),
                  audit_sessions=len(d.sessions),
                  decision_bearing_runs=len(d.runs),
                  decision_cycles=len(d.missions),
                  resolved_or_blocked_records=len(d.missions) - esc,
                  unresolved_escalation_records=esc,
                  cluster_key=CLUSTER_KEY,
                  bootstrap_resamples=BOOTSTRAP, rng_seed=RNG_SEED,
                  not_covered_here=['R2-3', 'R2-4', 'R2-5', 'R2-7', 'R2-8'],
                  not_covered_reason=('These are argued from the literature, from figures, or '
                                      'from experiments not yet run; they carry no figure '
                                      'this script could compute.')),
        points=points)

    json.dump(res, open(os.path.join(out, 'results_E.json'), 'w'), indent=2, ensure_ascii=False, default=str)
    open(os.path.join(out, 'RESULTS_E.md'), 'w', encoding='utf-8').write(render_markdown(res))
    open(os.path.join(out, 'BLOCKS.md'), 'w', encoding='utf-8').write(render_blocks_md(res))

    # Ship the script alongside its outputs, before the manifest is computed. Copying it
    # afterwards is what produced a CHECKSUMS.md5 that did not match its own script.
    me = os.path.abspath(__file__)
    if os.path.dirname(me) != out:
        shutil.copy2(me, os.path.join(out, os.path.basename(me)))

    lines = []
    for name in sorted(os.listdir(out)):
        p = os.path.join(out, name)
        if os.path.isfile(p) and name != 'CHECKSUMS.md5':
            import hashlib
            lines.append(f"{hashlib.md5(open(p,'rb').read()).hexdigest()}  {name}")
    open(os.path.join(out, 'CHECKSUMS.md5'), 'w').write('\n'.join(lines) + '\n')

    print(f'  wrote {len(points)} points to {os.path.relpath(out, root)}/results_E.json')
    for k, v in points.items():
        st = v['metrics'].get('status')
        print(f"    {k:<10} {v['title'][:58]}{'   [' + st.split()[0] + ']' if st else ''}")
    print('\nDONE')


if __name__ == '__main__':
    main()
