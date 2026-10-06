"""Render gates/*.md from gates/*.json (so reports never drift from results).  python3 -B gate_reports.py"""
import json, os
G = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gates') + os.sep
b = json.load(open(G + 'GATE_1B_negation.json')); a = json.load(open(G + 'GATE_1A_S_projection.json')); g = json.load(open(G + 'GATE_1_prompt_constructor.json'))
neg = [c for c in b['cases'] if c['frozen']]
open(G + 'GATE_1B_negation.md', 'w').write(f"""# GATE 1B — provenance validation of the common frozen negation envelope: **{b['verdict']}**
Generated {b['generated_utc']} by `harness/a4_bundle.py` (no model calls).

The negation envelope (`negation_markers`, `intent`, `forbidden_nodes`, rendered notice + sha256) is frozen in each bundle before arm
execution and is identical in arms A, B and C; the arms neither rebuild it nor run M3 to derive it. `forbidden_nodes` is the parent audit
`negation_forbidden_nodes`. Recomputation by the frozen `negation_guard` under the historical digest, in the S context, reproduces it:
**{b['n_pass']}/{b['n']}** ({len(neg)} items with negation; all others empty, as expected).

Finding: for N01, N03, N07, N08 the forbidden set {{0, 4}} is identified through M3 (the stripped instruction is resolved at Step 0);
recomputed with `m3_index = None` it is empty. Hence the envelope is frozen pre-run; M3 is used only in this provenance check, never inside arms B or C.
""")
open(G + 'GATE_1A_S_projection.md', 'w').write(f"""# GATE 1A — S projection: **{a['verdict']}**
Generated {a['generated_utc']} by `harness/a4_bundle.py` (no model calls).

For the {a['n']} A4 items with a same-cycle historical prompt, the S prompt built by the frozen builder with an empty dynamic store equals the
canonical projection of the historical prompt (YOLO object lines, `currently detected` marks and zones left empty removed; the rest unchanged):
**{a['n_pass']}/{a['n']}**. Extended over all 105 historical prompts: **{a['extended_pass']}/{a['extended_n']}**.
The remaining {38 - a['n']} S items have no historical prompt: contract-only (provenance of inputs), as declared in the protocol.
""")
bm = g['by_method']
open(G + 'GATE_1_prompt_constructor.md', 'w').write(f"""# GATE 1 — prompt constructor fidelity: **{g['verdict']}**
Generated {g['generated_utc']} by `harness/a4_bundle.py` (no model calls).

- Records with `extra.vlm_prompt_full` in RC1.1: **{g['n']}**, rebuilt byte-identical: **{g['n_pass']}/{g['n']}**
  (L3b_vlm {bm['L3b_vlm'][0]}/{bm['L3b_vlm'][1]}, L3b_vlm_negation_blocked {bm['L3b_vlm_negation_blocked'][0]}/{bm['L3b_vlm_negation_blocked'][1]}, escalated {bm['escalated'][0]}/{bm['escalated'][1]}).
- Two historical copies for L3b_vlm, `audit.vlm_prompt_full == logs/<run>/<mission>/vlm_decision_prompt.txt`: **{g['copy_pass']}/{g['copy_n']}**.

Independent frozen inputs: route graph and static objects (RC1 config), memory prefix (frozen `build_memory_prefix` on the digest identified by
content_md5), negation notice (frozen `build_negation_notice` on the audit markers and historical forbidden nodes), frozen `build_vlm_prompt`.
Replayed from the same-cycle prompt (declared): the YOLO entries (class, id, confidence, node, printed distance) and the `currently detected`
marks, because the dynamic store was not archived per cycle; and the decision-time context pose, printed rounded to 0.01 m. The constructor uses a
prompt-equivalent decision-time pose chosen within the 0.01-m rounding cell so that every printed static distance is reproduced (many feasible
points per record; all give identical output; not a unique reconstruction of the AMCL state).
Finding: the context pose differs from `extra.start_pose` in some records, and 2 prompts (E4, E6; not A4 items) carry pose 0, 0, 0.

Scope: 105/105 is not an independent reconstruction of YOLO geometry; H is a prompt-context replay for the dynamic component.
""")
print('gate reports rendered')
