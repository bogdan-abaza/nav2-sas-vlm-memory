# Controlled semantic comparison: M3 ablation and offline decision latency

**Status:** input seal `sealed/seal/SEAL.json` (sha256 `3771cb1660c328a42301d67a03449f58245db60c92a7d3dee43748f2fafc70e0`); executed 5 October 2026; results frozen (`results/RESULT_FREEZE.json`). **Reproducibility:** the post-run analysis can be re-executed from this release (`python3 tools/rerun_sealed.py semantic_comparison`). The execution itself can be verified but not re-executed from this release: it requires the protected target-resolution modules, the `qwen3.5:4b` model on Ollama 0.30.2 and a GPU.

The protocol is `PROTOCOL.md`, a release copy of the sealed protocol `sealed/protocol/A4_SEMANTIC_COMPARISON_PROTOCOL_20261005.md` with editorial changes only.

## Design
Three target-resolution configurations were run on the same instruction-context items:
- **A, complete:** M3 Step 0, deterministic Steps 1–6, and the VLM on escalation;
- **B:** Step 0 disabled, with Steps 1–6 and the M1/M2 context retained;
- **C:** direct VLM target resolution.

All arms share the item context, the M1/M2 prefix, a fixed forbidden-node envelope, the VLM prompt, the response contract, the post-response guard and structural validation.

Two conditions were run:
- **Standardized context** (primary), 38 items: 5 familiar associations, 27 unseen formulations and 6 clarification-required cases. The dynamic-object store is empty; the image, pose, static objects, graph, memory and safety envelope of each item are retained. Nine otherwise eligible items without an archived start image were excluded before execution, and no images were substituted.
- **Historical context**, 28 items: replays the same-cycle archived dynamic prompt context.

Each item has three paired seeds and a balanced arm order. This fixed archive-derived workload is distinct from the physical campaign. The primary unit is the item; an item is correct if at least two of its three observations are correct. Every decision is classified as an acceptable selection, an incorrect executable decision, a clarification, or a model/parser failure.

Before every observation, a dedicated server and a fresh runner were started and the model preloaded with an empty request. A twelve-call technical qualification preceded each condition and is excluded from all results.

The decision timer runs from raw instruction processing to the final semantic decision. It covers the executed resolver steps, archived-image preparation on the VLM path, prompt construction, local API inference, decoding, parsing and guard/validation. Resolver computation is timed separately for A and B. Live camera acquisition, robot communication and physical navigation are outside this offline measurement.

## Main results (`results/S`, `results/H`, `results/S_vs_H`)
| Condition and stratum | Arm | Items | Correct items | Acceptable | Incorrect executable | Clarification | Model/parser failure |
|---|---|---:|---:|---:|---:|---:|---:|
| Standardized: familiar | A | 5 | 5 | 15 | 0 | 0 | 0 |
| Standardized: familiar | B / C | 5 | 4 | 11 | 4 | 0 | 0 |
| Standardized: unseen | A/B/C, each | 27 | 17 | 47 | 22 | 7 | 5 |
| Standardized: clarification required | A/B/C, each | 6 | 3 | 0 | 7 | 8 | 3 |
| Historical: all | A/B/C, each | 28 | 16 | 44 | 23 | 11 | 6 |

- **Familiar associations.** A made no VLM call, compared with 12/15 for B and 15/15 for C. A had a higher correct-seed count than B and C on 2 items, a lower count on none and the same count on 3. This is limited descriptive evidence of M3 reuse for the five tested associations.
- **Unseen and clarification-required items.** No incremental benefit from M3 was observed.
- **Routing.** In the standardized condition, B and C made identical decisions in all 114 paired observations, while B used 99 VLM calls instead of 114.
- **Decision latency.**
  - Familiar items: the median paired A−B difference was −6948.323 ms.
  - All standardized items: the A−B interval included zero; the median paired A−C difference was −29.149 ms (95% interval −65.059 to −12.618 ms).
  - Historical condition: B was faster than A by a median paired 36.904 ms (6.924 to 71.570 ms).
- **Runtime state.** Conditions ran in fixed order. No thermal slowdown was recorded; the GPU power-cap flag was active in 172/925 and 155/733 thermal samples.
- **Independent reference** (`results_reference_sensitivity/`). Rescoring the E7 items with the independent evaluator's judgments (`analysis/session_e/e7_adjudication/`) changed absolute correctness: 14/25 instead of 15/25 in the standardized condition, and 10/20 instead of 12/20 in the historical condition. The change was identical in every arm, so all paired comparisons within the E7 subset remained tied.
- **Parser compatibility:** see `PARSER_AUDIT.md`.

## Files
- `PROTOCOL.md`: protocol, release copy.
- `sealed/`: the sealed input set, byte-identical. It contains the protocol, harness and analysis scripts, context bundles, schedule, gates, tests, the comparison manifest and keys, `seal/SEAL.json` and the dependency manifest. These files keep the working labels and paths of the environment in which they were sealed. One sealed file is not published, `manifest_candidate/README.md`, because it describes the internal working tree and is not an execution input.
- `PUBLIC_DEPENDENCY_MAP.csv`: maps each of the 267 external dependencies in the input seal to its path in this release (262 public files) or marks it as a protected module (5, identified by hash only).
- `runs/S/run_primary/`, `runs/H/run_primary/`: per-observation records with complete API envelopes, qualification reports, thermal logs and server logs. The run header is published as `RUN_HEADER.redacted.json`: the launch environment is reduced to the runtime variables and the host name is withheld. The SHA-256 of the original header is recorded inside it.
- `results/`: frozen analysis outputs, including the result freeze inventory and the parser-audit tables.
- `results_reference_sensitivity/`: the independent-reference rescoring. Its frozen script is `sealed/post_run/sc_reference_sensitivity.py`, published unchanged because its SHA-256 is recorded in the output.

## Verify and re-run
```bash
cd analysis/session_e/semantic_comparison && sha256sum -c CHECKSUMS_SHA256.txt && cd -
python3 tools/rerun_sealed.py semantic_comparison
python3 tools/rerun_sealed.py reference_sensitivity
```
The sealed analyzer checks the run headers against the input seal, the schedule, the bundles and its own harness before computing. All 25 regenerated output files, and both reference-sensitivity outputs, are byte-identical to the published results.
