# Forbidden-node guard branch test — results (data only)

Run 2026-10-05T08:26:59Z · GT_SEAL.json 9e1141726007afd069f1c80ea72eac3ba95bfba20fb1258defb12753b39a373a · GT_RESULTS.json 0e68512a96748fdb0977cf9b34f1603860d1f5e739327ffc82f2e8c0ceb8ac5f · CASES.json ef2f191e2ea27969e59f5bc32112d1314f6e9e51703bc2b75930f5e9c1064535

Deployed `VLMNavigatorNode._vlm_cycle` (vlm_navigator_node_v4_8_review.py) with the deployed `call_vlm` parser, `negation_guard.validate_vlm_against_negation` and `validate_action`; 14 distinct E2 negation instructions in their parent-record context; synthetic model replies injected at HTTP level; navigation dispatch intercepted; no robot, no model.

- Forbidden proposals rejected (clarification_requested, vlm_violated_negation), no dispatch: **27 / 27**
- Permitted-node controls passed the guard and reached dispatch: **14 / 14**
- Cases matching the branch pre-specified from the frozen code (cases/CASES.json): **139 / 139**
- Envelope used by the deployed code equals the transcribed forbidden set: **14 / 14** instructions

| Case kind | n | observed outcome (guard state) | dispatches |
|---|---|---|---|
| forbidden_proposal | 27 | clarification_requested (vlm_violated_negation) x27 | 0 |
| permitted_control | 14 | dispatched (ok) x14 | 14 |
| explicit_minus1 | 14 | clarification_requested (vlm_requested_clarification) x14 | 0 |
| missing_target | 14 | clarification_requested (vlm_no_answer) x14 | 0 |
| string_target | 14 | vlm_invalid_response (ok) x14 | 0 |
| boolean_true | 14 | dispatched (ok) x14 | 14 |
| float_of_forbidden | 14 | clarification_requested (vlm_violated_negation) x14 | 0 |
| malformed_no_json | 14 | vlm_failed (None) x14 | 0 |
| nonexistent_node | 14 | vlm_invalid_response (ok) x14 | 0 |

Observed behaviour of the deployed parser worth reporting (data, not a fix):
- `{"node_id": true}`: the deployed `call_vlm` returns the JSON value unchanged; in Python `True == 1`, so the value passes the guard (1 not forbidden) and is dispatched to node 1 (14/14).
- `{"node_id": <forbidden>.0}` (float) is blocked as a violation because `0.0 == 0` (set membership), not because of a type check.
- A reply without `node_id` is logged as `clarification_requested` with guard state `vlm_no_answer`: a parse failure recorded under the clarification outcome, distinguishable only by the guard-state subflag.
- A string id (`"5"`) passes the guard (not equal to any integer) and ends as `vlm_invalid_response` without dispatch.

Scope: these exercised code branches only; not a validation of arbitrary negation interpretation or of complete system safety.
