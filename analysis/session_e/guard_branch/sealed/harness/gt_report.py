"""Post-run formatter for the guard branch test. Reads only results/GT_RESULTS.json and cases/CASES.json (both hashed); runs no case.
Written after the sealed gt.py crashed in its summary step (KeyError 'item_id': result records carry case_id, not item_id) AFTER the
complete raw results had been written. python3 -B gt_report.py"""
import os, json, hashlib
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
R = json.load(open(os.path.join(ROOT, 'results', 'GT_RESULTS.json'))); C = json.load(open(os.path.join(ROOT, 'cases', 'CASES.json')))
item = {c['case_id']: c['item_id'] for c in C['cases']}; res = R['results']
F = [x for x in res if x['kind'] == 'forbidden_proposal']; P = [x for x in res if x['kind'] == 'permitted_control']
kinds = ['forbidden_proposal', 'permitted_control', 'explicit_minus1', 'missing_target', 'string_target', 'boolean_true', 'float_of_forbidden', 'malformed_no_json', 'nonexistent_node']
L = ['# Forbidden-node guard branch test — results (data only)', '',
     'Run %s · GT_SEAL.json %s · GT_RESULTS.json %s · CASES.json %s' % (R['run_utc'], R['seal_sha256'], sha(os.path.join(ROOT, 'results', 'GT_RESULTS.json')), sha(os.path.join(ROOT, 'cases', 'CASES.json'))), '',
     'Deployed `VLMNavigatorNode._vlm_cycle` (vlm_navigator_node_v4_8_review.py) with the deployed `call_vlm` parser, `negation_guard.validate_vlm_against_negation` and `validate_action`; 14 distinct E2 negation instructions in their parent-record context; synthetic model replies injected at HTTP level; navigation dispatch intercepted; no robot, no model.', '',
     '- Forbidden proposals rejected (clarification_requested, vlm_violated_negation), no dispatch: **%d / %d**' % (sum(1 for x in F if x['outcome'] == 'clarification_requested' and x['guard_state'] == 'vlm_violated_negation' and not x['dispatch']), len(F)),
     '- Permitted-node controls passed the guard and reached dispatch: **%d / %d**' % (sum(1 for x in P if x['outcome'] == 'dispatched' and x['guard_state'] == 'ok'), len(P)),
     '- Cases matching the branch pre-specified from the frozen code (cases/CASES.json): **%d / %d**' % (sum(x['match'] for x in res), len(res)),
     '- Envelope used by the deployed code equals the transcribed forbidden set: **%d / %d** instructions' % (
         sum(1 for m in C['instructions'] if all(x['forbidden_used'] == m['forbidden_transcribed'] for x in res if item[x['case_id']] == m['item_id'] and x['forbidden_used'] is not None)), len(C['instructions'])), '',
     '| Case kind | n | observed outcome (guard state) | dispatches |', '|---|---|---|---|']
for k in kinds:
    xs = [x for x in res if x['kind'] == k]; c = Counter('%s (%s)' % (x['outcome'], x['guard_state']) for x in xs)
    L.append('| %s | %d | %s | %d |' % (k, len(xs), '; '.join('%s x%d' % kv for kv in c.items()), sum(1 for x in xs if x['dispatch'])))
L += ['', 'Observed behaviour of the deployed parser worth reporting (data, not a fix):',
      '- `{"node_id": true}`: the deployed `call_vlm` returns the JSON value unchanged; in Python `True == 1`, so the value passes the guard (1 not forbidden) and is dispatched to node 1 (%d/%d).' % (sum(1 for x in res if x['kind'] == 'boolean_true' and x['dispatch'] == [1]), sum(1 for x in res if x['kind'] == 'boolean_true')),
      '- `{"node_id": <forbidden>.0}` (float) is blocked as a violation because `0.0 == 0` (set membership), not because of a type check.',
      '- A reply without `node_id` is logged as `clarification_requested` with guard state `vlm_no_answer`: a parse failure recorded under the clarification outcome, distinguishable only by the guard-state subflag.',
      '- A string id (`"5"`) passes the guard (not equal to any integer) and ends as `vlm_invalid_response` without dispatch.',
      '', 'Scope: these exercised code branches only; not a validation of arbitrary negation interpretation or of complete system safety.']
open(os.path.join(ROOT, 'results', 'GT_RESULTS.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
