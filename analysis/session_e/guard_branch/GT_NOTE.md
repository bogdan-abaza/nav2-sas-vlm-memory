# Guard branch test: run note

- The 139 cases were built (`sealed/cases/CASES.json`) and sealed (`sealed/seal/GT_SEAL.json`, 5 October 2026, 08:26:10Z) before the recorded run. The expected branch of every case was specified from the frozen code before that run.
- Before sealing, the harness was exercised on an unsealed copy of the same deterministic cases for debugging. The outcomes were therefore known before sealing. The test has no sampling. It checks whether the implemented branches behave as specified; it is not a blind evaluation.
- The recorded run executed all 139 cases and wrote `sealed/results/GT_RESULTS.json` completely. It then stopped in its summary step because of a key error in the summary code. No case was re-run and the results file was not overwritten. The summary `sealed/results/GT_RESULTS.md` was produced by the separate formatter `sealed/harness/gt_report.py`, which only reads the hashed results and cases.
