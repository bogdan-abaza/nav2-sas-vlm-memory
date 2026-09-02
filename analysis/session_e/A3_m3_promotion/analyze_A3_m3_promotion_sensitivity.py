#!/usr/bin/env python3
"""A3 — M3 promotion frequency/consistency sensitivity for frozen Session E.

Public-safe standalone analysis for ROBOT-D-26-01090 major revision.

The script intentionally does NOT import or require the production memory
extractor or any protected SAS runtime module. It reconstructs only the
published M3 promotion rule from released Session E audit records, using the
released sas_text.py v1.2.0 for the canonical instruction clustering key.

Primary controlled induction populations:
  E4.1  : data/session_e/day2_20260821/memory/logs_E41_only/*.jsonl
  E4b.1 : data/session_e/day2_20260821/memory/logs_E4b1_only/*.jsonl

Frozen rule reproduced before sensitivity analysis:
  frequency >= 3
  AND consistency >= 0.80
  AND at least one L3b_vlm resolution
where consistency = round(dominant_count / total, 2) BEFORE comparison.

Outputs are written to --out-dir.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from sas_text import SAS_TEXT_VERSION, cluster_key

ANALYSIS_ID = "A3_m3_promotion_sensitivity_v1"
STATUS = "FROZEN 2026-08-25"
NOMINAL_MIN_FREQUENCY = 3
NOMINAL_CONSISTENCY = 0.80
FREQUENCY_GRID = list(range(1, 7))
CONSISTENCY_GRID = [i / 100 for i in range(0, 101)]

E41_PREFIX = "data/session_e/day2_20260821/memory/logs_E41_only/"
E4B1_PREFIX = "data/session_e/day2_20260821/memory/logs_E4b1_only/"
E4_ARCHIVED_M3 = "data/session_e/day2_20260821/memory/digest_E4.2/M3_operator_preferences.jsonl"
E4B_ARCHIVED_M3 = "data/session_e/day2_20260821/memory/digest_E4b/M3_operator_preferences.jsonl"
E4_DIGEST = "data/session_e/day2_20260821/memory/digest_E4.2/memory_digest.json"
E4B_DIGEST = "data/session_e/day2_20260821/memory/digest_E4b/memory_digest.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonl_from_zip(z: zipfile.ZipFile, name: str) -> List[Dict[str, Any]]:
    out = []
    for line in z.read(name).decode("utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def audit_decisions_from_prefix(z: zipfile.ZipFile, prefix: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    names = sorted(n for n in z.namelist() if n.startswith(prefix) and n.endswith(".jsonl"))
    decisions: List[Dict[str, Any]] = []
    for name in names:
        for e in jsonl_from_zip(z, name):
            if e.get("_type") == "decision":
                x = dict(e)
                x["_source_file"] = os.path.basename(name)
                decisions.append(x)
    return decisions, names


def instruction_key_tuple(text: str) -> Tuple[str, ...]:
    return tuple(sorted(cluster_key(text)))


def reconstruct_candidates(decisions: Iterable[Dict[str, Any]], source_block: str) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, ...], Dict[str, List[Any]]] = defaultdict(
        lambda: {"instructions": [], "nodes": [], "methods": [], "timestamps": [], "source_files": []}
    )
    for d in decisions:
        instr = d.get("instruction", "")
        key = instruction_key_tuple(instr)
        if not key:
            continue
        g = grouped[key]
        g["instructions"].append(instr)
        g["nodes"].append(d.get("node_id"))
        g["methods"].append(d.get("resolution_method"))
        g["timestamps"].append(d.get("timestamp"))
        g["source_files"].append(d.get("_source_file"))

    rows = []
    for key, data in grouped.items():
        node_counts = Counter(data["nodes"])
        method_counts = Counter(data["methods"])
        total = len(data["nodes"])
        dominant_node, dom_count = node_counts.most_common(1)[0]
        consistency_raw = dom_count / total
        consistency_rounded = round(consistency_raw, 2)
        ready = (
            total >= NOMINAL_MIN_FREQUENCY
            and consistency_rounded >= NOMINAL_CONSISTENCY
            and method_counts.get("L3b_vlm", 0) >= 1
        )
        rows.append({
            "source_block": source_block,
            "instruction_key": list(key),
            "instruction_key_str": "|".join(key),
            "instruction_examples": sorted(set(data["instructions"]))[:3],
            "resolved_node_id": dominant_node,
            "frequency": total,
            "dominant_count": dom_count,
            "consistency_raw": consistency_raw,
            "consistency_rounded": consistency_rounded,
            "node_counts": dict(node_counts),
            "method_distribution": dict(method_counts),
            "l3b_vlm_count": method_counts.get("L3b_vlm", 0),
            "node_outcomes": list(data["nodes"]),
            "methods": list(data["methods"]),
            "source_files": list(data["source_files"]),
            "ready_nominal_reconstructed": ready,
        })
    rows.sort(key=lambda r: (r["source_block"], -r["frequency"], r["instruction_key_str"]))
    return rows


def normalize_archived_pref(r: Dict[str, Any], source_block: str) -> Dict[str, Any]:
    return {
        "source_block": source_block,
        "instruction_key": sorted(r["instruction_key"]),
        "resolved_node_id": r.get("resolved_node_id"),
        "frequency": r.get("frequency"),
        "consistency": r.get("consistency"),
        "method_distribution": r.get("method_distribution", {}),
        "ready": bool(r.get("ready_for_l3a_promotion")),
    }


def candidate_compare_key(r: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    return r["source_block"], tuple(sorted(r["instruction_key"]))


def reproduction_gate(candidates: List[Dict[str, Any]], archived: List[Dict[str, Any]]) -> Dict[str, Any]:
    rec = {candidate_compare_key(r): r for r in candidates}
    arc = {candidate_compare_key(r): r for r in archived}
    mismatches = []
    if set(rec) != set(arc):
        mismatches.append({"type": "candidate_key_set", "reconstructed": sorted(map(str, rec)), "archived": sorted(map(str, arc))})
    for k in sorted(set(rec) & set(arc), key=str):
        a, b = rec[k], arc[k]
        checks = {
            "resolved_node_id": (a["resolved_node_id"], b["resolved_node_id"]),
            "frequency": (a["frequency"], b["frequency"]),
            "consistency": (a["consistency_rounded"], b["consistency"]),
            "method_distribution": (a["method_distribution"], b["method_distribution"]),
            "ready": (a["ready_nominal_reconstructed"], b["ready"]),
        }
        for field, (x, y) in checks.items():
            if x != y:
                mismatches.append({"candidate": str(k), "field": field, "reconstructed": x, "archived": y})
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "candidate_count_reconstructed": len(rec),
        "candidate_count_archived": len(arc),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def promoted(candidate: Dict[str, Any], min_frequency: int, consistency_threshold: float) -> bool:
    return (
        candidate["frequency"] >= min_frequency
        and candidate["consistency_rounded"] >= consistency_threshold
        and candidate["l3b_vlm_count"] >= 1
    )


def short_label(c: Dict[str, Any]) -> str:
    ex = c["instruction_examples"][0].lower()
    if "deliver" in ex:
        return "deliveries"
    if "quiet" in ex:
        return "quiet_corner"
    if "glove" in ex:
        return "wet_gloves"
    return c["instruction_key_str"]


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            x = {}
            for fld in fields:
                v = r.get(fld)
                if isinstance(v, (dict, list, tuple)):
                    v = json.dumps(v, ensure_ascii=False)
                x[fld] = v
            w.writerow(x)


def extract_v3_crosscheck(v3_zip: Path | None) -> Dict[str, Any]:
    if v3_zip is None:
        return {"status": "NOT_REQUESTED"}
    with zipfile.ZipFile(v3_zip) as z:
        data = json.loads(z.read("session_e/results_E.json"))
    r18 = data["points"]["R1-8"]["metrics"]
    rejected = r18["promotion_candidates_rejected"]["day2_20260821/memory/digest_E4.2/memory_digest.json"]
    promoted_entries = r18["promotions_actually_created"]["day2_20260821/memory/digest_E4b/memory_digest.json"]
    obs = {
        "e4_rejected": sorted((int(x["node_id"]), int(x["frequency"]), float(x["consistency"]), bool(x["ready"])) for x in rejected),
        "e4b_promoted": sorted((int(x["node_id"]), int(x["frequency"])) for x in promoted_entries["entries"]),
    }
    expected = {
        "e4_rejected": [(9, 4, 0.75, False), (10, 4, 0.5, False)],
        "e4b_promoted": [(9, 4)],
    }
    return {"status": "PASS" if obs == expected else "FAIL", "observed": obs, "expected": expected, "results_E_sha256": sha256_file(v3_zip)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-e-zip", required=True, type=Path)
    ap.add_argument("--canonical-analysis-zip", type=Path, default=None,
                    help="Optional session_e_v3.zip cross-check")
    ap.add_argument("--out-dir", type=Path, default=Path("."))
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    local_sas = Path(__file__).with_name("sas_text.py")
    if not local_sas.exists():
        raise SystemExit("sas_text.py must be next to this script")

    with zipfile.ZipFile(args.session_e_zip) as z:
        e41, e41_names = audit_decisions_from_prefix(z, E41_PREFIX)
        e4b1, e4b1_names = audit_decisions_from_prefix(z, E4B1_PREFIX)
        candidates = reconstruct_candidates(e41, "E4.1") + reconstruct_candidates(e4b1, "E4b.1")
        archived = [normalize_archived_pref(r, "E4.1") for r in jsonl_from_zip(z, E4_ARCHIVED_M3)]
        archived += [normalize_archived_pref(r, "E4b.1") for r in jsonl_from_zip(z, E4B_ARCHIVED_M3)]
        e4_digest = json.loads(z.read(E4_DIGEST))
        e4b_digest = json.loads(z.read(E4B_DIGEST))
        zip_member_hashes = {n: sha256_bytes(z.read(n)) for n in (e41_names + e4b1_names + [E4_ARCHIVED_M3, E4B_ARCHIVED_M3, E4_DIGEST, E4B_DIGEST])}

    gate = reproduction_gate(candidates, archived)
    if gate["status"] != "PASS":
        raise SystemExit("REPRODUCTION GATE FAILED; sensitivity output suppressed")

    v3_check = extract_v3_crosscheck(args.canonical_analysis_zip)
    if v3_check["status"] == "FAIL":
        raise SystemExit("CANONICAL V3 CROSS-CHECK FAILED; sensitivity output suppressed")

    candidate_rows = []
    for c in candidates:
        x = dict(c)
        x["candidate_label"] = short_label(c)
        x["nominal_min_frequency"] = NOMINAL_MIN_FREQUENCY
        x["nominal_consistency_threshold"] = NOMINAL_CONSISTENCY
        x["consistency_minus_nominal_threshold"] = round(c["consistency_rounded"] - NOMINAL_CONSISTENCY, 2)
        x["promotion_threshold_max_for_this_candidate"] = c["consistency_rounded"]
        candidate_rows.append(x)

    candidate_fields = [
        "source_block", "candidate_label", "instruction_key_str", "instruction_examples",
        "node_outcomes", "methods", "resolved_node_id", "frequency", "dominant_count",
        "consistency_raw", "consistency_rounded", "node_counts", "method_distribution",
        "l3b_vlm_count", "ready_nominal_reconstructed", "nominal_min_frequency",
        "nominal_consistency_threshold", "consistency_minus_nominal_threshold",
        "promotion_threshold_max_for_this_candidate", "source_files",
    ]
    write_csv(out / "A3_m3_candidate_replay.csv", candidate_rows, candidate_fields)

    detail_grid = []
    summary_grid = []
    for fmin in FREQUENCY_GRID:
        for cthr in CONSISTENCY_GRID:
            promoted_labels = []
            for c in candidates:
                p = promoted(c, fmin, cthr)
                if p:
                    promoted_labels.append(short_label(c))
                detail_grid.append({
                    "min_frequency": fmin,
                    "consistency_threshold": f"{cthr:.2f}",
                    "candidate_label": short_label(c),
                    "source_block": c["source_block"],
                    "frequency": c["frequency"],
                    "consistency_rounded": f"{c['consistency_rounded']:.2f}",
                    "l3b_vlm_count": c["l3b_vlm_count"],
                    "promoted": p,
                })
            summary_grid.append({
                "min_frequency": fmin,
                "consistency_threshold": f"{cthr:.2f}",
                "promoted_count": len(promoted_labels),
                "promoted_candidates": promoted_labels,
            })

    write_csv(out / "A3_m3_promotion_sensitivity_grid.csv", detail_grid,
              ["min_frequency", "consistency_threshold", "candidate_label", "source_block", "frequency", "consistency_rounded", "l3b_vlm_count", "promoted"])
    write_csv(out / "A3_m3_promotion_summary_grid.csv", summary_grid,
              ["min_frequency", "consistency_threshold", "promoted_count", "promoted_candidates"])

    frequency_keypoints = []
    for fmin in FREQUENCY_GRID:
        labels = [short_label(c) for c in candidates if promoted(c, fmin, NOMINAL_CONSISTENCY)]
        frequency_keypoints.append({
            "min_frequency": fmin,
            "consistency_threshold_fixed": f"{NOMINAL_CONSISTENCY:.2f}",
            "promoted_count": len(labels),
            "promoted_candidates": labels,
            "is_nominal": fmin == NOMINAL_MIN_FREQUENCY,
        })
    write_csv(out / "A3_m3_frequency_keypoints.csv", frequency_keypoints,
              ["min_frequency", "consistency_threshold_fixed", "promoted_count", "promoted_candidates", "is_nominal"])

    consistency_keypoints = []
    # Exact decision-boundary points + nominal and one step above each boundary.
    kp = sorted(set([0.00, 0.50, 0.51, 0.75, 0.76, 0.80, 1.00]))
    for cthr in kp:
        labels = [short_label(c) for c in candidates if promoted(c, NOMINAL_MIN_FREQUENCY, cthr)]
        consistency_keypoints.append({
            "min_frequency_fixed": NOMINAL_MIN_FREQUENCY,
            "consistency_threshold": f"{cthr:.2f}",
            "promoted_count": len(labels),
            "promoted_candidates": labels,
            "is_nominal": math.isclose(cthr, NOMINAL_CONSISTENCY),
        })
    write_csv(out / "A3_m3_consistency_keypoints.csv", consistency_keypoints,
              ["min_frequency_fixed", "consistency_threshold", "promoted_count", "promoted_candidates", "is_nominal"])

    nominal_promoted = [short_label(c) for c in candidates if promoted(c, NOMINAL_MIN_FREQUENCY, NOMINAL_CONSISTENCY)]
    plateaus = [
        {"consistency_threshold_interval": "0.00–0.50 inclusive", "min_frequency_condition": "<=4", "promoted_count": 3, "promoted_candidates": ["deliveries", "quiet_corner", "wet_gloves"]},
        {"consistency_threshold_interval": "0.51–0.75 inclusive", "min_frequency_condition": "<=4", "promoted_count": 2, "promoted_candidates": ["quiet_corner", "wet_gloves"]},
        {"consistency_threshold_interval": "0.76–1.00 inclusive", "min_frequency_condition": "<=4", "promoted_count": 1, "promoted_candidates": ["wet_gloves"]},
        {"consistency_threshold_interval": "0.00–1.00", "min_frequency_condition": ">=5", "promoted_count": 0, "promoted_candidates": []},
    ]

    results = {
        "analysis_id": ANALYSIS_ID,
        "status": STATUS,
        "scope": "post-hoc offline sensitivity of the frozen M3 promotion gate over controlled Session E induction candidates; not parameter tuning and not a physical rerun",
        "sources": {
            "session_e_zip": Path(args.session_e_zip).name,
            "session_e_zip_sha256": sha256_file(args.session_e_zip),
            "canonical_analysis_zip": Path(args.canonical_analysis_zip).name if args.canonical_analysis_zip else None,
            "canonical_analysis_zip_sha256": sha256_file(args.canonical_analysis_zip) if args.canonical_analysis_zip else None,
            "sas_text_version": SAS_TEXT_VERSION,
            "sas_text_sha256": sha256_file(local_sas),
            "raw_audit_files": e41_names + e4b1_names,
            "zip_member_sha256": zip_member_hashes,
        },
        "population": {
            "E4.1_audit_files": len(e41_names),
            "E4.1_decisions": len(e41),
            "E4b.1_audit_files": len(e4b1_names),
            "E4b.1_decisions": len(e4b1),
            "candidate_associations": len(candidates),
        },
        "frozen_rule": {
            "min_frequency": NOMINAL_MIN_FREQUENCY,
            "consistency_threshold": NOMINAL_CONSISTENCY,
            "consistency_convention": "round(dominant_count / total, 2) before threshold comparison",
            "requires_at_least_one_L3b_vlm": True,
            "None_node_outcomes_included_in_denominator": True,
        },
        "reproduction_gate": gate,
        "canonical_v3_crosscheck": v3_check,
        "candidate_results": [
            {
                "source_block": c["source_block"], "candidate_label": short_label(c),
                "instruction": c["instruction_examples"][0], "node_outcomes": c["node_outcomes"],
                "frequency": c["frequency"], "dominant_node": c["resolved_node_id"],
                "dominant_count": c["dominant_count"], "consistency_raw": c["consistency_raw"],
                "consistency_rounded": c["consistency_rounded"], "l3b_vlm_count": c["l3b_vlm_count"],
                "promoted_at_nominal": promoted(c, NOMINAL_MIN_FREQUENCY, NOMINAL_CONSISTENCY),
            } for c in candidates
        ],
        "nominal": {"promoted_count": len(nominal_promoted), "promoted_candidates": nominal_promoted},
        "sensitivity": {
            "frequency_grid": FREQUENCY_GRID,
            "consistency_grid": {"min": 0.0, "max": 1.0, "step": 0.01},
            "decision_plateaus": plateaus,
            "key_findings": [
                "At consistency threshold 0.80, minimum-frequency settings 1 through 4 all reproduce the same outcome: only wet_gloves is promoted; minimum frequency >=5 rejects all three candidates.",
                "At minimum frequency 3, lowering consistency threshold to 0.75 promotes quiet_corner as well; lowering to 0.50 also promotes deliveries.",
                "The nominal 0.80 consistency threshold lies in the observed 0.76–1.00 plateau where only the 4/4-consistent wet_gloves association is promoted.",
                "The quiet_corner candidate is only 0.05 below the nominal consistency threshold (0.75 vs 0.80), so its rejection is boundary-sensitive to the consistency setting.",
                "All controlled candidates have frequency 4, so Session E does not empirically distinguish minimum frequency 3 from 1, 2, or 4; the frequency parameter is not optimized by this dataset.",
                "Promotion eligibility measures repeated-output stability, not semantic correctness; A3 provides no semantic ground-truth accuracy claim.",
            ],
        },
        "archived_digest_crosscheck": {
            "E4_promotions_ready": len(e4_digest.get("l3a_promotions_ready", [])),
            "E4b_promotions_ready": len(e4b_digest.get("l3a_promotions_ready", [])),
            "E4b_promoted_entries": e4b_digest.get("l3a_promotions_ready", []),
        },
        "limitations": [
            "Only three controlled candidate associations are available (two E4.1 rejection candidates and one E4b.1 promotion candidate).",
            "All three candidates have frequency 4; therefore the data characterize the threshold boundary but cannot identify an optimal minimum-frequency setting.",
            "The analysis varies only minimum frequency and consistency threshold while keeping the required >=1 L3b_vlm condition fixed.",
            "Sensitivity is post-hoc analysis of parameters frozen before Session E, not parameter tuning or a new physical experiment.",
            "Consistency is a stability criterion over observed outputs; it is not a measure of semantic truth.",
        ],
    }
    (out / "A3_m3_promotion_sensitivity_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = f"""# A3 — M3 frequency / consistency promotion-threshold sensitivity

**Status:** {STATUS}  
**Analysis ID:** `{ANALYSIS_ID}`  
**Scope:** post-hoc offline sensitivity analysis of the **frozen Session E M3 promotion gate**. This is not parameter tuning and not a physical rerun.

## Reproduction gate

The standalone public-safe implementation reads the released E4.1 and E4b.1 audit logs, clusters instructions with released `sas_text.py` v{SAS_TEXT_VERSION}, and applies the documented promotion rule:

`frequency >= 3 AND round(dominant_count / total, 2) >= 0.80 AND L3b_vlm_count >= 1`

`None` node outcomes remain in the node counter and denominator, matching the frozen extractor convention.

**Gate: {gate['status']}** — {gate['candidate_count_reconstructed']}/{gate['candidate_count_archived']} candidate associations reproduced; {gate['mismatch_count']} mismatches.  
Canonical `session_e_v3` cross-check: **{v3_check['status']}**.

## Controlled induction candidates

| Candidate | Block | Node outcomes | Frequency | Rounded consistency | Nominal outcome |
|---|---|---|---:|---:|---|
"""
    for c in candidates:
        report += f"| `{short_label(c)}` | {c['source_block']} | `{c['node_outcomes']}` | {c['frequency']} | {c['consistency_rounded']:.2f} | {'PROMOTE' if promoted(c,3,0.8) else 'REJECT'} |\n"
    report += """

At the frozen operating point (`minimum frequency = 3`, `consistency threshold = 0.80`), the two E4.1 candidates are rejected and the E4b.1 `wet_gloves` association is promoted, exactly reproducing the archived Session E outputs.

## Sensitivity findings

1. **Consistency is the discriminating parameter in the controlled Session E candidates.** With minimum frequency fixed at 3:
   - threshold `<= 0.50`: all three candidates promote;
   - `0.51–0.75`: `quiet_corner` and `wet_gloves` promote;
   - `0.76–1.00`: only `wet_gloves` promotes.

2. **The frozen 0.80 threshold lies on a stable observed plateau (`0.76–1.00`)** for these three candidates: only the 4/4-consistent association is promoted.

3. **The `quiet_corner` rejection is close to the boundary.** Its extractor-rounded consistency is 0.75, only 0.05 below the frozen threshold. A threshold of exactly 0.75 would promote it. This shows why promotion should be described as a stability gate rather than a semantic-correctness guarantee.

4. **Frequency sensitivity is weakly identified by Session E.** All three controlled candidates have frequency 4. At consistency 0.80, minimum-frequency settings 1, 2, 3, and 4 produce the same result; setting 5 or higher rejects all candidates, including the otherwise stable `wet_gloves` case. Thus Session E does **not** empirically optimize or uniquely justify `minimum frequency = 3`.

5. **Rounding is implemented production-faithfully.** The analysis computes `round(dominant_count / total, 2)` before comparison. For the three Session E candidates (2/4, 3/4, 4/4), rounding does not itself change an outcome, but retaining this convention is necessary for reproducibility and for other populations.

## Interpretation for the revision

A3 supports a conservative claim: the frozen promotion rule is exactly reproducible on the controlled Session E induction cases, and the 0.80 consistency threshold rejects both observed unstable candidates while admitting the 4/4-stable association. The analysis does **not** establish that 0.80 or frequency 3 is globally optimal. The gate measures repeated-output stability; semantic correctness requires separate safeguards and evidence.

This sensitivity analysis should therefore be presented as **post-hoc robustness characterization of a pre-frozen rule**, not as data-driven threshold selection.

## Public-release boundary

The public A3 artifact contains the standalone analysis, released `sas_text.py`, machine-readable outputs and provenance. It does **not** contain or import the protected production memory extractor or other protected SAS runtime source files.

## Files

- `analyze_A3_m3_promotion_sensitivity.py` — standalone analysis
- `sas_text.py` — approved released text-processing utility
- `A3_m3_candidate_replay.csv` — reconstructed candidate-level evidence
- `A3_m3_promotion_sensitivity_grid.csv` — candidate-level 2D grid
- `A3_m3_promotion_summary_grid.csv` — compact 2D grid summary
- `A3_m3_frequency_keypoints.csv` — frequency sweep at consistency 0.80
- `A3_m3_consistency_keypoints.csv` — consistency boundary keypoints at frequency 3
- `A3_m3_promotion_sensitivity_results.json` — machine-readable summary
- `A3_INPUT_PROVENANCE.md` — provenance and scope
- `A3_CHECKSUMS_SHA256.txt` — artifact checksums

## Limitations

- Primary experimental unit here is the **candidate association**, N=3, not the 12 underlying audit records.
- The three candidates are intentionally controlled induction cases, not a population sample from which to infer a universally optimal threshold.
- The `>=1 L3b_vlm` requirement is held fixed and is not itself ablated.
- A3 does not assess semantic ground-truth correctness of the promoted node.
"""
    (out / "A3_m3_promotion_sensitivity_report.md").write_text(report, encoding="utf-8")

    provenance = f"""# A3 input provenance

**Status:** {STATUS}

## Reviewer-facing source chain

1. **Primary raw evidence:** released Session E archive (`E.zip`), SHA-256 `{sha256_file(args.session_e_zip)}`.
2. **Controlled induction inputs:** 8 E4.1 audit JSONLs and 4 E4b.1 audit JSONLs under the day-2 memory folders.
3. **Canonical analysis cross-check:** `session_e_v3.zip` / `results_E.json` ({v3_check['status']}).
4. **Public SAS source used by this analysis:** `sas_text.py` v{SAS_TEXT_VERSION}, SHA-256 `{sha256_file(local_sas)}`.
5. **Archived extractor outputs used for the reproduction gate:** E4.2 and E4b `M3_operator_preferences.jsonl` plus their compiled `memory_digest.json` files.

## Population

- E4.1: {len(e41_names)} audit files, {len(e41)} decisions, 2 candidate associations.
- E4b.1: {len(e4b1_names)} audit files, {len(e4b1)} decisions, 1 candidate association.
- Primary A3 experimental unit: candidate association, **N=3**.

## Frozen rule reproduced

- minimum frequency: 3
- consistency threshold: 0.80
- consistency convention: `round(dominant_count / total, 2)` before threshold comparison
- at least one `L3b_vlm` resolution required
- `None` node outcomes retained in the node counter and denominator

## Protected-code policy

Protected SAS production modules are not included in, imported by, or required to execute this public-safe analysis. The production extractor was used only as internal provenance during author verification; reviewer-facing reproduction is through released raw logs, released `sas_text.py`, documented rule, archived extractor outputs, and this standalone script.
"""
    (out / "A3_INPUT_PROVENANCE.md").write_text(provenance, encoding="utf-8")

    # Checksums last, excluding checksum file itself.
    checksum_path = out / "A3_CHECKSUMS_SHA256.txt"
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != checksum_path.name)
    checksum_path.write_text("".join(f"{sha256_file(p)}  {p.name}\n" for p in files), encoding="utf-8")

    print(json.dumps({
        "analysis_id": ANALYSIS_ID,
        "status": STATUS,
        "reproduction_gate": gate["status"],
        "canonical_v3_crosscheck": v3_check["status"],
        "candidate_count": len(candidates),
        "nominal_promoted": nominal_promoted,
        "detail_grid_rows": len(detail_grid),
        "summary_grid_rows": len(summary_grid),
        "out_dir": str(out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
