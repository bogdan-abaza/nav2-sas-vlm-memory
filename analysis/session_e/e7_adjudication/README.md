# Independent adjudication of the sealed E7 destinations

**Status:** sealed before dispatch (4 October 2026, `sealed/internal/C3_SEAL.json`); response received and analysed 5 October 2026. **Reproducibility:** re-executable from this release (`python3 tools/rerun_sealed.py e7_adjudication`).

## Purpose
This is a post-hoc sensitivity check of the 28 sealed E7 acceptable-destination sets. The sealed E7 result, 17/28, remains the primary result. Neither the sealed key nor the evaluator's answers are revised.

## Procedure
One evaluator, Andy Dumitrescu (master's student, Faculty of Industrial Engineering and Robotics, National University of Science and Technology POLITEHNICA Bucharest, the authors' faculty), was not involved in constructing or executing E7 or Session E. He received only the blind packet `sealed/packets_blind/E7_adjudication_packet_v1.zip`: the 28 requests verbatim, in random order, under neutral codes Q01–Q28; the route graph; the static objects; and a map. He was not given the sealed key, the robot's choices, outcomes or scores. For each request he listed the acceptable nodes, or stated that no node is appropriate (the robot should ask for clarification). He also gave a confidence rating and could flag clearly wrong nodes. His completed independence declaration is `sealed/returned/dumitrescu/original_received/evaluator.txt`. The analysis plan and script were fixed and sealed with the packet (`sealed/ANALYSIS_PLAN.md`, `sealed/c3_analysis.py`).

The form was returned in Windows-1252 encoding. The analysis reads a UTF-8 transcription (`sealed/returned/dumitrescu/response_form.csv`). The original bytes are kept (`sealed/returned/dumitrescu/original_received/`), and no answer was changed (`sealed/C3_AMENDMENT_01_20261005.md`).

## Results (`sealed/analysis/`)
- The evaluator agreed with the sealed verdict (a destination versus clarification) in 26/28 cells.
- In the 25 cells where both give nodes, the sets are identical in 14, the evaluator's set is a subset of the sealed set in 5, a superset in 2, and they partially overlap in 4. Mean Jaccard is 0.81.
- Rescoring the scored system decision (the first observation per cell) under the evaluator's judgments gives **16/28** instead of 17/28. Two cells changed because the evaluator excluded CB204, which serves as both a laboratory and an office. One changed because the evaluator accepted the north-window node.

## Files
- `sealed/`: analysis plan, packet builder and seal scripts, analysis script, internal build record and code map, the blind packet (zip and unpacked), the returned form (original bytes and transcription), the encoding note and the analysis outputs, byte-identical to the sealed and frozen set. They keep the working labels and paths of the environment in which they were sealed.

## Verify and re-run
```bash
cd analysis/session_e/e7_adjudication && sha256sum -c CHECKSUMS_SHA256.txt && cd -
python3 tools/rerun_sealed.py e7_adjudication
```
