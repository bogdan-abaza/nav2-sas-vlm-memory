# Scope notes for ras-revision-rc1.2

The datasets and frozen analysis artifacts inherited from `ras-revision-rc1.1` are kept byte-identical, including passages whose wording this release qualifies. Release-level documentation is updated as recorded in `CHANGELOG.md`. These notes state the qualifications. They do not change any frozen artifact.

## 1. E0 and the M1 confirmation statistic

Primary Session E performance rates exclude E0, whereas the descriptive M1 positive-confirmation prevalence includes the E0 start-gate checks and is reported over all attempted confirmation checks.

Accordingly, the reported M1 confirmation statistic is 153/165 over all attempted confirmation checks, including E0; the E0-excluded value is 146/156 and is not used as the primary descriptive confirmation statistic.

Frozen files that carry the earlier, broader wording about E0:

| File | Location |
|---|---|
| `analysis/session_e/core/BLOCKS.md` | line 33 |
| `analysis/session_e/core/RESULTS_E.md` | line 134 |
| `analysis/session_e/core/analyze_session_e.py` | lines 44, 327, 1516–1521 |

There, "excluded from all rates" refers to the primary performance rates.

## 2. Sealed subset E7: cells, decision cycles and outcome classes

E7 has 28 sealed cells and 29 archived decision cycles. Cell H-P4 produced two decision cycles within the same run: the first ended `missed`, the second `mission_complete`, both at node 9. The cell was not executed twice. E7 scoring uses the first observation per sealed cell.

Frozen files that carry the earlier wording: `analysis/session_e/core/RESULTS_E.md` line 1116 and `analysis/session_e/core/analyze_session_e.py` line 690.

In `analysis/session_e/core/results_E.json`, the field `abstained` is derived as `nid is None` (`analyze_session_e.py` line 657). It is `true` for three E7 cells (H-P3, P-P4 and S-P2), which are model-response parse failures, not clarification requests. The outcome classes are reported separately in `analysis/session_e/rc1_2_reanalysis/`:
- 17 acceptable selections;
- 6 incorrect executable decisions;
- 2 executable decisions where clarification was required (G-3 and H-P2; frozen class `executable_where_abstention_expected`);
- 3 parse failures;
- 0 clarification requests.

The count of 17/28 is unchanged.

## 3. Navigation denominators

The terminal navigation miss is reported over two denominators, both in `analysis/session_e/rc1_2_reanalysis/`:
- all 199 protocol-valid runs: 1/199;
- the 164 runs that dispatched at least one navigation goal: 1/164.

The terminal outcome distribution of the 199 runs is 162 `mission_complete`, 1 `missed`, 22 `clarification_requested` and 14 `vlm_failed`. A separate measure is non-arrival among dispatched runs: 2/164. It includes the terminal `missed` run on Xplorer-C and a run on Xplorer-B that dispatched navigation, recorded a miss, and then ended `vlm_failed`. These three measures answer different questions and do not establish end-to-end semantic task success.

## 4. Sealed working labels

The `sealed/` subdirectories of the new analyses contain the exact files that were sealed or frozen. They are kept byte-identical so that their seals and analysis commands can be verified. They therefore retain the working labels and directory paths used when they were sealed. `tools/rerun_sealed.py` provides the expected layout without modifying them.
