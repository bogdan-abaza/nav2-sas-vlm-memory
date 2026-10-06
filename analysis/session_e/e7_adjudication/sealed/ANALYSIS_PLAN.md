# C3 — prespecified analysis plan (blind adjudication of the 28 sealed E7 cells)

Status: post-hoc sensitivity analysis. The sealed E7 result (17/28) remains the primary historical result and is never replaced. Fixed before any response is received; implemented in `c3_analysis.py` and sealed with the packet (`c3_seal.py`).

Evaluator input: `packets_blind/E7_adjudication_packet_v1` only (28 English v2 requests in random order under neutral codes Q01–Q28; route graph; static objects; map). Not given: sealed acceptable/wrong sets, referent_real, original_ro, v1 wording, provenance, category, level, cell ids, system choices, outcomes, score, dynamic (YOLO) objects. Labels are given exactly as served on day 2, including node 14 named `plant_5` while hosting `window_north` (`plant_5` attached to node 15). The evaluator instructions do not point to it ("labels are reproduced exactly from the historical configuration"); the analysis reports its possible effect when interpreting W-P2 and the plant/window cells.

Evaluators: one evaluator, independent of construction and execution of the original E7 key, evaluates all 28 cells. If a second evaluator is used in the formal sensitivity analysis, that evaluator independently evaluates the same complete 28-cell set. Any informal opinion on individual ambiguous cells is not part of this analysis and is not called a second evaluator.

Independence declaration: each evaluator completes `evaluator.txt` (name, affiliation/role, date, and a confirmation that, before completing the task, they were not shown the original acceptable-node key or destination annotations, the robot's selections or outcomes, or any score, and judged independently). It is returned with the form and kept with it in `returned/<evaluator>/`; `c3_analysis.py` refuses a form without a completed, confirmed declaration, a form whose request texts differ from the packet, or a missing/invalid confidence.

Per evaluator: (1) form validation; (2) verdict agreement with the sealed key (node set vs no-node); (3) set relation and Jaccard where both give nodes; (4) rescoring of the scored SAS decision (first observation per cell) under the evaluator key, with the corrected rule (no-node correct only on an explicit clarification request; parse failure never correct; sealed-key rescoring must reproduce 17/28); (5) cells whose correctness changes; (6) SAS choices marked clearly wrong. Two or more evaluators: pairwise agreement; strict (intersection) and lenient (union) keys.

Reporting: counts per cell and in total; no significance tests; disagreements listed by cell. Interpretation in prose follows these counts; the sealed key is not revised.

Language: the evaluator packet is administered in English. The 28 E7 requests are reproduced verbatim from the executed v2 set and are not translated or paraphrased. The evaluator must be able to follow the English procedural instructions without difficulty.

After sealing: nothing in the packet, the code map, this plan or `c3_analysis.py` is modified. Any real problem found later is handled by an explicit, dated amendment recorded next to the sealed set, never by silent regeneration.
