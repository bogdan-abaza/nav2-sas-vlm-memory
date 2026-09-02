# A2 — Step-0 M3 Jaccard-threshold and abstention-margin sensitivity

**Status:** FROZEN 2026-08-25  
**Freeze note:** independently validated 2026-08-25. The five machine-generated outputs regenerate byte-identically from `analyze_A2_m3_sensitivity.py` and the bundled inputs. This report is an authored document, not a script output; only this status block was changed at freeze time, the analysis text is unmodified.  
**Scope:** offline replay of the **Step-0 M3 matcher only** for frozen Session E.  
**Reviewer relevance:** R2-1; contributes to the offline closure package for R1-5 / R2-5.  
**Public-code policy:** this package is standalone and public-safe. It contains the approved `sas_text.py` utility but **does not contain or require any production SAS resolver/orchestration/memory source module**.

## 1. Question

Does the frozen Step-0 M3 behaviour reproduce from released inputs and a standalone implementation, and how sensitive is matcher acceptance to the Jaccard threshold and runner-up abstention margin?

This is a **post-hoc sensitivity analysis**, not parameter fitting. The evaluated operating point (`J = 0.75`, margin `0.10`) was frozen before Session E.

## 2. Inputs and population

The standalone replay uses the canonical Session E `missions.csv` / `sessions.csv`, exact digest states selected by each record's `digest_content_md5`, and frozen `sas_text.py` v1.2.0.

Primary selection:

- Session E raw decisions: **226**.
- E0 start-gate decisions excluded: **10**, leaving **216** primary decisions.
- E6 memory-ablation decisions with an empty M3 state: **4**, excluded from A2 because no Step-0 candidate set exists.
- **A2 evaluation population: 212 records with non-empty M3 memory.**
- Digest states: **207** records use the six-association digest `0fd61f9e...`; **5** use the one-association E4b digest `5b3f14bc...`.
- These 212 records contain **84 unique instruction strings** and **86 semantic-intent labels**; record counts are repeated observations and are not treated as independent statistical samples.
- `sas_text.detect_negation()` identifies **39/212** records; those abstain before Jaccard threshold/margin evaluation. The remaining **173** are non-negated matcher records.

For the 173 non-negated records, **168** use a digest with multiple candidate nodes and therefore have a runner-up score; **5** use the one-node E4b digest and have no runner-up. At the frozen operating point, four of those five single-node records are accepted M3 matches; hence the margin is vacuous for **4/39 observed Step-0 matches**, as anticipated in the revision matrix.

## 3. Mandatory reproduction gate

At the frozen settings `J = 0.75`, margin `0.10`:

- observed Step-0 accepts: **39**;
- standalone replay accepts: **39**;
- accept/abstain agreement: **212/212**;
- accepted-node agreement: **39/39**;
- reproduction mismatches: **0**.

The standalone analysis therefore passes the required gate **without importing the unpublished production resolver**.

An additional internal-only diagnostic cross-check against the enriched Session E export also reproduced, for all 39 observed Step-0 matches, the logged top Jaccard score, runner-up score (where present), and matched example; the 39 derived negation-gated records also coincide with the enriched `negation_detected` records. This additional check is not required to execute the public analysis.

## 4. Frozen operating point

At `J = 0.75`, margin `0.10`:

| Outcome | Records |
|---|---:|
| Step-0 M3 accepted | **39** |
| Negation-gated abstention | **39** |
| Below-threshold abstention | **134** |
| Ambiguous-margin abstention | **0** |
| No-candidate abstention | **0** |
| **Total** | **212** |

The 39 matcher accepts correspond to **5 unique instruction strings**. All 39 have a top Jaccard score of **1.0**. Of these, **35** have a runner-up candidate and **4** do not. The minimum runner-up gap among the 35 multi-candidate accepted records is **0.80**, so the frozen margin `0.10` is not active on any observed nominal acceptance.

Among the 39 accepted records, `expected_node_id` is populated for **35**; the matcher candidate agrees with that **protocol-defined expected node in 35/35**. The four E4b reuse records have no `expected_node_id` field and are excluded from that descriptive check.

## 5. Jaccard-threshold sensitivity

Margin is held at the frozen value `0.10`.

| J threshold | Accepted | New vs 0.75 | Below threshold | Margin abstentions | Expected-node disagreements among labelled accepts |
|---:|---:|---:|---:|---:|---:|
| 0.20 | 54 | +15 | 114 | 5 | 4 |
| 0.25 | 53 | +14 | 120 | 0 | 4 |
| 0.375 | 44 | +5 | 129 | 0 | 4 |
| 0.50 | 43 | +4 | 130 | 0 | 4 |
| **0.60** | **43** | **+4** | **130** | **0** | **4** |
| 0.625 | 43 | +4 | 130 | 0 | 4 |
| 0.65 | 39 | 0 | 134 | 0 | 0 |
| 0.70 | 39 | 0 | 134 | 0 | 0 |
| **0.75 frozen** | **39** | **0** | **134** | **0** | **0** |
| 0.85 | 39 | 0 | 134 | 0 | 0 |
| 1.00 | 39 | 0 | 134 | 0 | 0 |

The score distribution is strongly discrete: the 173 non-negated records have top scores ranging from 0 to 1, but the highest rejected score at the frozen operating point is **0.625**, followed by the 39 exact matches at **1.0**. Consequently, at margin 0.10 there is a stable matcher-decision plateau for **thresholds >0.625 through 1.0**.

The manuscript's former `J = 0.60` value would admit **four additional records (two unique instruction strings, each repeated twice)** at score `0.625`. They are E2 explicit-location/fire phrasings (`lab cb203 ... fire` and `lab cb204 ... fire`) whose M3 candidate is node 8. For the four records, the candidate differs from the protocol-defined `expected_node_id`.

**Important scope caveat:** these four are **matcher-level counterfactual accepts**, not demonstrated final navigation errors. The complete v4.8-review resolver has separate downstream handling, including explicit-location conflict protection, which is outside A2. Therefore A2 supports the conservatism of the higher threshold but does not estimate a full-system error rate at `J = 0.60`.

## 6. Abstention-margin sensitivity

At the frozen threshold `J = 0.75`, the matcher is unchanged over a broad margin range:

| Margin | Accepted | Ambiguous-margin abstentions |
|---:|---:|---:|
| 0.00 | 39 | 0 |
| 0.05 | 39 | 0 |
| **0.10 frozen** | **39** | **0** |
| 0.15 | 39 | 0 |
| 0.20 | 39 | 0 |
| 0.30 | 39 | 0 |
| 0.50 | 39 | 0 |
| 0.80 | 39 | 0 |
| 0.90 | 18 | 21 |

Thus Session E does **not empirically optimize or identify `0.10` as a unique margin**. At the frozen threshold, all accepted multi-candidate matches are already widely separated from their runner-up (`gap >= 0.80`). The margin should therefore be presented as a conservative ambiguity guard rather than as a parameter tuned for maximum Session E performance.

The full 2-D sensitivity grid (`J = 0.20..1.00`, margin `0.00..0.30`, increments 0.01) confirms that the margin becomes active only when the Jaccard threshold is lowered into the low-overlap region. For example, at `J = 0.20`, increasing the margin from 0 to 0.10 changes matcher accepts from 59 to 54 by abstaining on five near-tie records.

## 7. Interpretation for the revision

A2 supports four narrow claims:

1. **Reproducibility:** the released standalone implementation exactly reproduces the frozen observed Step-0 M3 accept/abstain decisions and accepted nodes at `0.75 / 0.10`.
2. **Threshold robustness:** the frozen 0.75 threshold lies inside a wide observed decision plateau; all 39 nominal matches are exact (`J=1.0`) while the nearest lower score cluster is `0.625`.
3. **Effect of the former 0.60 threshold:** lowering the threshold to 0.60 admits four additional moderate-overlap matcher candidates. This is a matcher-level sensitivity result, not a counterfactual full-resolver failure rate.
4. **Margin limitation:** the 0.10 margin is inactive at the nominal threshold on this dataset. It is a safety/ambiguity mechanism whose numerical value is **not empirically optimized by Session E**.

A2 does **not** establish semantic correctness for unlabeled records, does not replay downstream cascade steps or the full location-conflict logic, and must not be described as an independent-N=212 accuracy experiment.

## 8. Suggested manuscript-ready wording

> Offline replay of the released Session E Step-0 M3 inputs reproduced all 39 observed M3 resolutions and all 173 non-Step-0 outcomes among the 212 E0-excluded decisions with non-empty M3 state, with 39/39 accepted node IDs reproduced. With the abstention margin fixed at 0.10, the frozen Jaccard threshold of 0.75 lay within a stable decision plateau: all 39 accepted matches had Jaccard 1.0, whereas the next-highest candidate score was 0.625. Reverting to the earlier 0.60 threshold would admit four additional 0.625-overlap matcher candidates. At the frozen 0.75 threshold, the 0.10 runner-up margin did not alter any decision because all 35 accepted matches with a runner-up had score gaps of at least 0.80; the remaining four accepted matches had no runner-up. We therefore interpret the margin as a conservative ambiguity guard rather than an empirically optimized operating point.

For the Results/Discussion, retain the explicit caveat that this sensitivity replay concerns the **Step-0 matcher** and not counterfactual execution of the complete resolver.

## 9. Release recommendation

After independent validation/freeze, the public repository can include the standalone script, machine-readable results, score table, sensitivity grid, report, and the already-approved `sas_text.py` plus released Session E tabular/config inputs. No other SAS source file is required or should be released for A2.
