# M3 Decision-Boundary Challenge — construction rule (FROZEN)

Frozen 2026-10-05, approved by B. Abaza (draft `0dd69985…` + author's precisions of 08:48 local), before any item score was computed.
Scope: diagnostic set built deliberately near the decision boundary; reported separately from A4-primary; never pooled.
**Reporting sentence (fixed):** *diagnostic set constructed with access to similarity scores; labels assigned before each candidate was scored and reviewed on sheets without scores or decisions.* No claim of a fully blind construction.

## 1. Frozen matcher and inputs (public, RC1.1)
- Reimplementation: `analysis/session_e/A2_m3_sensitivity/analyze_A2_m3_sensitivity.py` (`build_index`, `rank_instruction`, `classify`) and `inputs/sas_text.py` (sha256 aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1). Read-only from the RC1.1 local copy; hashes checked at every invocation.
- Historical index H = `inputs/memory_digest_standard.json` (sha256 1fe64ed09a96343bac5abd0cae476545bd0100dd496dc25122b1ca4a2cd7c3ab): 6 stored examples, 5 nodes (14, 0, 4, 8, 0, 9).
- Feasibility finding (synthetic token sets, not items, 2026-10-05): on H no token set reaches ≥ 0.75 to one node while scoring > 0.40 to another node (best: 0.80 to node 9 with 0.40 to node 14), so the 0.10 margin is never active on H. Family F3 is therefore scored on H + C (§3).

## 2. Matchers compared
- **EXACT** (primary baseline): `detect_negation` → abstain; else accept the node of the stored example whose `normalize()` equals `normalize(instruction)`; otherwise abstain.
- **JACCARD 0.75 / 0.10** (operational): `classify(rank_instruction(...), 0.75, 0.10)`, unchanged, with the implementation's own floating-point arithmetic. Any effect of numerical representation at the exact boundaries (e.g. a gap of exactly 1/10 computed below 0.10) is reported, not corrected.
- JACCARD 0.60 / 0.10: optional historical reference, separate column.
Outcomes per item: correct accept, wrong accept, abstention; for items labelled `abstain`: correct abstention vs wrong accept.

## 3. Families (48 = 16 + 16 + 16)
| Family | Index | Content | Bands |
|---|---|---|---|
| F1 valid paraphrases of a stored association | H | same intent as a stored example, reworded | 3 at J = 1 · 4 in (3/4, 1) · 3 at J = 3/4 · 6 in [1/2, 3/4) |
| F2 high overlap, different meaning | H | shares most content words with a stored example but means something else | 3 at J = 1 · 4 in (3/4, 1) · 3 at J = 3/4 · 6 in [1/2, 3/4) |
| F3 near-tied associations | H + C | close to two stored associations of different nodes | top ≥ 3/4 in all; gap: 6 with gap < 1/10 · 4 with gap = 1/10 · 6 with gap in (1/10, 1/4] |
- **Bands from exact fractions.** Scores for band assignment are computed as exact fractions |T∩E| / |T∪E| (`fractions.Fraction`) on the frozen `tokenize` output; numerator and denominator are kept for every candidate. F3: top and runner-up are computed **globally over distinct nodes on the whole H + C** (per-node maximum over examples, as in `rank_instruction`), not only within the intended pair; gap = top − runner-up as a fraction.
- **Challenge index C:** 8 synthetic association pairs (16 stored examples), each pair two examples mapping to two different real graph nodes, written in the style of H, declared synthetic. **C is written and hashed before any F3 candidate is scored** and is sealed with the set. Two F3 items per pair (target). F1/F2 are scored on H alone.
- **Identity exclusion:** in F1/F2 a candidate with `normalize(candidate) == normalize(stored example)` is excluded (punctuation or case removed by normalisation is not a rewording). J = 1 items must differ from every stored example after `normalize()`.
- **No negation:** no item may express negation in meaning, and none may trigger `detect_negation` of the frozen implementation (checked per candidate, logged).
- **Spread:** F1 and F2 at most 4 items per stored example of H; every example of H used at least once in F1 ∪ F2.
- **Natural wording:** no unnatural phrasing is forced to fill a band. A band that cannot be filled with natural candidates is declared short; bands are never redefined after scoring.

## 4. Labels (semantic, written with the candidate)
- Each candidate is written together with its label, before its score exists: `node:<id>` (the graph node the instruction means; may differ from the related stored example) or `abstain` (meaning genuinely ambiguous between nodes, or not served by the stored associations).
- F3 labels follow semantic ambiguity, not score proximity: an F3 item is labelled `abstain` only if its meaning is ambiguous between the two nodes, also above the margin; otherwise it is labelled with the node it means.
- Each authoring batch is hashed before the scorer reads it. A candidate reworded after scoring gets a new id and a newly written label; the old candidate stays in the log. The author of a rewording may know the earlier candidate's score; this is declared (reporting sentence above).
- Author review (B. Abaza) on a sheet with id, instruction, label and related stored association only — no scores, no bands, no decisions. Approval dated; label changes in review logged.

## 5. Selection
- Candidates are assigned to the band their exact fraction falls in; bands are filled in authorship order; surplus candidates remain in `candidates_log.csv` with band and fractions, unused.
- Never consulted for selection: EXACT or JACCARD decisions, agreement with labels.
- Shortfalls declared.

## 6. Seal, then run
Sealed set: this rule, `challenge_index_C.json`, all authoring batches with their hashes, `candidates_log.csv`, `items.csv` (id, family, instruction, label, related stored example(s), index used, band, fractions), the score-free review sheet with approval, `c5_run.py`, hashes of the RC1.1 inputs. Only after the seal: `c5_run.py`. No item added, removed or relabelled after the run; corrections only as dated amendments next to the sealed set.

## 7. Graph nodes (for labels), from RC1.1 `route_graph_fiir.geojson` / `semantic_objects_static_v2.geojson`
0 toilet_m (restroom_men) · 1 hall_entry (emergency_exit) · 2 hall_exit (emergency_exit) · 4 toilet_f (restroom_women) · 5 cb204 (lab_cb204) · 8 cb202 (lab_cb202, fire_extinguisher_cb202) · 9 radiator (radiator_main) · 13 plant_4 · 14 plant_5 (window_north) · 15 junction_e1 (plant_5 re-anchored, lab_chair) · 19 plant_3 · 20 plant_2 (window_south) · 21 plant_1 · 22 cb203_entrance · 23 cb203_exit; junctions 3, 6, 7, 10–12, 16–18 carry no POI.
