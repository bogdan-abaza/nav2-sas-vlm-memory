# M3 decision-boundary challenge

**Status:** sealed and run 5 October 2026 (`sealed/C5_SEAL.json`). **Reproducibility:** re-executable from this release (`python3 tools/rerun_sealed.py m3_boundary`).

## Purpose
The Session E sensitivity analysis showed consistent reuse of stored associations, but every accepted match had Jaccard similarity 1.0 and the runner-up margin was never active. This diagnostic set probes the matcher near its decision boundaries. It also adds an exact-match baseline to show what approximate matching contributes beyond replaying familiar strings.

## Set
47 items in three families: F1, 16 valid paraphrases of stored associations with graded lexical overlap; F2, 15 instructions with high lexical overlap but a different meaning; F3, 16 cases with competing destinations near the margin. F2 has 15 items because the construction rule could not fill one band; the shortfall is recorded in `sealed/C5_AMENDMENT_01_20261005.md`. F3 uses a declared synthetic index (`sealed/challenge_index_C.json`) next to the historical one.

Diagnostic set constructed with access to similarity scores; labels assigned before each candidate was scored and reviewed on sheets without scores or decisions. The set is deliberately concentrated near the boundary and is not a natural sample.

## Matchers
EXACT (exact match after the published normalisation), Jaccard 0.75 with runner-up margin 0.10 (the frozen operational setting), and Jaccard 0.60 with margin 0.10 as a historical reference column. The matcher is the published reimplementation in `analysis/session_e/A2_m3_sensitivity/`, unchanged.

## Results (`sealed/results/RESULTS_C5.md`, `per_item.csv`, `summary.csv`)
| Matcher | Correct accept | Wrong accept | Abstention where a node was expected | Correct abstention |
|---|---:|---:|---:|---:|
| EXACT | 0 | 0 | 23 | 24 |
| Jaccard 0.75 / 0.10 | 14 | 11 | 9 | 13 |
| Jaccard 0.60 / 0.10 (reference) | 18 | 15 | 4 | 10 |

By family, Jaccard 0.75/0.10 accepts 10/16 valid paraphrases (F1), wrongly accepts 9/15 high-overlap different-meaning instructions (F2), and in F3 gives 4 correct and 2 wrong acceptances with 9 correct abstentions. By construction no item is identical to a stored example after normalisation, so EXACT accepts none; this describes the baseline, not paraphrase behaviour in general. For the four items at an exact gap of 1/10, floating-point evaluation gives 0.09999999999999998 and the implemented matcher abstains on the margin; this is reported, not corrected. Two F3 items use a synthetic-index association whose destination is semantically questionable; they are flagged in `per_item.csv`.

## Files
- `sealed/`: construction rule, amendments 01–02, authoring batches, candidate log, label-review sheets, final items, synthetic index, scripts (`c5_build.py`, `c5_seal.py`, `c5_run.py`), seal and results, byte-identical to the sealed set. They keep the working labels and paths of the environment in which they were sealed.

## Verify and re-run
```bash
cd analysis/session_e/m3_boundary && sha256sum -c CHECKSUMS_SHA256.txt && cd -
python3 tools/rerun_sealed.py m3_boundary
```
The sealed `c5_run.py` checks every sealed file and its published inputs before running. The adapter supplies the directory layout it expects without modifying any sealed file. The regenerated `per_item.csv` and `summary.csv` are byte-identical to the published ones.
