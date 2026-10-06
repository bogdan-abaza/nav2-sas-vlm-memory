"""Known-answer test of sc_analyze.py on synthetic records (protocol s.14 gate 3). No model, no files outside tests/.
Checks: four outcome counts; item correctness >= 2/3; clarification correct vs parser failure; same_node exclusion counted as wrong executable;
paired better/worse/tied; zero denominators -> 'not applicable'; fast-path errors; resolver 'not applicable' in C; paired timing difference and
named ratio; bootstrap keeps items whole (constant per-item difference -> degenerate interval). python3 -B sc_analysis_test.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sc_analyze as AN
res = []
def check(n, c, d=''): res.append((n, bool(c), str(d)[:200])); print('%s %s %s' % ('PASS' if c else 'FAIL', n, '' if c else d))
def rec(item, stratum, arm, base, outcome, path, ms, resolver_ms=None, sub='', node=1):
    correct = outcome == 'clarification' if stratum == 'CLARIFICATION_REQUIRED' else outcome == 'acceptable'
    return dict(item_id=item, stratum=stratum, arm=arm, seed_base=base, seed=base, outcome=outcome, outcome_sub=sub, path=path, node_id=node, correct=correct,
                decision_ns=int(ms * 1e6), resolver_ns=None if arm == 'C' else int((resolver_ms or 0.2) * 1e6), resolution_step=5 if path == 'L3a' else None)
R = []
# F1 familiar: A L3a acceptable x3 (10 ms); B VLM acceptable x2 + incorrect x1 (1000 ms); C VLM incorrect x3 (1100 ms)
for b in (1, 2, 3):
    R.append(rec('F1', 'FAMILIAR_ASSOCIATION', 'A', b, 'acceptable', 'L3a', 10))
    R.append(rec('F1', 'FAMILIAR_ASSOCIATION', 'B', b, 'acceptable' if b < 3 else 'incorrect_executable', 'L3b', 1000))
    R.append(rec('F1', 'FAMILIAR_ASSOCIATION', 'C', b, 'incorrect_executable', 'L3b', 1100))
# U1 unseen: all arms VLM, acceptable 3/3, A 2000 ms, B 2000 ms, C 2000 ms; A has an L3a WRONG on base 3 (fast-path error)
for b in (1, 2, 3):
    R.append(rec('U1', 'UNSEEN_FORMULATION', 'A', b, 'incorrect_executable' if b == 3 else 'acceptable', 'L3a' if b == 3 else 'L3b', 2000, sub='same_node_no_motion' if b == 3 else ''))
    R.append(rec('U1', 'UNSEEN_FORMULATION', 'B', b, 'acceptable', 'L3b', 2000))
    R.append(rec('U1', 'UNSEEN_FORMULATION', 'C', b, 'acceptable', 'L3b', 2000))
# K1 clarification-required: A clarification x3; B parser failure x3; C incorrect executable x3
for b in (1, 2, 3):
    R.append(rec('K1', 'CLARIFICATION_REQUIRED', 'A', b, 'clarification', 'L3b', 3000, sub='vlm_explicit_-1'))
    R.append(rec('K1', 'CLARIFICATION_REQUIRED', 'B', b, 'model_or_parser_failure', 'L3b', 3000))
    R.append(rec('K1', 'CLARIFICATION_REQUIRED', 'C', b, 'incorrect_executable', 'L3b', 3000))
T = AN.analyze('S', R)
O = {(r['scope'], r['arm']): r for r in T['outcomes']}
check('F1 A 3 acceptable', O[('FAMILIAR_ASSOCIATION', 'A')]['acceptable'] == 3)
check('F1 B item correct (2/3)', O[('FAMILIAR_ASSOCIATION', 'B')]['items_correct'] == 1)
check('F1 C item not correct', O[('FAMILIAR_ASSOCIATION', 'C')]['items_correct'] == 0)
check('U1 A item correct with 2/3 despite same_node error', O[('UNSEEN_FORMULATION', 'A')]['items_correct'] == 1 and O[('UNSEEN_FORMULATION', 'A')]['incorrect_executable'] == 1)
check('K1 A clarification counted correct', O[('CLARIFICATION_REQUIRED', 'A')]['items_correct'] == 1)
check('K1 B parser failure never correct', O[('CLARIFICATION_REQUIRED', 'B')]['items_correct'] == 0 and O[('CLARIFICATION_REQUIRED', 'B')]['model_or_parser_failure'] == 3)
check('K1 B parser-failure items = 1', O[('CLARIFICATION_REQUIRED', 'B')]['parser_failure_items'] == 1)
check('ALL A 3/3 items correct', O[('ALL', 'A')]['items_correct'] == 3)
check('four classes sum to observations', all(sum(r[k] for k in AN.CLASSES) == r['observations'] for r in T['outcomes']))
C = {(r['scope'], r['contrast']): r for r in T['contrasts']}
check('A vs B ALL: better 2 (F1, K1), worse 1 (U1), tied 0', (C[('ALL', 'A_vs_B')]['better'], C[('ALL', 'A_vs_B')]['worse'], C[('ALL', 'A_vs_B')]['tied']) == (2, 1, 0), C[('ALL', 'A_vs_B')])
check('B vs C F1: better 1', C[('FAMILIAR_ASSOCIATION', 'B_vs_C')]['better'] == 1)
check('B vs C K1: tied (both 0 correct seeds)', C[('CLARIFICATION_REQUIRED', 'B_vs_C')]['tied'] == 1)
check('single-item stratum bootstrap degenerate', C[('FAMILIAR_ASSOCIATION', 'A_vs_B')]['diff_item_correctness_boot95'] == (0.0, 0.0), C[('FAMILIAR_ASSOCIATION', 'A_vs_B')]['diff_item_correctness_boot95'])
G = {(r['scope'], r['arm']): r for r in T['routing']}
check('A fast-path conditional error = 1/4 on ALL', G[('ALL', 'A')]['fast_path_counts'] == '1/4/9' and abs(G[('ALL', 'A')]['fast_path_conditional_error'] - 0.25) < 1e-9, G[('ALL', 'A')])
check('C fast-path conditional error not applicable', G[('ALL', 'C')]['fast_path_conditional_error'] == 'not applicable')
check('CLARIFICATION scope: L3a coverage 0 -> conditional n/a', G[('CLARIFICATION_REQUIRED', 'A')]['fast_path_conditional_error'] == 'not applicable')
TM = [r for r in T['timing'] if r['arm'] == 'C' and r['measure'] == 'resolver_ms']
check('resolver not applicable in C', TM and all(r['median'] == 'not applicable' for r in TM))
TC = {(r['scope'], r['contrast']): r for r in T['timing_contrasts']}
f = TC[('FAMILIAR_ASSOCIATION', 'A_vs_B')]
check('F1 paired diff A-B = -990 ms', abs(f['value_diff'] + 990) < 1e-6, f)
check('F1 ratio B/A = 100 named A faster', abs(f['median_paired_ratio'] - 100) < 1e-6 and 'A faster' in f['ratio_name'], f)
u = TC[('UNSEEN_FORMULATION', 'B_vs_C')]
check('U1 equal times -> diff 0, ratio 1', u['value_diff'] == 0 and u['median_paired_ratio'] == 1.0, u)
n_fail = sum(1 for _, ok, _ in res if not ok)
d = os.path.join(AN.ROOT, 'tests'); os.makedirs(d, exist_ok=True)
json.dump(dict(n=len(res), n_pass=len(res) - n_fail, analyze_sha256=AN.sha(os.path.join(HERE, 'sc_analyze.py')), results=res), open(os.path.join(d, 'ANALYSIS_TESTS.json'), 'w'), indent=1)
print('ANALYSIS TESTS %d/%d' % (len(res) - n_fail, len(res))); sys.exit(1 if n_fail else 0)
