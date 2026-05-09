# A Semantic Autonomy Framework for VLM-Integrated Indoor Mobile Robots

**Hybrid Deterministic Reasoning and Cross-Robot Adaptive Memory**

[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Nav2](https://img.shields.io/badge/Nav2-1.3.x-green)](https://docs.nav2.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2605.02525-b31b1b.svg)](https://arxiv.org/abs/2605.02525)

This repository contains experimental data, and analysis scripts accompanying the manuscript:

> **B. F. Abaza, A.-A. Staicu, and C. V. Doicin**, "A Semantic Autonomy Framework for VLM-Integrated Indoor Mobile Robots: Hybrid Deterministic Reasoning and Cross-Robot Adaptive Memory," 2026. [arXiv:2605.02525](https://arxiv.org/abs/2605.02525).

**Companion repository:** The perception and route planning layers (L1–L2) are available at [nav2-semantic-route-server](https://github.com/bogdan-abaza/nav2-semantic-route-server), accompanying the published Sensors paper ([DOI: 10.3390/s26072232](https://doi.org/10.3390/s26072232)).

---

## System Overview

This repository implements **Layers L3–L5** of the Semantic Autonomy Stack (SAS), a six-layer reference framework for semantically autonomous indoor navigation:

- **L3 — Semantic Reasoning:** A hybrid dual-process architecture where a seven-step parametric resolver (L3a) handles 88% of natural language instructions deterministically in under 0.1 ms, with automatic escalation to Vision-Language Model reasoning (L3b, Qwen 3.5:4b via Ollama) for ambiguous cases.
- **L5 — Operational Intelligence:** A five-category semantic memory framework (M1–M5) with explicit scope taxonomy (global environment knowledge, per-operator preferences, per-robot capabilities) enabling cross-session learning and cross-robot knowledge transfer.
- **Executive Contract ⟨A, O, V, L⟩:** A formalized interface between the VLM and the robot's navigation capabilities, providing model agnosticism, safety validation, and complete audit logging.

### Key Results

| Metric | Value |
|---|---|
| L3a fast-path rate | 88% of all decisions |
| M3 preference resolve time | 0.065 ms (mean) |
| VLM inference time (L3b) | 6,733 ms (mean) |
| Latency reduction (L3b → L3a) | 103,000× |
| Cross-robot transfer accuracy | 33/33 = 100% (95% CI [0.894, 1.000]) |
| Semantic resolution accuracy | 100% (41/41 on transfer robot) |
| Physical validation | 82 decisions, 2 robots, 3 sessions |
| Training required | None |

---

## Repository Structure

```
nav2-sas-vlm-memory/
├── config/                               # Configuration files
│   ├── semantic_objects_static.geojson    #   18 static POIs (8 classes, surveyed)
│   ├── policy.yaml                       #   Safety policy (action allowlist, limits)
│   └── SOUL.md                          #   OpenClaw operator agent profile
├── data/                                 # Experimental dataset
│   ├── session_a/                        #   Session A: Xplorer-C, learning cycle
│   │   ├── audits/                       #     Structured JSONL audit logs (10 files)
│   │   ├── csv_clean/                    #     Post-v4.8 session monitor CSVs
│   │   ├── csv_debug/                    #     Pre-v4.8 data (transparency)
│   │   └── mission_folders/              #     Per-mission images + VLM prompts/responses
│   ├── session_b/                        #   Session B: Xplorer-B, cross-robot transfer
│   │   ├── audits/                       #     3 audit log files
│   │   ├── csv/                          #     Session monitor CSVs
│   │   └── mission_folders/              #     Per-mission images + VLM data
│   ├── session_c/                        #   Session C: concurrent operation (both robots)
│   │   ├── audits/                       #     4 audit logs (1 per robot per pair)
│   │   └── mission_folders/              #     Per-mission images
│   └── memory/                           #   Memory files used in experiments
│       ├── memory_digest.json            #     Compiled digest (MD5: 97241265)
│       ├── M1_environment.jsonl          #     Entity visit statistics
│       ├── M2_temporal_patterns.jsonl    #     Scene observation clusters
│       ├── M3_operator_preferences.jsonl #     Promoted instruction→node mappings
│       ├── M4_xplorer-b.jsonl            #     Platform capabilities (Xplorer-B)
│       ├── M4_xplorer-c.jsonl            #     Platform capabilities (Xplorer-C)
│       └── M5_task_history.jsonl         #     Per-decision summaries
├── analysis/                             # Reproducibility
│   └── figures/                          #   Python scripts for paper figures
│       ├── data_loader.py                #     Read experimental data from `data/session_*/audits/*.jsonl`
│       ├── Fig8.py                       #     Learning cycle VLM times (bar chart)
│       ├── Fig9.py                       #     Resolve times by category (box plot)
│       ├── Fig10.py                      #     L3b vs L3a speedup (log-scale)
│       └── Fig11.py                      #     Navigation outcomes (stacked bar)
├── README.md
├── LICENSE                               # MIT
└── CITATION.cff
```

---

## Reproducing Paper Figures

All figure scripts read experimental data from `data/session_*/audits/*.jsonl` via the shared `data_loader.py` module. To reproduce:

```bash
cd analysis/figures
pip install matplotlib numpy scipy
python3 Fig8.py   # Learning cycle VLM times (bar chart)
python3 Fig9.py   # Resolve times by category (box plot)
python3 Fig10.py  # L3b vs L3a speedup (log-scale)
python3 Fig11.py  #  Navigation outcomes (stacked bar)
```

Each script produces PDF, TIFF, EPS, and PNG outputs at 600 DPI (publication-ready).

---

## Experimental Data

The `data/` directory contains all experimental data from the three-session validation:

| Session | Robot | Decisions | Purpose |
|---|---|---|---|
| A | Xplorer-C | 37 | M3 preference confirmation + S3new learning cycle |
| B | Xplorer-B | 41 | Cross-robot memory transfer validation |
| C | Both | 4 | Concurrent operation feasibility |
| **Total** | | **82** | |

### Audit log format

Each decision is logged as a JSONL entry containing: timestamp, instruction, resolution method (L3a_m3_preference / L3a_deterministic / L3b_vlm), target node, timing breakdown (resolve_ms, vlm_ms, nav_total_s), navigation outcome, confirmation data, images, and platform-specific metrics. The complete audit entry schema is described in Section 4.5 of the paper.

### Memory digest

The compiled digest used for Sessions B and C (`data/memory/memory_digest.json`, MD5: `97241265`) contains 6 M3 preferences promoted from VLM interactions. This is the artifact that enables cross-robot transfer without retraining.

---
## Source Code

The navigator, executive contract, and memory extractor source code 
is available from the corresponding author upon reasonable request.
## Citation

```bibtex
@article{abaza2026sas,
  title     = {A Semantic Autonomy Framework for {VLM}-Integrated Indoor
               Mobile Robots: Hybrid Deterministic Reasoning and
               Cross-Robot Adaptive Memory},
  author    = {Abaza, Bogdan Felician and Staicu, Andrei-Alexandru
               and Doicin, Cristian Vasile},
  year      = {2026},
  eprint    = {2605.02525},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO},
  note      = {Preprint},
```

---

## Related Publications

- **Sensors 2026 (L1–L2):** B. F. Abaza, A.-A. Staicu, and C. V. Doicin, "[Lightweight Semantic-Aware Route Planning on Edge Hardware for Indoor Mobile Robots](https://doi.org/10.3390/s26072232)," *Sensors*, 26(7), 2232, 2026. Repository: [nav2-semantic-route-server](https://github.com/bogdan-abaza/nav2-semantic-route-server)

---

## Authors

- **Bogdan Felician Abaza** — system architecture, SAS framework, semantic memory design, experimental framework, manuscript ([bogdan.abaza@upb.ro](mailto:bogdan.abaza@upb.ro))
- **Andrei-Alexandru Staicu** — VLM navigator, context bridge, executive contract, YOLO integration, data collection
- **Cristian Vasile Doicin** — validation, formal analysis, resources, funding, writing–review

Faculty of Industrial Engineering and Robotics (FIIR), National University of Science and Technology POLITEHNICA Bucharest

---

## License

This project is released under the [MIT License](LICENSE).
