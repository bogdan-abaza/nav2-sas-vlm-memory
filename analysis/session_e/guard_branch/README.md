# Forbidden-node guard: offline branch test

**Status:** sealed 5 October 2026; results frozen (`sealed/GT_RESULT_FREEZE.json`). **Reproducibility:** verifiable, not re-executable from this release (it runs the protected navigator module).

## Purpose
No forbidden-node proposal reached the post-response guard in the Session E trials. This test supplies such proposals deliberately and checks the implemented code branch offline. It does not establish a broader safety guarantee.

## Method
The deployed method `VLMNavigatorNode._vlm_cycle` of the frozen navigator runs with its response parser, the negation guard and action validation, on the 14 distinct E2 negation instructions in the context of their parent records. Synthetic model replies are injected at the HTTP level and navigation dispatch is intercepted. No model and no robot are involved. Every case has an expected branch specified from the frozen code before the run.

## Results (`sealed/results/GT_RESULTS.md`)
| Case kind | Result |
|---|---|
| Forbidden-node proposals | 27/27 rejected (clarification requested), no dispatch |
| Permitted-node controls | 14/14 reached dispatch |
| All cases on the pre-specified branch | 139/139 |
| Forbidden set used by the deployed code equals the transcribed set | 14/14 instructions |

139/139 means agreement with the anticipated branches, including the deficient one described below. It is not a count of correct or safe outcomes. The 27 forbidden proposals cover 14 instructions, not 27 independent linguistic scenarios. Intercepted dispatch shows the navigation-command path, not physical motion.

The test also exposed missing type validation in the deployed parser: a synthetic `{"node_id": true}` response reached intercepted navigation dispatch for node 1 in all 14 tested contexts. No boolean proposal was observed in Session E; all 91 recorded VLM node proposals were integers. This finding limits claims about response-contract enforcement and does not alter the frozen Session E results.

## Files
- `sealed/`: cases, harness (`gt.py`, `gt_report.py`, `a4_bundle.py`), seal, results and result freeze, byte-identical to the sealed set. These files keep the working labels and paths of the environment in which they were sealed.
- `GT_NOTE.md`: run note (a debug run before sealing; the summary produced by a separate formatter).

## Verify
```bash
cd analysis/session_e/guard_branch && sha256sum -c CHECKSUMS_SHA256.txt
```
The cases, synthetic replies, expected and observed branches are published. Re-execution requires the protected navigator module, which is available to the editor and reviewers in confidence through the journal.
