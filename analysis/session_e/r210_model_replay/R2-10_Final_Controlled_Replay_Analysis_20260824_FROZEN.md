# R2-10 — Final controlled replay analysis (24 August 2026), rev. 3

**Manuscript:** ROBOT-D-26-01090
**Status:** **R210-AN-02 — FROZEN**; based on the final v3 acquisition; supersedes the exploratory 23 August replay analysis and all prior R2-10 analysis drafts.
**Acquisition SHA-256:** `f59063c0e55fbc9a021c80c97c2e0897f161f620ebb374a887ba0ee4ed54ad04`
**Executed runner SHA-256:** `58cafa07d7dca62ea249218bb317590fe9d8874c0456f804a12bc9137a4e4c7e`

> **Changes in rev. 3.** Every figure has now been independently recomputed twice from the frozen acquisition and reproduced exactly; no arithmetic has changed since rev. 1. Rev. 2 introduced one factual error of its own — it claimed the original model's reply on the 22 guard-handled negation activations was unrecoverable. It is not: `extra.vlm_proposed_node` preserves it, and it is `-1` in all 22. Rev. 3 restores the original accounting, and adds what verifying it revealed: across all 35 negation activations that reached the guard, the original model never once proposed a forbidden node. §7 is rewritten around the full population rather than the replayable subset alone. Two terminology corrections complete the revision (§15).
> **Freeze note (R210-AN-02).** Numerical results are unchanged from rev. 3. The final freeze separates the full-population original-model negation rate from the outcome-conditioned replay rates, and describes the post-VLM negation guard as a defense-in-depth mechanism rather than claiming an empirically observed blocked forbidden-node proposal.


## 1. Executive conclusion

The final replay supports **L3b interface-level model portability, not semantic model invariance**. Both alternative VLMs operated through the frozen prompt/parser interface without model-specific prompt changes, but exact destination selection and abstention style remained model dependent. The M3 promotion replay likewise shows one robust association and one low-sample gate whose historical decision is not stable under rerunning — including under rerunning of the original model.

## 2. Integrity, provenance, and population

- Final main acquisition: **69 records × 3 models × 3 seed bases = 621 replay outcomes**.
- Primary analysis excludes E0: **68 records × 3 models × 3 seed bases = 612 replay outcomes**. The 68 records, not the 612 outputs, are the clustering unit.
- Supplementary text-only diagnostic: **14 × 3 × 3 = 126 outcomes**; these are not multimodal counterfactuals.
- Environment invariant across all six run environments: `fiir-eq2-Yoga-Pro-9-16IAH10`, Ollama 0.30.2, NVIDIA GeForce RTX 5050 Laptop GPU, driver 580.173.02, 8151 MiB, compute capability 12.0.
- Controlled sampler hash identical in every arm and every pass: `17d8f94f0f63578f4116e53d39219fff`. The Qwen control digest matched the digest recorded contemporaneously in the Session E `navigator_startup` records.
- Transport failures: **0**; calls requiring retry: **0**.

### 2.1 Session E VLM call-path population

| Class | n | What it means |
|---|---:|---|
| `L3b_vlm` | 69 | model produced an accepted node; `image_start` persisted → **the replay cohort** |
| `L3b_vlm_negation_blocked` | 22 | the VLM returned `node_id = -1`; the post-VLM negation guard converted this clarification request into a no-navigation `clarification_requested` outcome; no `image_start` was persisted |
| `escalated` | 14 | no accepted L3b result; no `image_start` persisted → the supplementary text-only set |
| **total VLM call-path attempts** | **105** | of which 91 carry a `vlm_ms` timing |

**What is and is not recoverable on the 22.** All 22 preserve the parsed VLM proposal as `extra.vlm_proposed_node = -1` and the post-response state as `extra.vlm_negation_check = "vlm_requested_clarification"`. The frozen navigator writes `det_extra['vlm_proposed_node'] = node_id` immediately after the VLM call, before the guard runs; `validate_vlm_against_negation` then returns `vlm_requested_clarification` for any `node_id == -1`. The original model's clarification decision is therefore **known**. What was not persisted is the raw reply text and reason — the execution path terminates at the guard before the richer response structure is built — and, critically, the `image_start` frame. These records can therefore be characterized, but they cannot enter a multimodal model-substitution replay, because the original image no longer exists.

The 69-case cohort is therefore **outcome-conditioned** on the original system reaching an accepted navigational L3b result *and* persisting `image_start`. It is not an unconditional sample of the 105 VLM-path attempts, and every agreement figure below inherits that conditioning.

## 3. Primary model comparison

| Model | Parser-contract compliance\*\* | Accepted navigational node | Abstention (`-1`) on negation prompts | Abstention (`-1`) elsewhere | No parseable contract | Agreement with archived node\* | Median wall latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:4b (control) | 181/204 = 88.7% | 160/204 = 78.4% | 21/204 = 10.3% | 0/204 = 0.0% | 23/204 = 11.3% | 137/204 = 67.2% | 7.20 s |
| gemma4:e2b | 204/204 = 100.0% | 194/204 = 95.1% | 10/204 = 4.9% | 0/204 = 0.0% | 0/204 = 0.0% | 131/204 = 64.2% | 6.77 s |
| qwen3.5:9b | 199/204 = 97.5% | 165/204 = 80.9% | 33/204 = 16.2% | 1/204 = 0.5% | 5/204 = 2.5% | 120/204 = 58.8% | 14.63 s |

\*Archived-node agreement is a **reference-agreement metric, not accuracy**: the archived Qwen output is one stochastic realization, and the replay cohort was selected from accepted archived outcomes.

\*\*Compliance is judged by the frozen production parser, which accepts a bare JSON object *or* the first JSON object extracted from surrounding prose, and requires `node_id` to be a JSON integer rather than a string. It is not stricter than the contract the navigator itself enforced. "Strict JSON" would overstate it.

Rev. 1 folded the last two columns into a single "no accepted outcome". They are separated here because they are different events. A `-1` on a negation prompt is a defensible refusal; a `-1` on an ordinary navigation request is a failure to answer; an unparseable reply is a contract breach. The single non-negation abstention is **qwen3.5:9b, seed 1, record `49_20260821_144722_s001`** (`take me to the place where deliveries arrive`, `escalation_reason = no_deterministic_match`).

Per-seed parser-contract compliance:

- **qwen3.5:4b:** seed 1 59/68 = 86.8%, seed 2 63/68 = 92.6%, seed 3 59/68 = 86.8%.
- **gemma4:e2b:** seed 1 68/68 = 100.0%, seed 2 68/68 = 100.0%, seed 3 68/68 = 100.0%.
- **qwen3.5:9b:** seed 1 66/68 = 97.1%, seed 2 65/68 = 95.6%, seed 3 68/68 = 100.0%.

Output-format portability is strong for both alternative models: Gemma produced a valid integer contract in all 204 primary replay outcomes, Qwen9 in 199/204. The original Qwen4 control is materially more format-sensitive under the same controlled replay conditions. This does not imply that Gemma or Qwen9 is semantically more correct.

## 4. Reasoning consistency across seed replicates

| Model | All 3 seeds contract-valid | Same exact node in all 3 seeds | Conditional unanimity among all-valid records | Pairwise conditional agreement range |
|---|---:|---:|---:|---:|
| qwen3.5:4b | 48/68 = 70.6% | 40/68 = 58.8% | 40/48 = 83.3% | 81.8–89.1% |
| gemma4:e2b | 68/68 = 100.0% | 66/68 = 97.1% | 66/68 = 97.1% | 97.1–98.5% |
| qwen3.5:9b | 63/68 = 92.6% | 50/68 = 73.5% | 50/63 = 79.4% | 83.1–86.4% |

Gemma is highly stable under the controlled sampler: 66 of 68 records yield the same node under all three seed bases. Both Qwen models show appreciably larger stochastic target variation. "Reasoning consistency" is therefore itself model dependent, and any single-run comparison between models would be measuring this variation rather than the models.

## 5. Cross-model semantic agreement

- **qwen3.5:4b vs gemma4:e2b:** 115/204 = 56.4% strict agreement when failures count as disagreement; 115/181 = 63.5% conditional on both outputs being contract-valid.
- **qwen3.5:4b vs qwen3.5:9b:** 133/204 = 65.2% strict; 133/177 = 75.1% conditional.
- **gemma4:e2b vs qwen3.5:9b:** 117/204 = 57.4% strict; 117/199 = 58.8% conditional.
- All three models selected exactly the same node in **97/204 = 47.5%** record×seed cells, or **97/177 = 54.8%** conditional on all three returning a contract-valid node.

The two Qwen variants agree more often with each other than either agrees with Gemma. This is descriptive evidence of family-specific target priors, not an accuracy ranking.

## 6. Agreement with the archived Session E decision

- **qwen3.5:4b:** seed 1 46/68 = 67.6%, seed 2 49/68 = 72.1%, seed 3 42/68 = 61.8%; aggregate 137/204 = 67.2%.
- **gemma4:e2b:** seed 1 44/68 = 64.7%, seed 2 44/68 = 64.7%, seed 3 43/68 = 63.2%; aggregate 131/204 = 64.2%.
- **qwen3.5:9b:** seed 1 40/68 = 58.8%, seed 2 40/68 = 58.8%, seed 3 40/68 = 58.8%; aggregate 120/204 = 58.8%.

The same-model Qwen4 control reproduces only **61.8–72.1%** of archived nodes across three controlled seed passes. The archived answer therefore cannot be treated as semantic ground truth: the model that produced it does not reproduce it. Gemma lies inside that same-model range (63.2–64.7%); Qwen9 is below it at 58.8% in all three passes. Both remain reference-agreement results, not correctness results.

## 7. Negation behaviour

### 7.1 What the original Session E system did — full population

Of 39 negation activations, 35 reached the post-VLM guard. The guard records its verdict in `extra.vlm_negation_check`, and across the whole session it took only two values:

| Guard state | n | VLM-proposed node |
|---|---:|---|
| `vlm_requested_clarification` | 22 | `-1` in all 22 |
| `ok` (non-forbidden actionable node) | 13 | `{9: 10, 5: 1, 1: 1, 15: 1}` |
| — did not reach the guard (error/parse) | 4 | — |

**`vlm_violated_negation` never occurred.** In the entire session the original model never proposed a forbidden node on a negation activation, and no forbidden destination was ever executed. The guard handled clarification requests; it never had to block a violation.

The original model therefore requested clarification on **22 of the 35** negation activations that reached the guard — **63%** — and proposed an actionable non-forbidden destination on the remaining 13.

### 7.2 What the replay can and cannot see

The R2-10 multimodal cohort contains only the **13** activations where the original proposed an actionable node, because only those persisted an `image_start`. The 22 clarification cases and the 4 error/parse cases have no image and cannot be replayed.

This selection has a consequence that must be stated plainly: **within the cohort the archive never abstains, but that is an artifact of how the cohort was built, not a property of the original model.** The original model's full-population clarification rate (22/35 = 62.9%) is therefore reported descriptively, but it is **not directly comparable** with replay abstention rates, because the replay cohort contains only the 13 original actionable, image-complete cases.

### 7.3 Replay behaviour on the 13 replayable activations

Across 3 models × 3 seed bases × 13 records = **117 replay outcomes, zero forbidden-node selections were observed.**

| Model | Overall `-1` | Prohibitions: `-1` | Exclusion requests: `-1` | Exclusion requests: actionable node | Forbidden selections |
|---|---:|---:|---:|---:|---:|
| qwen3.5:4b | 21/39 = 53.8% | 8/18 = 44.4% | 13/21 = 61.9% | 7/21 = 33.3% | 0/117 |
| gemma4:e2b | 10/39 = 25.6% | 10/18 = 55.6% | 0/21 = 0.0% | 21/21 = 100.0% | 0/117 |
| qwen3.5:9b | 33/39 = 84.6% | 18/18 = 100.0% | 15/21 = 71.4% | 5/21 = 23.8% | 0/117 |

Across the **full original Session E negation population that reached the guard**, Qwen4 returned clarification in 22/35 cases (62.9%) and a non-forbidden actionable node in 13/35. This full-population result is descriptive context only and is **not used as a denominator-matched reference** for the replay table above.

Within the **13 outcome-conditioned replayable cases**, the two directions of divergence are opposite and are invisible in an aggregate rate. On a pure prohibition — *"never go to a place to take a short break for personal needs"* — no destination is requested, and `-1` is defensible; Qwen9 takes that reading in 18/18. On an exclusion request — *"take me anywhere except the restroom"* — a destination *is* requested, and only Gemma supplies one every time (21/21), while Qwen9 refuses in 15 of 21.

Neither behaviour is a safety failure: no model, and not the original, ever selected a forbidden node. These results support retaining the deterministic post-VLM guard as a **defense-in-depth mechanism**: it safely routes clarification outputs and continues to enforce the forbidden-node constraint, although no forbidden-node proposal was observed in either Session E or the replayable subset.

## 8. Failure morphology

Rev. 1 computed this and did not report it. It is the most concrete evidence available about *how* the contract fails, and it connects the replay directly to the `vlm_error` records observed in August.

| Arm | Contract failures | Distinct records affected | Modes |
|---|---:|---:|---|
| qwen3.5:4b | 23/204 | 20 | backslash escaping 13, truncation 9, other 1 |
| gemma4:e2b | 0/204 | 0 | — |
| qwen3.5:9b | 5/204 | 5 | truncation 4, Python-literal quoting 1 |
| qwen3.5:4b (text-only) | 39/42 | 14 | **backslash escaping 39/39** |

Definitions: *truncation* = `done_reason = length` at `eval_count = 500`; *backslash escaping* = the reply contains `\"` inside what should be a plain JSON string, e.g. `{"node_id": 9, "reason": \"…\"}`, which is not valid JSON; *Python-literal quoting* = single quotes around keys or values, e.g. `{'node_id': -1}`.

Two points follow. First, the dominant failure mode of the **original** model is a serialization defect, not an inability to decide: in every one of the 39 text-only failures, and in 13 of 23 multimodal failures, a well-formed integer `node_id` is present in the raw text and recoverable — the decision was made and then mis-serialized. Second, the modes are model specific: Gemma never produced one, and Qwen9's failures are overwhelmingly truncation rather than escaping.

Recovery counts are diagnostic only. Contract compliance in §3 is decided by the runner's parser, which mirrors the production navigator, and is never relaxed by recoverability.

## 9. Latency

- **qwen3.5:4b:** median 7.20 s, mean 7.72 s, p95 11.88 s, max 15.01 s over 204 primary calls.
- **gemma4:e2b:** median 6.77 s, mean 6.70 s, p95 7.07 s, max 7.17 s.
- **qwen3.5:9b:** median 14.63 s, mean 15.61 s, p95 18.97 s, max 44.00 s.
- Paired record×seed median ratio Gemma/Qwen4 = **0.936×** (IQR 0.892–0.971); Qwen9/Qwen4 = **2.008×** (IQR 1.868–2.182).

Gemma is also the tightest distribution — its p95 sits 0.30 s above its median, against 4.68 s for Qwen4 and 4.34 s for Qwen9 — which matters more than the median for a robot with a control-loop deadline.

Latency is same-machine descriptive evidence, not a hardware-independent benchmark. Archived Session E timings must not be pooled with controlled replay timings: they were acquired in a different run context, and the replay uses an explicit warm-up call whose load cost is excluded.

## 10. M3 promotion stability under the production rule

Rule: `frequency ≥ 3 ∧ round(dominant/frequency, 2) ≥ 0.80 ∧ L3b count ≥ 1`. The population is one induction phase, and records that produced no node **remain in the denominator** — both read off the Session E digests, which this replay reproduces exactly.

Archived: E4.1 quiet-corner `[9, 15, 9, 9]` → 0.75 → **reject**; E4.1 delivery `[10, 10, 5, None]` → 0.50 → **reject**; E4b.1 gloves `[9, 9, 9, 9]` → 1.00 → **promote**.

### 10.1 Quiet-corner candidate — fully replayable

| Model | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| qwen3.5:4b | `[9,9,9,9]` 1.00 promote | `[9,9,9,9]` 1.00 promote | `[9,9,9,9]` 1.00 promote |
| gemma4:e2b | `[9,9,9,9]` 1.00 promote | `[9,9,9,9]` 1.00 promote | `[9,9,9,9]` 1.00 promote |
| qwen3.5:9b | `[9,9,9,9]` 1.00 promote | `[9,9,9,9]` 1.00 promote | `[9,9,9,15]` 0.75 reject |

**8 of 9 model×seed arms promote, while the archived realization rejected.** The same-model Qwen4 control promotes in 3/3, so the historical→replay flip cannot be attributed to substituting the model: it is a property of a four-sample gate evaluated on a stochastic decoder. The archived rejection rests on a single draw in which the original model answered node 15 once.

**Consequence for the manuscript.** Any passage presenting the E4.1 rejection as evidence that the gate discriminates correctly does not survive replay and must be rewritten or removed.

### 10.2 Gloves candidate (E4b.1) — fully replayable

All three models, under all three seed bases, reproduce `[9,9,9,9]` and promote at consistency 1.00, matching the archive. This is a **robust cross-model, cross-seed promotion**, and it is the promotion example the manuscript can rely on.

### 10.3 Delivery candidate — partial counterfactual only

Only 3 of the 4 induction records are image-complete; the fourth (`audit_20260821_144154.jsonl`) escalated at run time and has no `image_start`. It is held fixed as `None` for every source, including the archive, so the denominator is identical across arms. All 9 model×seed calculations remain **rejected**, at consistency 0.25–0.75:

| Model | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| qwen3.5:4b | `[23,9,·,None]` 0.25 | `[1,9,5,None]` 0.25 | `[·,·,15,None]` 0.25 |
| gemma4:e2b | `[9,9,9,None]` 0.75 | `[9,9,9,None]` 0.75 | `[9,9,9,None]` 0.75 |
| qwen3.5:9b | `[23,23,-1,None]` 0.50 | `[10,23,23,None]` 0.50 | `[23,23,23,None]` 0.75 |

(`·` = no contract-valid node.) The rejection is stable, but the *reason* differs by model: Qwen4 rejects through instability and contract failures, Gemma through a consistent 3-of-4 that still misses the 0.80 threshold. **This is not a full model-substitution counterfactual**, and the text-only `no_image` output is deliberately not inserted into the promotion chain, because it is not the original multimodal condition.

Scientific conclusion for M3: the promotion gate measures **stability of sampled outputs**, not semantic truth. Some associations are robust across models and seeds (E4b); boundary cases can flip under a rerun of the *same* model (quiet corner).

## 11. Methodological note — the seed schedule

Seeds are derived per record as `(base_seed × 1000003 + int(md5(record_key)[:8], 16)) mod (2³¹ − 1)`, identical across arms for any given record and different across passes. Both the base and the derived value are written to every CSV row.

Distinct deterministic per-record seed initialization was used deliberately, rather than applying one common seed across the entire record set. Every reply in the cohort opens from a near-identical distribution — each must emit a JSON object and the `node_id` key — so a single shared RNG state would replay the same early draw on every record and correlate the sampling error across the arm instead of averaging it out.

Describe the schedule as *distinct deterministic per-record RNG initialization*. The seeds enable controlled repetition; they neither guarantee bit-identical GPU inference nor establish statistical independence between records.

*(A development-phase measurement quantifying the single-seed effect exists but is deliberately excluded from this report: it was taken on an acquisition that is not part of the frozen v3 artifact, and reproducibility claims here rest only on v3. It is retained as an internal engineering note.)*

## 12. Reviewer-facing conclusion and wording

Recommended core claim:

> The controlled replay demonstrates **model portability at the L3b application interface**: two alternative VLMs can consume the frozen multimodal prompt and return the required machine-readable destination contract without model-specific prompt or parser changes. However, destination selection, negation interpretation, latency, and low-sample M3 promotion behaviour remain model- and sampling-dependent. We therefore do not claim semantic model invariance, nor unconditional performance across all Session E VLM-path attempts.

Do **not** use "model agnostic" as shorthand for semantic equivalence. Prefer **model-portable interface**, **model-substitution replay**, or **interface-level model portability**.

## 13. Coverage statement for the manuscript

> The model-substitution replay evaluates the L3b semantic destination-selection path only. The post-navigation visual-confirmation module is a separate VLM interface, using a distinct prompt, API endpoint and inference configuration, and was not included in the model-substitution experiment.

And in Limitations:

> Accordingly, the reported model-portability evidence applies to L3b reasoning and its downstream M3 promotion behaviour, not to the separate post-arrival VLM confirmation module.

Successful missions whose destination carries a visual signature may invoke that second, post-arrival VLM path; pose-based confirmations do not. Across the Session E audits, 165 of 226 decisions carry a confirmation block: 108 `vlm_landmark`, 34 `vlm_contextual`, 23 `pose_based`.

## 14. Methodological limitations that must accompany the result

1. The multimodal replay covers 69 accepted-node, image-complete original outcomes; 68 remain after the E0 exclusion. It does not estimate alternative-model behaviour over the full 105 Session E VLM-path attempts, and it is outcome-conditioned on the original model having succeeded.
2. The archived node is a reference outcome, not ground truth; exact agreement is not semantic accuracy. The control arm reproduces it only 61.8–72.1% of the time.
3. Three prespecified seed bases characterize, but do not exhaust, decoder variability. See §11 for what the per-record schedule does and does not guarantee.
4. The replay tests only the L3b semantic destination-selection path (§13).
5. The delivery-promotion candidate lacks one original image; only the quiet-corner and E4b chains are fully multimodally replayable.
6. Latency is same-machine descriptive evidence, not a hardware-independent model benchmark.
7. For the 22 guard-handled negation activations the parsed VLM proposal is preserved as `node_id = -1`, but the raw reply text, the reason, and the pre-navigation image were not persisted. Their original clarification behaviour can therefore be characterized, whereas alternative-model multimodal behaviour on these records cannot be estimated.

## 15. Revision history

### Corrections applied in rev. 2 (retained)

| # | Location | Change |
|---|---|---|
| 1 | §3 | "No accepted outcome" split into abstention-on-negation, abstention-elsewhere, and unparseable contract. The single non-negation abstention is named: qwen3.5:9b, seed 1, record `49_20260821_144722_s001`. |
| 2 | §8 | New section. Failure morphology was computed in rev. 1 but never printed. |
| 3 | §7 | Rev. 1 wrote "0/39" for forbidden selections in a section opening with "13 of the 39 original negation activations" — two unrelated counts of 39. Now stated as 0/117 replay outcomes. |
| 4 | §10.1 | Added the explicit consequence for the manuscript: the archived E4.1 rejection cannot be presented as evidence that the gate discriminates. |
| 5 | analysis script | Dead code at lines 348–353 (`rep = as_int(man[k] if False else 0)`), and the delivery reconstruction hardcodes the missing record as the second repetition. The assumption is correct but irrelevant — consistency is order-independent — and the code implies a dependency that does not exist. |

### Corrections applied in rev. 3

| # | Location | Change |
|---|---|---|
| 6 | §2.1, §7, §14.7 | **Reverses an error introduced by rev. 2.** Rev. 1 described the 22 `L3b_vlm_negation_blocked` records as original abstentions. Rev. 2 rejected that, arguing from `vlm_response: null` that the model's reply was unrecoverable. That was an overcorrection reached from an incomplete read of the audit record: `extra.vlm_proposed_node` preserves the parsed proposal and is `-1` in all 22, with `extra.vlm_negation_check = "vlm_requested_clarification"`, and the frozen navigator sets `vlm_proposed_node` before the guard runs. Rev. 1's accounting was correct. What is genuinely unrecoverable is the raw reply text and the `image_start` frame — which is why these records cannot enter the replay, and is the only limitation that should be stated. |
| 7 | §7 | Rewritten around the full negation population rather than the replayable subset. Adds the verification result that motivated it: across all 35 activations reaching the guard, `vlm_negation_check` took only the values `vlm_requested_clarification` (22) and `ok` (13) — **no `vlm_violated_negation` ever occurred**, so the original model never proposed a forbidden node. Adds the original model's own clarification rate over the full population (22/35 = 62.9%) as the correct reference for replay abstention rates. Rev. 2's claim that "the archive never abstained" was true only within the cohort and was a pure selection artifact. |
| 8 | §3 | "Strict JSON+integer contract" renamed **parser-contract compliance**, with the parser's actual behaviour stated. The frozen parser also accepts the first JSON object extracted from surrounding prose, so "strict JSON" overstated the requirement. Counts unchanged (181/204, 204/204, 199/204). |
| 9 | §11 | The quantitative single-seed measurement is removed from the frozen report. It was taken on an acquisition that is not part of the frozen v3 artifact, and reproducibility claims here must rest on v3 alone. The design rationale is retained; the figure survives as an internal engineering note. |

### Freeze correction applied in R210-AN-02

| # | Location | Change |
|---|---|---|
| 10 | §7.2–§7.3 | Separated the original full-population clarification rate (22/35 = 62.9%) from the outcome-conditioned replay abstention rates. The former is descriptive context only and is not a denominator-matched comparator for the replay cohort. |
| 11 | §7.3 | Removed the original-model full-population row from the replay table and replaced the guard interpretation with a defense-in-depth claim consistent with the observation that neither Session E nor the replayable subset contained a forbidden-node proposal. |

No figure has changed since rev. 1. Every number in this report has been independently recomputed twice from the frozen acquisition.
