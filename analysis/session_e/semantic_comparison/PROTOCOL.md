# Semantic comparison: controlled M3 ablation and offline decision latency

**Protocol identifier:** `a4_semantic_comparison_20261005`  
**Date:** 5 October 2026  
**Scope:** offline semantic-resolution comparison of three target-resolution configurations.  
**Status:** release copy of the sealed protocol (`sealed/protocol/`). Editorial changes only: internal workflow references, a pre-execution feasibility check and internal infrastructure names are removed. Configurations, measurements, controls and rules are unchanged; the sealed original remains the reference for execution.  
**Operator:** Bogdan-Felician Abaza.

## 1. Objective and required outputs

Compare the complete system, the hybrid system with M3 Step 0 disabled while retaining M1/M2, and VLM-direct target resolution. Evaluate the same instructions and context, including familiar associations, unseen formulations and cases requiring clarification. Distinguish acceptable selections, incorrect executable decisions, clarification requests and model/parser failures. Measure complete offline instruction-to-decision latency alongside resolver computation time.

A-B estimates M3 target reuse; B-C estimates the deterministic cascade; A-C describes the complete routing contrast. The implementation must produce all required measurements even when the result is equality or disadvantage. No outcome-dependent sample extension, relabelling, parameter tuning or selective rerun is permitted.

| Requirement | Prespecified output |
|---|---|
| Three configurations on the same inputs | Paired A/B/C records, identical context and L3b payload hashes whenever invoked |
| Three instruction strata | Familiar, unseen and clarification-required results, with explicit distinct-item denominators |
| Four final outcome classes | Per-observation and per-item tables, parser failure never scored as clarification |
| Contribution of M3 and the cascade | Better/worse/tied paired counts, correctness, wrong executable outcomes and VLM invocation |
| Resolver computation | Applicable resolver time for A/B, including escalation attempts; C is not applicable |
| Complete decision latency | Monotonic instruction-to-decision timing, including image preparation on the VLM path, parsing and validation |
| Comparable runtime state | Dedicated inference service, fresh runner, empty preload, balanced arm positions and complete runtime logs |
| Limited conclusions | Offline semantic resolution; fixed workload; five familiar cases support descriptive conclusions |

Use the first technically valid completed run of each condition. Technical qualification calls are excluded from comparative outcome and latency estimates. Existing frozen records are preserved.

The matcher-boundary challenge, guard-branch test, navigation-denominator analysis, confirmation/AprilTag reporting and independent E7 adjudication are separate analyses; none is an input to, or a prerequisite of, this comparison.

## 2. Experimental boundary

The station experiment measures **offline semantic resolution**, not physical navigation, live perception acquisition, multi-robot throughput or end-to-end mission time. The model is loaded before the decision timer starts. Each timed VLM request is the first evaluation of its image and semantic prompt in a newly instantiated model runner.

The measured decision time includes local HTTP/API transport to the inference server. It excludes live camera acquisition, robot-to-workstation communication, robot motion, model preparation, experiment orchestration and result-file writes. No separately measured camera time is added to the offline decision time.

M1/M2 inputs are held constant across arms. S versus H changes the dynamic object context; it is not an M1/M2 ablation. This protocol does not establish generality across buildings, independently learned human preferences, physical safety guarantees or superiority over external navigation systems.

## 3. Frozen system and evidence

Use the released input data at `ras-revision-rc1.1`, commit `cde9307`, and the frozen deployed target-resolution modules from commit `f973aa0`. Record full commit IDs, clean-tree state where available, and SHA256 for every actually used module. Do not change the resolver, parser, guard, policy, prompts, model weights or operational thresholds to improve outcomes.

Primary inference model: `qwen3.5:4b`, digest `0c8faadc50c205b83c634430c1dae6d1a4896c9b818cb8f290aa34d535265018`, quantization Q4_K_M. Freeze the complete model description and API response, Ollama executable/version, driver, GPU, CPU, RAM, operating system, Python and installed dependency versions, model template, relevant server environment and placement on CPU/GPU. Verify the installed backend rather than assuming that current online documentation describes every field it exposes.

Inference settings for measured requests: `num_predict=500`, `temperature=0.3`, `num_ctx=16384`, `top_k=20`, `top_p=0.95`, `presence_penalty=1.5`, `think=false`, non-streaming single-user `/api/chat` request, one archived image. Explicitly retain the model throughout each measured request. No conversation history, previous context tokens, extra cache-busting text, altered image or shortened prompt is supplied.

Each context bundle contains instruction, graph, static semantic objects, pose, dynamic context condition, historical digest, common negation envelope, current node, archived image, canonical L3b prompt and all provenance hashes. All arm-specific indexes are prepared before the timed instruction arrives; index compilation cost is not presented as per-instruction resolver cost.

The released Session E data and records remain byte-identical to `ras-revision-rc1.1`.

## 4. Population and context

### 4.1 Primary condition S

Use the fixed 38 instruction-context items with available archived start images:

| Source | Items | Semantic stratum |
|---|---:|---|
| Familiar stored associations | 5 | 5 familiar-association items |
| E7 | 25 | 23 unseen formulations and 2 clarification-required items |
| E2 | 8 | 4 unseen formulations/exclusions and 4 clarification-required prohibitions |
| Total | 38 | 5 familiar; 27 unseen; 6 clarification-required |

S uses an empty transient dynamic-object store, a documented standardised context state. It retains the item's image, pose, static objects, graph, memory and safety envelope. It is not described as reconstruction of the exact historical dynamic state.

“Unseen formulation” denotes a formulation not stored in the applicable memory, not a newly collected independent holdout for this evaluation. The archive-derived sample is fixed; the evaluation does not claim that investigators have never seen its earlier outcomes.

The nine records without an archived start image are excluded by input completeness: E7 S-P2, P-P4, H-P3 and E2 N02, N04, N05, N06, N09, N10. Their omission is disclosed; no image from a different time is substituted. Archive completeness does not imply missingness at random.

### 4.2 Context sensitivity H

Use the 28 items with a same-cycle archived dynamic prompt: 20 E7 and 8 E2. Replay dynamic object entries and their printed same-cycle distances. Keep all other inputs identical to S. This is prompt-context replay, not independent reconstruction of YOLO geometry or the unique AMCL pose. H contains no familiar-association item and cannot estimate M3's effect in that stratum.

Analyse S and H separately. Compare them only on their 28 common items. The two populations are not pooled with one another or with physical-run results.

### 4.3 Parent selection

E7 uses the first frozen observation of each cell. M3 and E2 use the first chronological protocol-valid observation with an archived start image, without success-based selection. Retain parent run, cycle, repetition, selection reason and completeness limitation. For E2-X02 and X03, the selected second repetitions are disclosed because the first repetitions lacked images and had adverse outcomes.

For same-cycle archived prompts, the context pose reproduces the printed distance constraints within their rounding cells. Otherwise use the archived start pose. Record provenance explicitly; do not interpret a prompt-equivalent pose as exact localisation ground truth.

## 5. Fixed semantic references

Familiar items are scored against the stored association in the parent's historical digest, explicitly interpreted as association reuse rather than proof of a unique natural-language destination. The fifth familiar item uses its E4b digest.

E7 uses the original sealed acceptable-node sets. G-3 and H-P2 require clarification under that reference. A parser failure is always incorrect, including on clarification-required items. Record acceptable sets and their provenance in the manifest before executing this comparison.

For E2 prohibitions N, clarification/no target is correct. For exclusions X, a valid target must be outside the forbidden set and different from the current node derived from the frozen context pose; an instruction requesting motion is not fulfilled by returning the current node. Retain `same_node_no_motion` as a subflag.

Independent E7 adjudication, when available, is reported as a separately identified semantic-reference sensitivity table over the applicable E7 items; it does not change this comparison's original key, requests, routing or timings.

Legacy graph names and semantic-object anchoring are distinct provenance fields. Node 14 hosts the north window despite its stale plant name; plant_5 is anchored to node 15. Preserve the frozen environment and disclose this limitation rather than silently repairing it during evaluation.

## 6. Arms and controlled contrasts

| Arm | Target selection | Shared components |
|---|---|---|
| A: complete | M3 Step 0; deterministic Steps 1-6; VLM on escalation | Frozen context, M1/M2 prefix, negation envelope, L3b prompt, parser, forbidden-node guard, structural policy |
| B: without M3 target reuse | Step 0 disabled; Steps 1-6; VLM on escalation | Same shared components |
| C: VLM-direct | All target-selection Steps 0-6 bypassed; VLM on every item | Same shared components |

The forbidden-node envelope is an input held constant across arms, not re-estimated under each arm. Independently verify that the frozen negation mechanism reproduces that envelope. A-B isolates M3's **target-reuse contribution conditional on this common safety input**, not removal of every historical use of M3. B-C isolates deterministic target selection. A-C describes the complete routing contrast.

C is named “VLM-direct target resolution under common validation safeguards”. It does not bypass parser or safety validation. When different arms reach the VLM for the same item/condition/seed, request payload hashes must agree. Response equality is measured; it is not assumed or enforced.

## 7. Repetitions, schedule and cost

The primary unit is the instruction-context item. Three paired seed bases, {1,2,3}, are repeated observations, not additional independent cases.

For item `i` and condition `k`, let `h` be the integer represented by the first eight hexadecimal characters of MD5(`i|k`). The model seed is `(base * 1000003 + h) mod (2^31 - 1)`, identical across arms. This fixes input sampling parameters without asserting that the backend is perfectly deterministic.

For each condition, sort item IDs lexicographically and index them from zero. Even-indexed items receive the three orders ABC, BCA, CAB for bases 1,2,3; odd-indexed items receive ACB, CBA, BAC. Thus each arm occupies each within-item position once. Across S, each of the six orders occurs 19 times; across H, each occurs 14 times.

Sort item-seed blocks by the hexadecimal SHA256 of `20261005|condition|item_id|base`, with the literal tuple as tie-breaker. Keep the three arms of a block adjacent. Generate and hash the full schedule before execution. Run S and then H; this condition order limits interpretation of elapsed session effects and does not create an arm-order confound.

Measured observations: S 38*3*3 = **342**, H 28*3*3 = **252**, total **594**. Maximum measured VLM requests is 594; A/B may use fewer. Backend preparation calls and qualification calls are additional and separately counted. This is an observation budget, not a promise of a particular wall-clock duration.

## 8. Qualified runtime state and station execution

### 8.1 Dedicated service and fixed environment

Use a dedicated, operator-owned Ollama service on `127.0.0.1:11435`, started without sudo using `/usr/local/bin/ollama`, `OLLAMA_MODELS=/usr/share/ollama/.ollama/models` and `OLLAMA_NOPRUNE=1`. Freeze the complete launched command and inherited environment, including runtime-relevant values beyond these variables. The systemd service on port 11434 is not stopped or reconfigured.

Record Ollama 0.30.2 and its binary hash, exact model digest, Q4_K_M, driver and hardware in the station inventory. Before every preparation, confirm through the system service's `/api/ps` that it has no loaded model. Record other GPU workloads; no competing inference client or model is allowed during measurement. This prevents contention independently of whether two copies might fit in nominal VRAM.

### 8.2 Preparation before every arm-seed observation

The selected operating state is **model resident, fresh inference runner, first item prompt/image evaluation**, after session-level technical qualification. It is not production steady-state cache throughput or cold model-start latency. OS file caches are not purged.

Before every observation, including deterministic outcomes:

1. Stop only the dedicated evaluation service and confirm termination of its runner descendants. Record PID together with process start time/generation, because PID alone can be reused. No child runner may survive into the next observation.
2. Start a new dedicated service with the frozen configuration. Confirm readiness and empty `/api/ps` on 11435. Record service identity and the empty inventory.
3. Preload with an empty `/api/generate` request, `keep_alive=-1`, `num_ctx=16384` and the same relevant runtime options. No evaluation instruction, image or generated warm-up text is supplied. Capture the preload envelope.
4. Confirm the exact model digest, context length, runner identity and GPU placement after preload. Immediately pass the instruction into the timed resolver. Confirm after inference that the runner was not replaced between preload and the measured request.

All preparation is outside the decision timer and logged separately. Do not change prompts/images to defeat caching. Preload must not evaluate the item's prompt. Retain the measured model across its one request; kill its runner only after the observation and audit evidence have been captured.

### 8.3 Twelve-call qualification and continuity

Immediately before each measured condition, use the outside-manifest record `20260821_143713#1`, its exact archived image/prompt, frozen options and seed:

- R: one fresh service and empty preload, followed by six identical-payload calls on the retained runner.
- I: six calls, each after its own stop/start/empty-inventory/preload sequence.

Archive all twelve complete responses and server/runner logs. None enters outcome counts, VLM-invocation denominators or latency estimates. The first qualification call may pay session-start costs; those calls establish the warm-session operating state, not a system-quality outcome.

The experimental specification and executable inputs are sealed before station qualification. The qualification report references the SHA256 of that immutable `SEAL.json` and the verified inventory of execution files and external dependencies. Each condition's run references both that seal and its own qualification report by full SHA256. Qualification and run evidence are new append-only artifacts, subsequently included in the result freeze; they are not inserted retrospectively into, or used to modify, the input seal. Verify the seal before qualification and again before the first measured preparation, using an automated handoff that preserves the continuity limit below. A post-run analysis check complements these pre-execution checks.

Start the first measured preparation within **60 seconds** of qualification completion. During measurement, an unplanned idle interval longer than 60 seconds between a completed observation and the start of the next preparation invalidates continuity. Time actively spent in the prescribed preparation, current model request or automated logging is not an operator idle interval; unusually slow preparation is logged and investigated under the runtime checks. Do not interrupt a valid slow model call merely because it exceeds 60 seconds.

A pause between S and H is allowed because H receives its own full qualification immediately before its measured run. An idle break inside a measured condition stops that condition as incomplete; rerun the whole condition under the same sealed schedule after fresh qualification. Do not splice pre-pause and post-pause measurements.

### 8.4 Isolation evidence and API fields

Qualification and every measured request require empty pre-load inventory, new runner lifetime, correct post-load digest/context/placement, terminated predecessor runners and unchanged runner between preload and inference. Timing alone is not certification of isolation.

For the reported installed Ollama 0.30.2, `prompt_eval_cached_count` is absent. Store `null` with status `unavailable_in_0.30.2`; never synthesize zero. `prompt_eval_count` measures input tokens and must not be treated as the number of uncached tokens. Retain full API envelopes and original-nanosecond `total_duration`, `load_duration`, `prompt_eval_duration`, `eval_duration`, plus token counts, `done_reason`, complete content and thinking. Capture missing-field status separately for any other unavailable field.

On the qualification payload (2,734 tokens plus image), retained-runner prefill is near 29 ms and isolated-runner prefill near 5.8 s, which distinguishes reused from fresh computation for that payload. Other evaluation items have different prompt/image workloads: **do not impose a universal 5.84-second prefill threshold or discard fast/slow items on that basis**. Runtime lifecycle evidence is the primary gate; prefill duration is corroborating evidence and a mechanism diagnostic.

Likewise, byte-identical replies on one payload do not guarantee identical replies throughout the experiment. Compare outputs; do not enforce or assume equality. Prompt cache reuse concerns reused computation, not demonstrated storage of a complete answer.

### 8.5 Session state and long-run monitoring

First-session costs are not separately attributed to disk I/O, GPU initialisation, thermal state or other startup mechanisms; they are described as session-start sensitivity, without assigning a precise cause.

Capture GPU temperature, clocks, utilisation, power and reported throttle reasons, where the driver exposes them, with UTC and monotonic timestamps every **5 seconds** through qualification and measurement. Freeze the supported field list; unsupported fields remain unavailable. Record GPU placement/VRAM after every preload and check for competing processes.

Retain the frozen balanced item-seed schedule. As a descriptive runtime audit, show latency and thermal/clock traces against elapsed time and summarise each arm's position counts. Do not discard slow valid observations, select a favourable session segment, or recalibrate semantic prompts based on thermal trends. Throttling observed without a protocol violation is reported as a limitation of the actual session, not silently removed. A hardware/backend configuration change or competing model invalidates the condition.

### 8.6 API durations

API `total_duration` remains a backend diagnostic. It does not replace the full instruction-to-decision timer, which also includes resolver, input preparation, parser and validation.

## 9. Timer boundaries and outcome classification

### 9.1 Decision clock

Use a monotonic high-resolution clock, `time.perf_counter_ns`. Load and verify context, memory indexes and the common safety envelope before the instruction arrives. They represent resident runtime state. Record these setup costs separately.

Start the main timer immediately before raw instruction processing. Include normalisation/tokenisation, target resolver, archived-image reading and base64 conversion on the VLM path, prefix/prompt construction, payload serialization, local API call, response decoding, parser, guard and structural validation. End when the semantic decision is available: executable target, explicit clarification or model/parser failure.

Reference-key scoring, acceptable/incorrect labelling against the key, result serialization and log writes occur **after** this timer. The executable system does not consult the reference key. Instrumentation is identical across arms.

Record separately: target-resolver computation; image/prompt preparation; API wall time; parsing; guard/validation; main decision time. Resolver time includes all target-resolution Steps 0-6 executed, whether they resolve or escalate. C has resolver time `null/not_applicable`, not a fabricated zero. Instrumented intervals must be nonnegative and consistent with the enclosing main interval; backend internal durations need not sum to client wall time.

### 9.2 Four outcome classes

| Class | Rule |
|---|---|
| Acceptable selection | Structurally allowed graph target in the reference acceptable set |
| Incorrect executable decision | Structurally allowed graph target outside that set, including a target where clarification is required |
| Clarification/abstention | Explicit valid `node_id=-1`, forbidden-node rejection or recorded structural-policy rejection |
| Model/parser failure | Response cannot be decoded into the required contract, non-integer/boolean target, missing target or target outside the graph other than -1 |

Retain parser/contract, explicit -1, guard and structural-policy subflags. Apply parser validity before interpreting a target or abstention. A valid but wrong executable node is not a parser failure. Structural-policy rejection is distinguishable from a semantic request for clarification even when they share the aggregate class.

For target-required items, correct means acceptable selection. For clarification-required items, correct means clarification/abstention, with its actual mechanism reported. Parser failure is always incorrect. Synthetic guard controls do not enter these station-population counts.

## 10. Station analysis and indicators

### 10.1 Integrity

Require completed header, exact sealed schedule keys, one record per item-condition-arm-base, correct seeds, valid schema and all input/code/runtime hashes. Require the complete response envelope and runtime preparation evidence for each VLM observation. Count model/parser failures without exclusion from semantic or timing summaries.

### 10.2 Semantics and routing

For each condition and arm, overall and by the three semantic strata, report:

- all four outcome counts over item-seed observations, always showing the number of distinct items;
- per-item correct-seed counts (0-3), and primary item correctness defined as at least 2 of 3 correct;
- acceptable selections, wrong executable decisions, requested clarifications and parser failures separately; no failure-as-abstention conflation;
- paired A-B, B-C and A-C counts of items better/worse/tied in correct-seed count;
- each arm's invocation count/number of observations, number of distinct items invoking the VLM, L3a coverage and resolution-step distribution;
- fast-path error incidence = wrong executable L3a decisions / all observations;
- fast-path conditional error = wrong executable L3a decisions / all L3a decisions;
- erroneous L3a resolution on clarification-required items / all clarification-required observations;
- seed agreement for outcome class and selected node, plus distinct items affected by model/parser failure.

A zero denominator is `not applicable`, not zero error. Report observation ratios and distinct-item summaries together; seeds are not independent sample-size inflation.

Item correctness receives descriptive Wilson intervals. Paired differences in item correctness and VLM-call fractions receive stratified paired item-bootstrap intervals with 10,000 resamples, analysis seed 20261005; each resampled item retains all its arm/seed records. Report the point differences and better/worse/tied counts regardless of interval width. A two-sided exact sign test on non-tied item correct-seed differences may be shown as descriptive; no five-item stratum significance claim or equivalence claim is made. Generalisation beyond the fixed workload is not implied by these intervals.

### 10.3 Timing

For decision time and applicable resolver time, report observation-level median, IQR, arithmetic mean and min-max, overall/by stratum, with sample denominators. Also report the distribution of each item's median across its three seeds. Include failed responses because they consume decision time. Failure-specific summaries are additional, not replacements for all-outcome latency.

For each item, compute median decision time per arm. For contrasts A-B, B-C, A-C report paired millisecond differences, median of paired item ratios and stratified paired item-bootstrap 95% intervals using the procedure above. The ratio is explicitly named, e.g. C/A > 1 means A is faster on that item. Do not divide by a rounded zero; retain nanosecond data and declare an undefined ratio if necessary. Never present the ratio of pooled means as the median paired ratio.

The primary latency comparison includes all items in each stratum. VLM-path-only summaries are descriptive conditional quantities because routing changes the populations reaching the VLM. A timing comparison restricted to common VLM calls may additionally use identical item-seed keys, with its restricted denominator disclosed. Output length, input tokens, prefill and decoding times describe mechanisms; they are not post-hoc criteria for filtering the primary comparison.

### 10.4 Context and references

Compare S-H on the 28 common items, per arm, using paired correctness, node/outcome changes, all four outcome counts and VLM invocation. Report sensitivity to the specified dynamic context. Do not infer robustness from a mixed direction or equal aggregate accuracy. H and S latency are reported separately, with the fixed condition order disclosed.

If independently adjudicated E7 judgments become available from the separate workflow, add their scoring as a separate semantic-reference sensitivity table without changing requests, routing, timing or the original key. This is not a new adjudication procedure or a blocking station gate.

## 11. Implementation acceptance, seal and execution

These are technical acceptance checks completed before execution.

1. Every required indicator has a schema field and tested analysis path. Required timers and denominators are defined before model execution.
2. Verify frozen inputs and prompt construction: 105 archived prompts, 69 historical copies, S projections, 38 common negation envelopes and all current bundle hashes. The shared envelope is verified, not replaced by a new guard experiment.
3. Synthetic harness/analysis cases cover four outcomes, clarification versus failure, same-node exclusion, paired contrasts, zero denominators, ratio direction and item-clustered uncertainty.
4. Timing tests prove separate resolver instrumentation, scoring after the main timer and retention of full API envelopes. The system never consults scoring keys while producing a decision.
5. Dry-run checks cover exact 342/252 schedules, seed pairing, balanced arm positions, payload identity and preparation before each observation. Preparation/qualification calls are excluded from measured invocation counts.
6. Complete local implementation acceptance and prepare the station inventory and dependency manifest. Seal this protocol, comparison manifest/keys, bundles, schedule, all execution/analysis/test scripts, timer definitions and prescribed runtime settings on the preparation workstation. Record full SHA256 for every file and actual operator/UTC in `SEAL.json`; create a new read-only set without overwriting an existing seal. The separate analyses of this release are not requirements of this seal. Do not require future condition-specific qualification evidence in this input seal.
7. Transfer the sealed comparison tree with the protocol, immutable input seal and all required orchestration/check scripts. Every external file actually consumed must be listed by exact relative path and full SHA256 in the sealed dependency manifest. Verify those files, the complete sealed input set and station runtime settings before qualification; repeat the prescribed checks at runtime. Unchanged Python files alone do not establish unchanged data, policy, images or keys.
8. On the station, run the sealed harness's twelve-call qualification immediately before S; automatically verify the input seal and enter measured execution within the section 8.3 limit. Repeat qualification immediately before H. Verify fresh-runner lifecycle, unchanged runtime settings, GPU placement and thermal logger. Qualification reports and run headers record the input seal's full hash. No return to the preparation workstation and no new input sealing occurs between qualification and execution.
9. Analyse the first valid completed run of each condition, verify all inputs and references against the input seal and freeze this comparison's result set, including qualification, runtime inventory, process/thermal logs and analysis. This result freeze is separate from the immutable input seal.

The protected deployed modules are held unchanged. Only execution orchestration, timing instrumentation, response capture and analysis implementation are modified for this experiment.

## 12. Failure and stopping rules

Infrastructure failure means no model response: HTTP error status, connection loss, timeout or unreadable API envelope. Stop the condition and mark it incomplete. Runtime-lifecycle violation, competing model, configuration change or the specified idle break also stops/invalidate the condition. Retain all partial records and logs.

Repeat an affected condition in full under the same sealed schedule and inputs in a new directory, after fresh qualification. Maximum three attempts per condition. Analyse the first valid completed attempt; never stitch partial attempts or replace individual adverse observations. A received model response that fails the parser is a valid recorded outcome, not an infrastructure rerun trigger.

No outcomes may be used to change the sample, labels, prompts or operational parameters. Missing qualification, incomplete timers or a failed runtime-state gate means the comparison is not yet valid, not that a subset of its results can be presented as the complete experiment.

## 13. Interpretation and comparison deliverables

Assess quality, invocation and latency separately. For each prespecified stratum/contrast, evidence consistent with a descriptive quality benefit requires at least one better item, no worse item and no increase in wrong executable decisions by observation count or affected-item count. Show parser failures alongside it. Mixed-direction results remain mixed; do not conceal worse items under a favourable aggregate. Apply the same predicate whichever arm is favoured.

Fewer VLM calls without deteriorating correctness or increasing wrong executable decisions supports a selective-invocation benefit. Otherwise describe the quality/call tradeoff. A latency advantage requires the valid selected runtime state and the paired latency analysis; an interval crossing zero for a difference or one for a ratio does not support a general directional claim. Equal observed correctness does not establish equivalence.

The five familiar items support limited descriptive association-reuse evidence, not broad M3 generalisation or independently learned operator preference. A microsecond resolver-to-VLM ratio is not the complete architecture's instruction-to-decision speedup. No physical-navigation benefit is inferred from offline target resolution.

Minimum comparative deliverables:

1. Population, parent inputs, context, three strata, exclusions and key provenance.
2. Four outcome classes and item-level correctness by arm/stratum.
3. Paired A-B, B-C and A-C results, wrong executable decisions, fast-path errors, seed agreement and VLM invocation.
4. Resolver computation and complete offline decision latency, stage timings, paired differences/ratios and uncertainty.
5. Separate S-H context sensitivity and, when available, separately identified external semantic-reference sensitivity.
6. Runtime qualification, preparation costs, supported API fields, process evidence and thermal/elapsed-time audit.
7. Sealed provenance, raw responses, complete per-observation/per-item tables and executable analysis scripts.

The protected resolver means the full comparison is verifiable but not publicly re-executable without those modules; state this precisely. Publish raw inputs/results and analysis scripts under the established release policy. Protected code is not published merely to simplify a reproducibility sentence.

Sources for runtime instrumentation: <https://docs.ollama.com/api/usage>, <https://docs.ollama.com/api/ps>, <https://docs.ollama.com/faq>. Installed-version behaviour is established by archived station evidence, not presumed from current documentation.
