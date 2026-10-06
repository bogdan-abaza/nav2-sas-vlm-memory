# Session E: RC1.2 reanalysis layer

This directory adds corrected descriptive figures derived from the RC1.1 Session E records.
It changes nothing in RC1.1: the dataset (`data/session_e/`), the core analyzer and its
published output (`analysis/session_e/core/`) are read only. The script checks their hashes
before computing anything, verifies every dataset file it reads against
`data/session_e/CHECKSUMS_PUBLIC.md5`, and stops if the published figures that remain valid
do not reconcile.

| Output | Content |
|---|---|
| `RC1_2_REANALYSIS.md` | human-readable summary of all sections |
| `rc1_2_reanalysis_results.json` | full results, with definitions, denominators and Wilson 95% intervals |
| `e7_taxonomy_per_cell.csv` | the 28 sealed E7 cells: scored record, decision class, correctness |
| `e7_g3_prompt_timeline.csv` | L3b decision prompts of the G-3 platform on day 2, with the `stop sign_8` context line |
| `navigation_non_arrival_runs.csv` | protocol-valid runs with a dispatched navigation goal that did not end in arrival |

## What is corrected

- **E7 decision classes.** In RC1.1 a cell without a node was recorded as `abstained`. The
  three such cells are model-response parse failures, not abstentions; no E7 record is a
  clarification request. The layer classifies each cell into one of five mutually exclusive
  classes and scores a clarification-required cell as correct only on an explicit clarification
  request. The frozen class name `executable_where_abstention_expected` is retained in the outputs. The correct count (17/28) is unchanged.
- **Fast path.** False-fast-resolution incidence over the 28 cells and the error rate among
  fast-path decisions are reported separately.
- **G-3.** The documentary evidence on the context available to this deterministic decision
  is collected; it supports a reconstruction, not direct per-cycle provenance.
- **Navigation denominators.** Three measures, each with its own denominator: terminal miss
  over all protocol-valid runs, terminal miss over runs with a dispatched navigation goal, and
  non-arrival over runs with a dispatched navigation goal.

## Reproduce

From the repository root:

```bash
PYTHONPATH=data/session_e/public_code \
python3 analysis/session_e/rc1_2_reanalysis/reanalyze_session_e.py \
    --dataset data/session_e --core analysis/session_e/core --outdir <your-outdir>
```

The outputs are deterministic and byte-identical to the files in this directory
(`CHECKSUMS_SHA256.txt`). Requires numpy and scipy, as the core analyzer. Status: publicly
reproducible from this release.
