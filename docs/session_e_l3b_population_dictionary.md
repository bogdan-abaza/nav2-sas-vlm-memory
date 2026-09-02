# Session E — VLM/L3b population dictionary

Five nested populations describe the VLM path of Session E. They are never interchangeable,
and every published VLM-path figure names the one it uses. All five values below are derived
programmatically: the outcome split from `analysis/session_e/core/results_E.json`
(`points.R1-4`, `by_method`), the timed count from `vlm_ms` in `data/session_e/missions.csv`.

| Population | n | Definition |
|---|---|---|
| VLM call-path attempts | **105** | every decision cycle that left the deterministic path (69 + 22 + 14) |
| Timed VLM records | **91** | attempts with a recorded, non-zero VLM inference time (`vlm_ms` > 0) |
| Accepted-node / image-complete L3b records | **69** | the VLM returned a node that was accepted, with complete imagery |
| Clarification outcomes | **22** | the VLM returned `vlm_proposed_node = -1`, requesting clarification — the intended behaviour under negation |
| Error / parse outcomes | **14** | the call returned no parseable contract JSON |

The archived-population composition is 226 = 121 deterministic-path + 105 VLM-path
decision cycles; the primary E0-excluded composition is 216 = 112 + 104. Latency figures for
the VLM path use the timed population (91); acceptance and outcome rates use the
populations named in their captions.
