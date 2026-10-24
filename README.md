# A Semantic Autonomy Framework for VLM-Integrated Indoor Mobile Robots

**Public evidence and reproducibility package for the article published in *Robotics and Autonomous Systems* 207 (2027) 105822**

[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.1016%2Fj.robot.2026.105822-blue.svg)](https://doi.org/10.1016/j.robot.2026.105822)
[![arXiv](https://img.shields.io/badge/arXiv-2605.02525-b31b1b.svg)](https://arxiv.org/abs/2605.02525)

This repository accompanies the article by **B. F. Abaza, A.-A. Staicu, and C. V. Doicin** on the Semantic Autonomy Stack (SAS) for VLM-integrated indoor mobile robots, published open access in *Robotics and Autonomous Systems* 207 (2027) 105822 ([DOI: 10.1016/j.robot.2026.105822](https://doi.org/10.1016/j.robot.2026.105822)). It is primarily a **public evidence and reproducibility package**, not a complete source-code release.

The release contains the development-stage Sessions A–C, the frozen `v4.8-review` Session E confirmatory physical campaign, supporting post-hoc analyses, a controlled L3b model-substitution replay, unified evidence indexes, and the public SAS text-processing module `data/session_e/public_code/sas_text.py`.

Release `ras-revision-rc1.2` adds new analyses without changing the Session E data or the RC1.1 analyses:
- a reanalysis of the E7 outcome classes and of the navigation denominators;
- a controlled offline comparison of semantic resolution and decision latency;
- an M3 decision-boundary challenge;
- an offline test of the forbidden-node guard branch;
- an independent adjudication of the E7 destination sets;
- a descriptive AprilTag summary;
- a live image-request transaction measurement.

See [`CHANGELOG.md`](CHANGELOG.md).

The inherited perception and route-planning foundation (L1–L2) is documented in the companion repository [nav2-semantic-route-server](https://github.com/bogdan-abaza/nav2-semantic-route-server) and the corresponding *Sensors* paper ([DOI: 10.3390/s26072232](https://doi.org/10.3390/s26072232)).

> **Reading note.** Some frozen analytical records preserve wording or quantitative formulations from the original submission because they are immutable audit records. Their presence does not make those formulations current claims. Current interpretation is governed by the published article, this README, [`docs/PUBLICATION_SCOPE.md`](docs/PUBLICATION_SCOPE.md) and [`docs/RC1_2_SCOPE_NOTES.md`](docs/RC1_2_SCOPE_NOTES.md).

> **Quick start.** Verify the published Session E package with `cd data/session_e && md5sum -c CHECKSUMS_PUBLIC.md5`; re-run the Session E core analysis with the command in §5; re-run the sealed analyses added in rc1.2 with `python3 tools/rerun_sealed.py all`; every headline value in §3 points to its governing public artifact; and [`docs/REPRODUCIBILITY_NOTES.md`](docs/REPRODUCIBILITY_NOTES.md) states which frozen procedures are executable from this release alone.

---

## 1. What the published work evaluates

SAS is a six-layer reference and integration framework:

| Layer | Role in SAS | Scope in this work |
|---|---|---|
| **L0** | Platform hardware | Inherited deployment foundation |
| **L1** | Navigation execution | Inherited from prior validated work |
| **L2** | Perception and semantic mapping | Inherited from prior validated work |
| **L3** | Semantic reasoning | Higher-layer focus: deterministic-first resolution, safeguards, L3b escalation, and post-arrival confirmation |
| **L4** | Mission interface | Higher-layer integration boundary between external instructions and robot reasoning/execution |
| **L5** | Operational intelligence and semantic memory | Higher-layer focus: scoped M1–M5 memory framework, with M3 promotion and shared-memory reuse directly demonstrated |

The revised experiments target the **higher-layer mechanisms and their integration with the inherited L0–L2 stack**. The inherited lower layers are not presented as newly developed or independently revalidated here.

### Hybrid deterministic–VLM reasoning

L3 uses a seven-step deterministic-first resolver for eligible instructions and escalates unresolved cases to VLM reasoning. The frozen `v4.8-review` implementation includes Step-0 acceptance threshold and runner-up margin checks, negation/exclusion precedence, location-conflict handling, action validation, audit logging, and post-arrival confirmation. Deterministic-path latency is reported as **sub-millisecond**, not as a generic sub-0.1-ms property.

The Session E control VLM is `qwen3.5:4b` via Ollama. The reported SAS pipeline uses **no task-specific model fine-tuning and no separately trained task classifier**.

### Scoped semantic memory

L5 defines five memory categories (M1–M5). The strongest direct experimental support concerns **M3 learned instruction–node associations**, their promotion into compiled memory, and deliberate **shared-memory reuse across robot platforms** after installation of the compiled artifact.

Here, adaptation means promoting recurrent instruction–node associations into deterministic rules for later reuse, without retraining the VLM; it does not denote online model learning or validated acquisition of human preferences. The promotion gate is a **sampled-output stability criterion**, not a semantic-correctness criterion. M1/M2 are exercised jointly with M3 in the whole compiled-memory-layer intervention. The added A/B comparison isolates M3 target reuse while holding the M1/M2 context constant; M4/M5 are implemented and described but are not independently evaluated for performance contribution. Shared-memory reuse is not autonomous peer-to-peer exchange or direct robot-to-robot learning.

### L3b interface contract and model substitution

The L3b path uses a structured executive contract over admissible actions, objects, destinations, and locations, with output validation before execution. Controlled replay with alternative evaluated VLMs supports **interface-level model portability under the frozen L3b interface**. It does **not** establish semantic model invariance.

---

## 2. Evidence model

The repository contains several evidence streams with different roles and experimental units. They must not be pooled as one validation population.

| Evidence stream | Role | Public location | Reproducibility status |
|---|---|---|---|
| **Sessions A–C** | Development-stage physical evidence across evolving implementations | `data/session_a/`, `data/session_b/`, `data/session_c/` | Raw evidence public; legacy analysis scripts retained |
| **Session E** | Confirmatory physical campaign for frozen `v4.8-review` | `data/session_e/` | Core quantitative analysis executable from the public release |
| **A1 — cascade analysis** | Post-hoc characterization of deterministic cascade use and latency | `analysis/session_e/A1_cascade/` | Frozen and self-verifying; original full input set is not entirely public |
| **A2 — M3 sensitivity** | Post-hoc parameter sensitivity around the frozen M3 matching settings | `analysis/session_e/A2_m3_sensitivity/` | Publicly reproducible |
| **A3 — promotion sensitivity** | Post-hoc characterization of the frozen promotion rule | `analysis/session_e/A3_m3_promotion/` | Frozen and self-verifying; original end-to-end historical reproduction path is not public |
| **R210 model replay** | Controlled L3b model-substitution replay supporting higher-layer reasoning/memory claims | `analysis/session_e/r210_model_replay/` | Publicly executable from the released replay package |
| **E7 and navigation reanalysis** (rc1.2) | E7 outcome classes with parse failures separated from clarification; fast-path measures; navigation measures conditional on dispatch | `analysis/session_e/rc1_2_reanalysis/` | Publicly executable |
| **Controlled semantic comparison** (rc1.2) | Offline comparison of the complete system, M3 Step 0 disabled, and direct VLM resolution; resolver and instruction-to-decision latency | `analysis/session_e/semantic_comparison/` | Post-run analysis publicly executable; execution verifiable, not re-executable (protected modules, model, GPU) |
| **M3 decision-boundary challenge** (rc1.2) | Labelled near-boundary set for the M3 matcher, with an exact-match baseline | `analysis/session_e/m3_boundary/` | Publicly executable |
| **Guard branch test** (rc1.2) | Offline injection of forbidden-node proposals into the deployed guard | `analysis/session_e/guard_branch/` | Verifiable, not re-executable (protected module) |
| **E7 independent adjudication** (rc1.2) | Blind independent judgment of the E7 acceptable-destination sets; sensitivity analysis | `analysis/session_e/e7_adjudication/` | Publicly executable |
| **AprilTag summary** (rc1.2) | Descriptive discrepancy summary from the published detections | `analysis/session_e/apriltag_summary/` | Publicly executable |
| **Live image-request transaction** (rc1.2) | HTTP image request through JSON decoding and base64 extraction for L3b, on Xplorer-B; frame age is not measured | `analysis/session_e/camera_transaction/` | Statistics recomputable; measurement requires the robot |

For the exact public-rerun boundary of each frozen analysis, see [`docs/REPRODUCIBILITY_NOTES.md`](docs/REPRODUCIBILITY_NOTES.md).

### Session E design at a glance

Session E is not one homogeneous benchmark. It is a set of block-specific experiments with different primary units.

| Block | Experimental purpose | Primary unit / N |
|---|---|---|
| **E0** | Frozen configuration/start gate | No performance N; excluded from primary rates |
| **E1 / E1b** | Post-arrival visual confirmation | E1b: 8 controlled trials, 4 present + 4 absent |
| **E2** | Negation/exclusion and location-conflict safeguards | 19 semantic-intent clusters; repetitions are not independent cases |
| **E3** | Resolver repeatability | 11 semantic-intent clusters |
| **E4** | Rejection of unstable candidate associations | 2 candidate instruction–node associations |
| **E4b** | Induction → compilation/install → recipient reuse | 1 induced association; 4 repeated recipient reuse observations |
| **E5** | Concurrent two-robot L3b operation | 3 concurrent pairs / 6 missions |
| **E6** | Whole compiled-memory-layer intervention | 4 instruction × platform paired units |
| **E7** | Sealed previously unseen instructions | 28 sealed cells; 29 archived cycles; Xplorer-B only |

Raw decision cycles are therefore not treated as independent experimental units by default; statistical interpretation follows the primary unit defined for each block. A1–A3 and R210 are post-hoc supporting analyses of frozen evidence, not additional physical Session E blocks.

**Frozen Session E configuration:** `v4.8-review`; Step-0 Jaccard threshold `0.75`; runner-up margin `0.10`; M3 promotion gate frequency `≥3`, rounded consistency `≥0.80`, and `≥1` accepted L3b observation; control VLM `qwen3.5:4b`.

### Session E population vocabulary

Session E contains **214 audit sessions**, **210 decision-bearing runs**, **226 decision cycles**, and **90 semantic units**. These terms are intentionally distinct. Population and denominator conventions are documented in [`data/SESSIONS.md`](data/SESSIONS.md) and [`docs/session_e_l3b_population_dictionary.md`](docs/session_e_l3b_population_dictionary.md).

For the L3b call path, the release distinguishes **105 call-path attempts**, **91 timed VLM records**, **69 accepted-node/image-complete records**, **22 negation-blocked clarifications**, and **14 unresolved escalation/error outcomes**. These counts answer different questions and should not be substituted for one another.

---

## 3. Headline results and claim boundaries

The values below use different experimental units. The rows should not be interpreted as one pooled benchmark.

| Result | Current interpretation | Governing public source |
|---|---|---|
| **Session E deterministic fast path** | 121/226 = **53.5%** of all archived decision cycles (95% CI [47.0%, 59.9%]); primary E0-excluded population: 112/216 = **51.9%** | `analysis/session_e/core/results_E.json` |
| **Deterministic-path latency** | **0.245 ms median**, 0.072–0.960 ms; 112/112 deterministic primary records < 1 ms | `analysis/session_e/A1_cascade/A1_cascade_step_results.json` |
| **Whole compiled-memory-layer ablation** | Paired within-instruction latency ratio: **75,500× median** (72,039–88,269×), n=4 paired units; this is not an M3-only ablation | `analysis/session_e/core/results_E.json` |
| **One-case recipient-reuse illustration** | **101,944×** latency ratio on Xplorer-B from one pre-promotion VLM baseline (n=1) to four post-promotion Step-0 observations; mechanistic illustration, not a population estimate | `analysis/session_e/core/results_E.json` |
| **Shared-memory reuse across robot platforms** | One independently induced instruction–node association was promoted and reused on the recipient in **4/4 repeated Step-0 observations without a VLM call**; repetitions are not independent transfer cases | `analysis/session_e/core/results_E.json` |
| **L3b model-substitution replay** | 69 accepted-node/image-complete replay records; primary E0-excluded cohort 68 records across 3 evaluated models (`qwen3.5:4b`, `qwen3.5:9b`, `gemma4:e2b`) × 3 seed bases; supports interface-level portability, not semantic invariance | `analysis/session_e/r210_model_replay/R210_AN_02_FROZEN_RESULTS.json` |
| **Sealed subset E7** | 28 sealed instruction cells and 29 archived decision cycles (one cell produced two decision cycles in one run); deterministic fast path **5/28 = 17.9%** (95% CI [7.9%, 35.6%]) at the cell level | `analysis/session_e/core/results_E.json` |
| **Physical validation scope** | Frozen Session E higher-layer integration on **two robot configurations in one indoor environment** | `analysis/session_e/core/results_E.json`; `data/SESSIONS.md` |

The current machine-readable Session E quantitative source is [`analysis/session_e/core/results_E.json`](analysis/session_e/core/results_E.json). Frozen prose reports are retained for auditability, but current quantitative interpretation follows the machine-readable sources and the digest-bound supersession policy described in [`docs/PUBLICATION_SCOPE.md`](docs/PUBLICATION_SCOPE.md).

### Results added in ras-revision-rc1.2

These are separate analyses with their own units; they are not pooled with the Session E rows above.

| Result | Current interpretation | Governing public source |
|---|---|---|
| **E7 outcome classes** | 17 acceptable selections, 6 incorrect executable decisions, 2 executable decisions where clarification was required (`executable_where_abstention_expected`), 3 model-response parse failures, 0 clarification requests (28 cells); false-fast incidence 1/28 (Wilson 95% 0.006–0.177); error among fast-path decisions 1/5 (0.036–0.625) | `analysis/session_e/rc1_2_reanalysis/rc1_2_reanalysis_results.json` |
| **Navigation denominators** | Terminal miss 1/199 over all protocol-valid runs (0.001–0.028) and 1/164 over runs that dispatched navigation (0.001–0.034); non-arrival after dispatch 2/164 (0.003–0.043), including one run ending `missed` and one ending `vlm_failed`; terminal outcomes: 162 `mission_complete`, 1 `missed`, 22 `clarification_requested`, 14 `vlm_failed`; these measures do not establish end-to-end semantic task success | same |
| **Controlled semantic comparison** | On five familiar associations, the complete system gave 15/15 acceptable selections without a VLM call, versus 11/15 with M3 Step 0 disabled and with direct VLM resolution; no incremental M3 benefit on unseen or clarification-required items; in the standardized condition, the deterministic cascade made the same decisions as direct VLM resolution with 99 instead of 114 VLM calls; offline semantic resolution only | `analysis/session_e/semantic_comparison/results/` |
| **M3 decision-boundary challenge** | At Jaccard 0.75 / margin 0.10: 14 correct and 11 wrong acceptances on 47 near-boundary items; exact match accepts none | `analysis/session_e/m3_boundary/sealed/results/` |
| **Guard branch test** | 27/27 forbidden proposals rejected, 14/14 permitted controls dispatched; the deployed parser dispatched a synthetic boolean `true` to node 1 in 14/14 contexts (no boolean proposal occurred in Session E) | `analysis/session_e/guard_branch/sealed/results/` |
| **E7 independent adjudication** | Destination-versus-clarification agreement 26/28 (not equality of acceptable-node sets); 16/28 under the evaluator's judgments, against 17/28 under the sealed key, which remains primary | `analysis/session_e/e7_adjudication/sealed/analysis/` |
| **AprilTag summary** | dx +0.208 m (SD 0.042, n = 11); 10 of 11 detections from one marker; no interval of the mean | `analysis/session_e/apriltag_summary/results/` |
| **Live image-request transaction** | Xplorer-B, image request to image available for L3b: median 57.3 ms (IQR 46.4–68.2; range 34.7–211.5; n = 50); separate from the offline comparison | `analysis/session_e/camera_transaction/` |

---

## 4. Where to find the evidence

| Question | Start here |
|---|---|
| What are the Session E populations and experimental units? | [`data/SESSIONS.md`](data/SESSIONS.md) |
| What is the canonical machine-readable Session E result set? | [`analysis/session_e/core/results_E.json`](analysis/session_e/core/results_E.json) |
| Where are the raw Session E records? | [`data/session_e/`](data/session_e/) |
| Where are the unified A–C / E indexes? | `data/sessions_index.csv`, `data/missions_index.csv`, `data/session_register.json` |
| How are the 105/91/69/22/14 L3b populations defined? | [`docs/session_e_l3b_population_dictionary.md`](docs/session_e_l3b_population_dictionary.md) |
| How is the deterministic cascade characterized? | [`analysis/session_e/A1_cascade/`](analysis/session_e/A1_cascade/) |
| Where is the M3 parameter sensitivity analysis? | [`analysis/session_e/A2_m3_sensitivity/`](analysis/session_e/A2_m3_sensitivity/) |
| Where is promotion-rule sensitivity characterized? | [`analysis/session_e/A3_m3_promotion/`](analysis/session_e/A3_m3_promotion/) |
| Where is the model-substitution replay? | [`analysis/session_e/r210_model_replay/`](analysis/session_e/r210_model_replay/) |
| Where is the sealed E7 set? | `data/session_e/day2_20260821/session/` and `data/session_e/day2_20260821/E7_seal.txt` |
| How were A–C records included/excluded? | `docs/ac_inclusion_funnel.csv` and [`docs/AC_EVIDENCE_NOTES.md`](docs/AC_EVIDENCE_NOTES.md) |
| Which memory digest was active at A–C startup? | `docs/ac_startup_digest_map.csv` |
| What is public and what is deliberately not public? | [`docs/PUBLICATION_SCOPE.md`](docs/PUBLICATION_SCOPE.md) |
| Which analyses are independently rerunnable from this release? | [`docs/REPRODUCIBILITY_NOTES.md`](docs/REPRODUCIBILITY_NOTES.md) |
| What changed in rc1.2, and which frozen wording is qualified? | [`CHANGELOG.md`](CHANGELOG.md), [`docs/RC1_2_SCOPE_NOTES.md`](docs/RC1_2_SCOPE_NOTES.md) |
| How do the configurations compare on the same instructions? | [`analysis/session_e/semantic_comparison/`](analysis/session_e/semantic_comparison/) |
| How does the M3 matcher behave near its thresholds? | [`analysis/session_e/m3_boundary/`](analysis/session_e/m3_boundary/) |
| How does the guard handle a forbidden-node proposal? | [`analysis/session_e/guard_branch/`](analysis/session_e/guard_branch/) |
| How do the E7 destination sets compare with an independent judgment? | [`analysis/session_e/e7_adjudication/`](analysis/session_e/e7_adjudication/) |
| What are the E7 outcome classes and navigation denominators? | [`analysis/session_e/rc1_2_reanalysis/`](analysis/session_e/rc1_2_reanalysis/) |

---

## 5. Quick verification and reproduction

### Verify the published Session E package

From the repository root:

```bash
cd data/session_e
md5sum -c CHECKSUMS_PUBLIC.md5
cd ../..
```

This verifies the integrity of the **published** Session E package. Reconstructing the dataset from the original delivery is a separate provenance operation and requires material outside the public release.

The released analyses make no network calls. Install any required third-party Python
dependencies separately if they are not already available.

### Re-run the Session E core analysis

```bash
PYTHONPATH=data/session_e/public_code \
python3 analysis/session_e/core/analyze_session_e.py \
    --dataset data/session_e \
    --outdir <your-outdir>
```

The public module `data/session_e/public_code/sas_text.py` is resolved through `PYTHONPATH`. With this public module, the released analyzer reproduces the reported Session E metrics. One auxiliary offline memory-extractor replay depends on a non-public production module; in its absence the analyzer reports that the auxiliary replay did not run, without changing the reproduced Session E metrics.

### Supporting analyses

Each supporting-analysis directory contains its own report, checksums, and reproduction or self-verification instructions where applicable:

- `analysis/session_e/A1_cascade/`
- `analysis/session_e/A2_m3_sensitivity/`
- `analysis/session_e/A3_m3_promotion/`
- `analysis/session_e/r210_model_replay/`

The R210 directory includes the frozen acquisition archives required for the controlled model-substitution recompute and is executable from the public release. See [`docs/REPRODUCIBILITY_NOTES.md`](docs/REPRODUCIBILITY_NOTES.md) for the precise boundary of every path.

### Analyses added in ras-revision-rc1.2

```bash
# E7 outcome classes and navigation denominators
PYTHONPATH=data/session_e/public_code python3 analysis/session_e/rc1_2_reanalysis/reanalyze_session_e.py \
    --dataset data/session_e --core analysis/session_e/core --outdir <your-outdir>

# sealed analyses: boundary challenge, E7 adjudication, semantic comparison, reference sensitivity
python3 tools/rerun_sealed.py all

# AprilTag summary
python3 analysis/session_e/apriltag_summary/apriltag_summary.py --out <your-outdir>
```

The sealed analyses verify the SHA-256 of their inputs before running. `tools/rerun_sealed.py` supplies the directory layout they expect in a temporary sandbox, without modifying any sealed file, and compares the regenerated outputs with the published ones. Every component directory contains `CHECKSUMS_SHA256.txt` (`sha256sum -c CHECKSUMS_SHA256.txt`).

---

## 6. Development-stage Sessions A–C

Sessions A–C are retained as **development-stage evidence**, not as confirmatory validation of the frozen `v4.8-review` system.

| Session | Robot | Raw audit records | Scenario-classified records | Development-stage role |
|---|---|---:|---:|---|
| A | Xplorer-C | 85 | 37 | M3-association and S3new learning-cycle observations |
| B | Xplorer-B | 76 | 41 | Recipient-side reuse of a deliberately installed compiled-memory artifact |
| C | Both | 4 | 4 | Concurrent two-platform operation observations |
| **Total** | | **165** | **82** | |

The public A–C funnel is **165 = 82 scenario-classified + 83 excluded**. The scenario subset is reproduced with `classify()` from `analysis/figures/data_loader.py`; the generated funnel is stored in `docs/ac_inclusion_funnel.csv`.

The compiled digest used in Sessions B and C is `data/memory/memory_digest.json` (MD5 `97241265217eb4b08e26fb718eb21f40`) and contains six stored M3 associations. It supports deliberate shared-memory reuse after compilation and installation; it does not implement autonomous inter-robot exchange.

### Legacy A–C figure scripts

The scripts under `analysis/figures/` reproduce visualizations from the development-stage A–C evidence. They are retained for transparency and reproducibility of that historical evidence stream and are **not** the production figure set of the published article.

```bash
cd analysis/figures
pip install matplotlib numpy scipy   # optional dependency setup, only if not already installed
python3 Fig8.py
python3 Fig9.py
python3 Fig10.py
python3 Fig11.py
```

---

## 7. Publication and source-code boundary

The repository publishes raw A–C and Session E evidence, unified indexes, public-safe supporting analyses, the controlled replay package, and one production SAS source module:

```text
data/session_e/public_code/sas_text.py
```

The remaining SAS production modules are protected and deliberately outside the public release. The complete source remains available to the editor and reviewers in confidence, upon request through the journal.

Raw evidence is preserved for provenance and may contain original Romanian-language instructions or session notes and deployment-local identifiers. These records are not rewritten in place. For the publication policy, frozen-record handling, provenance model, language policy, and declared boundary decisions, see [`docs/PUBLICATION_SCOPE.md`](docs/PUBLICATION_SCOPE.md).

---

## 8. Repository map

```text
nav2-sas-vlm-memory/
├── config/                              # Historical A–C configuration
│
├── data/
│   ├── session_a/                       # Development-stage Session A evidence
│   ├── session_b/                       # Development-stage Session B evidence
│   ├── session_c/                       # Development-stage Session C evidence
│   ├── memory/                          # Historical memory snapshots + verified regeneration
│   │
│   ├── session_e/                       # Frozen v4.8-review confirmatory campaign
│   │   ├── day1_20260820/
│   │   ├── day2_20260821/
│   │   ├── external_reference/
│   │   ├── notes/
│   │   ├── public_code/                 # Public SAS source boundary
│   │   ├── missions.csv
│   │   ├── sessions.csv
│   │   ├── PROVENANCE.tsv
│   │   ├── PROVENANCE_PUBLIC.tsv
│   │   ├── CHECKSUMS_PUBLIC.md5
│   │   ├── SOURCE.md
│   │   ├── KNOWN_DISCREPANCIES.md
│   │   └── README.md
│   │
│   ├── sessions_index.csv
│   ├── missions_index.csv
│   ├── session_register.json
│   └── SESSIONS.md
│
├── analysis/
│   ├── figures/                          # Legacy A–C development-stage scripts
│   └── session_e/
│       ├── core/                         # Canonical Session E core analysis
│       ├── A1_cascade/
│       ├── A2_m3_sensitivity/
│       ├── A3_m3_promotion/
│       ├── r210_model_replay/
│       ├── rc1_2_reanalysis/             # rc1.2: E7 classes, navigation denominators
│       ├── semantic_comparison/          # rc1.2: controlled offline comparison
│       ├── m3_boundary/                  # rc1.2: matcher decision-boundary challenge
│       ├── guard_branch/                 # rc1.2: forbidden-node guard branch test
│       ├── e7_adjudication/              # rc1.2: independent E7 adjudication
│       ├── apriltag_summary/             # rc1.2: AprilTag descriptive summary
│       └── camera_transaction/           # rc1.2: image-request transaction, Xplorer-B
│
├── docs/
│   ├── PUBLICATION_SCOPE.md
│   ├── REPRODUCIBILITY_NOTES.md
│   ├── RC1_2_SCOPE_NOTES.md
│   ├── AC_EVIDENCE_NOTES.md
│   ├── session_e_l3b_population_dictionary.md
│   ├── ac_inclusion_funnel.csv
│   ├── ac_startup_digest_map.csv
│   ├── publication_exceptions.json
│   └── link_resolution_map.json
│
├── tools/
│   ├── build_dataset.py
│   ├── reproduce_digest.py
│   └── rerun_sealed.py
│
├── README.md
├── CHANGELOG.md
├── CITATION.cff
├── LICENSE
└── .gitignore
```

---

## 9. Integrity and provenance

For Session E:

- `data/session_e/CHECKSUMS_PUBLIC.md5` verifies the published package;
- `data/session_e/PROVENANCE.tsv` preserves the delivered provenance record;
- `data/session_e/PROVENANCE_PUBLIC.tsv` records public-reference material added after delivery;
- `data/session_e/KNOWN_DISCREPANCIES.md` documents the declared post-delivery metadata discrepancy.

Frozen analytical packages under `analysis/session_e/` retain their own checksum manifests. Digest-bound historical wording exceptions and link resolutions are recorded in `docs/publication_exceptions.json` and `docs/link_resolution_map.json`.

The analyses added in rc1.2 each carry `CHECKSUMS_SHA256.txt`. Their `sealed/` subdirectories hold the sealed or frozen files byte-identical, so that the seals can be verified. Run evidence that contained runtime environment data is published as separately identified redacted copies, which record the SHA-256 of the original. The RC1.1 datasets and frozen analysis artifacts are unchanged; release-level documentation is updated as recorded in [`CHANGELOG.md`](CHANGELOG.md).

---

## 10. Citation

Published article (open access, CC BY 4.0):

> B. F. Abaza, A.-A. Staicu, and C. V. Doicin, “A Semantic Autonomy Framework for VLM-Integrated Indoor Mobile Robots: Hybrid Deterministic Reasoning and Cross-Robot Adaptive Memory,” *Robotics and Autonomous Systems*, vol. 207, Art. no. 105822, 2027. [DOI: 10.1016/j.robot.2026.105822](https://doi.org/10.1016/j.robot.2026.105822)

```bibtex
@article{abaza2026sas,
  title         = {A Semantic Autonomy Framework for {VLM}-Integrated Indoor
                   Mobile Robots: Hybrid Deterministic Reasoning and
                   Cross-Robot Adaptive Memory},
  author        = {Abaza, Bogdan Felician and Staicu, Andrei-Alexandru
                   and Doicin, Cristian Vasile},
  journal       = {Robotics and Autonomous Systems},
  volume        = {207},
  pages         = {105822},
  year          = {2027},
  doi           = {10.1016/j.robot.2026.105822},
  eprint        = {2605.02525},
  archivePrefix = {arXiv},
  primaryClass  = {cs.RO},
}
```

The published version is also available on arXiv as [arXiv:2605.02525](https://arxiv.org/abs/2605.02525) (v2). The repository citation metadata is provided in [`CITATION.cff`](CITATION.cff).

---

## 11. Related publication

**Inherited L1–L2 foundation:**  
B. F. Abaza, A.-A. Staicu, and C. V. Doicin, “Lightweight Semantic-Aware Route Planning on Edge Hardware for Indoor Mobile Robots: Monocular Camera–2D LiDAR Fusion with Penalty-Weighted Nav2 Route Server Replanning,” *Sensors*, 26(7), 2232, 2026. [DOI: 10.3390/s26072232](https://doi.org/10.3390/s26072232)

Companion repository: [nav2-semantic-route-server](https://github.com/bogdan-abaza/nav2-semantic-route-server)

---

## 12. Authors, contributions, and affiliation

The contributions below summarize work on the SAS research and its accompanying public evidence and reproducibility package.

- **Bogdan Felician Abaza** — conceptualization, methodology, software (SAS framework, software implementation, and system integration), formal analysis, investigation, resources, data curation, writing – original draft, writing – review & editing, validation, visualization, supervision, and project administration.
- **Andrei-Alexandru Staicu** — software (software implementation, system integration, and VLM integration), investigation, data curation, writing – review & editing, validation, and visualization.
- **Cristian Vasile Doicin** — resources, funding acquisition, formal analysis, writing – review & editing, validation, visualization, and supervision.

Faculty of Industrial Engineering and Robotics (FIIR)  
National University of Science and Technology POLITEHNICA Bucharest

Correspondence: [bogdan.abaza@upb.ro](mailto:bogdan.abaza@upb.ro)

---

## 13. License

This repository is released under the [MIT License](LICENSE).
