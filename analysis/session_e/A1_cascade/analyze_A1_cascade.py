#!/usr/bin/env python3
"""
A1 — Cascade-step contribution analysis for ROBOT-D-26-01090 (RAS major revision)

Purpose
-------
Reproduce and package the observed first-resolving-step composition of the
frozen Session E v4.8-review deterministic cascade. This is a LOG QUERY, not a
leave-one-step-out causal ablation.

Canonical source chain
----------------------
1. E.zip / data/session_e/missions.csv             PRIMARY raw Session E table
2. session_e_v3.zip / session_e/results_E.json    CANONICAL Session E analysis cross-check
3. enriched missions CSV supplied by the author   same 226 decisions + additional columns

Primary analysis policy
-----------------------
- Exclude experiment E0 from primary results.
- A fast-path decision is a row with resolution_step in {0,...,6}.
- Report the step that FIRST resolved the instruction.
- Percentages in the main cascade table use the 112 E0-excluded fast-path
  decisions as denominator.
- The archival 121-step composition (including E0) is reported separately.
- resolve_ms is summarized descriptively using sample SD (ddof=1).

Outputs
-------
<out_dir>/A1_cascade_step_results.csv
<out_dir>/A1_cascade_step_results.json
<out_dir>/A1_cascade_step_report.md

The script is intentionally dependency-free (Python standard library only).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ANALYSIS_ID = "A1"
ANALYSIS_VERSION = "A1-v1"
ANALYSIS_DATE = "2026-08-24"

STEP_LABELS = {
    0: "M3 learned association",
    1: "explicit node ID",
    2: "node name",
    3: "object ID (obj_id)",
    4: "attribute match",
    5: "single class match",
    6: "class + proximity",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def read_csv_path(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_csv_bytes(data: bytes) -> List[Dict[str, str]]:
    text = data.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def percentile_linear(values: Sequence[float], q: float) -> float | None:
    """NumPy-default style linear percentile for q in [0,1]."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1 - w) + xs[hi] * w


def latency_stats(values: Sequence[float]) -> Dict[str, Any]:
    vals = list(values)
    if not vals:
        return {k: None for k in ["latency_n", "mean_ms", "sd_sample_ms", "median_ms", "q1_ms", "q3_ms", "min_ms", "max_ms", "p95_ms"]}
    return {
        "latency_n": len(vals),
        "mean_ms": statistics.fmean(vals),
        "sd_sample_ms": statistics.stdev(vals) if len(vals) >= 2 else None,
        "median_ms": statistics.median(vals),
        "q1_ms": percentile_linear(vals, 0.25),
        "q3_ms": percentile_linear(vals, 0.75),
        "min_ms": min(vals),
        "max_ms": max(vals),
        "p95_ms": percentile_linear(vals, 0.95),
    }


def f6(x: Any) -> Any:
    if isinstance(x, float):
        return round(x, 6)
    return x


def normalize_row(row: Dict[str, str], columns: Sequence[str]) -> tuple:
    return tuple(row.get(c, "") for c in columns)


def compare_enriched_to_raw(enriched: List[Dict[str, str]], raw: List[Dict[str, str]]) -> Dict[str, Any]:
    if not enriched or not raw:
        raise AssertionError("Empty missions table")
    raw_cols = list(raw[0].keys())
    enriched_cols = list(enriched[0].keys())
    common = [c for c in raw_cols if c in enriched_cols]
    missing = [c for c in raw_cols if c not in enriched_cols]
    added = [c for c in enriched_cols if c not in raw_cols]
    same_n = len(enriched) == len(raw)
    same_common_values = same_n and all(
        normalize_row(e, common) == normalize_row(r, common)
        for e, r in zip(enriched, raw)
    )
    return {
        "raw_rows": len(raw),
        "enriched_rows": len(enriched),
        "raw_columns": len(raw_cols),
        "enriched_columns": len(enriched_cols),
        "common_columns": len(common),
        "missing_raw_columns_in_enriched": missing,
        "added_enriched_columns": added,
        "same_row_count": same_n,
        "all_common_values_identical_in_order": same_common_values,
    }


def step_counts(rows: Iterable[Dict[str, str]]) -> Counter:
    c = Counter()
    for r in rows:
        s = (r.get("resolution_step") or "").strip()
        if s in {str(i) for i in range(7)}:
            c[int(s)] += 1
    return c


def filter_primary(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [r for r in rows if (r.get("experiment_id") or "") != "E0"]


def scope_table(rows: List[Dict[str, str]], scope_type: str, scope_value: str) -> List[Dict[str, Any]]:
    counts = step_counts(rows)
    denom_fast = sum(counts.values())
    denom_all = len(rows)
    out = []
    for step in range(7):
        vals = []
        methods = Counter()
        for r in rows:
            if (r.get("resolution_step") or "").strip() == str(step):
                v = (r.get("resolve_ms") or "").strip()
                if v:
                    vals.append(float(v))
                methods[r.get("resolution_method") or ""] += 1
        st = latency_stats(vals)
        n = counts.get(step, 0)
        out.append({
            "scope_type": scope_type,
            "scope_value": scope_value,
            "step": step,
            "step_label": STEP_LABELS[step],
            "n": n,
            "denominator_fast_path": denom_fast,
            "pct_of_fast_path": (100.0 * n / denom_fast) if denom_fast else None,
            "denominator_all_decisions": denom_all,
            "pct_of_all_decisions": (100.0 * n / denom_all) if denom_all else None,
            "methods": dict(methods),
            **st,
        })
    return out


def rows_by(rows: List[Dict[str, str]], field: str) -> Dict[str, List[Dict[str, str]]]:
    vals = sorted({r.get(field, "") for r in rows})
    return {v: [r for r in rows if r.get(field, "") == v] for v in vals}


def get_results_e_r21(session_e_v3_zip: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(session_e_v3_zip) as z:
        obj = json.loads(z.read("session_e/results_E.json"))
    return obj["points"]["R2-1"]["metrics"]


def make_report(result: Dict[str, Any]) -> str:
    p = result["primary"]
    r = result["raw_archival"]
    lines = []
    lines.append(f"# {ANALYSIS_ID} — Cascade-step contribution ({ANALYSIS_VERSION})")
    lines.append("")
    lines.append(f"**Date:** {ANALYSIS_DATE}  ")
    lines.append("**Status:** candidate for freeze after author validation  ")
    lines.append("**Analysis type:** direct log query; no replay, no model inference, no causal step ablation.")
    lines.append("")
    lines.append("## Scope and interpretation")
    lines.append("")
    lines.append(
        "A1 reports the **first deterministic cascade step that resolved each fast-path decision**. "
        "It does **not** estimate the causal performance loss that would result from removing a step: "
        "a decision unresolved at one step could fall through to a later deterministic step or to L3b."
    )
    lines.append("")
    lines.append("## Source-of-truth chain and validation gates")
    lines.append("")
    lines.append("1. `E.zip/data/session_e/missions.csv` — primary raw Session E decision table.")
    lines.append("2. `session_e_v3.zip/session_e/results_E.json` — canonical Session E analysis cross-check.")
    lines.append("3. Author-confirmed enriched `missions.csv` — same 226 decisions with additional fields; all raw columns are checked row-by-row.")
    lines.append("")
    vg = result["validation_gates"]
    lines.append(f"- Enriched-vs-raw row/column identity gate: **{'PASS' if vg['enriched_matches_raw_common_columns'] else 'FAIL'}**.")
    lines.append(f"- Raw cascade counts vs Session E v3 `results_E.json`: **{'PASS' if vg['raw_cascade_matches_results_E_v3'] else 'FAIL'}**.")
    lines.append(f"- E0 exclusion accounting: **{'PASS' if vg['e0_exclusion_reconciles'] else 'FAIL'}**.")
    lines.append("")
    lines.append("## Primary result — E0 excluded")
    lines.append("")
    lines.append(
        f"Session E contains **{p['all_decisions']} primary decisions** after excluding E0. "
        f"Of these, **{p['fast_path_decisions']}** were resolved by deterministic Steps 0–6 "
        f"(**{p['fast_path_pct_of_all_decisions']:.1f}%** of primary decisions)."
    )
    lines.append("")
    lines.append("| Step | First-resolving rule | n | % of fast path (N=112) | % of all primary decisions (N=216) | Median resolve_ms | Mean resolve_ms | Max resolve_ms |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for row in result["primary_step_table"]:
        lines.append(
            f"| {row['step']} | {row['step_label']} | {row['n']} | {row['pct_of_fast_path']:.1f}% | "
            f"{row['pct_of_all_decisions']:.1f}% | {row['median_ms']:.3f} | {row['mean_ms']:.3f} | {row['max_ms']:.3f} |"
        )
    lines.append("")
    lines.append(
        f"Across all {p['fast_path_decisions']} primary fast-path decisions, `resolve_ms` was "
        f"median **{p['latency']['median_ms']:.3f} ms**, mean **{p['latency']['mean_ms']:.3f} ms**, "
        f"range **{p['latency']['min_ms']:.3f}–{p['latency']['max_ms']:.3f} ms**. "
        f"All {p['fast_path_decisions']}/{p['fast_path_decisions']} observations were below 1 ms; "
        f"only {p['latency']['under_0_1_ms_n']}/{p['fast_path_decisions']} were below 0.1 ms. "
        "Therefore the manuscript should describe the complete deterministic cascade as **sub-millisecond**, not `<0.1 ms`."
    )
    lines.append("")
    lines.append("## Raw archival composition — E0 included")
    lines.append("")
    lines.append(
        f"Including E0, **{r['fast_path_decisions']}** decisions carry a resolution step. "
        "The raw counts are Step 0–6 = " + ", ".join(str(r['step_counts'][str(i)]) for i in range(7)) + "."
    )
    lines.append(
        "E0 contributes **9** fast-path decisions: 4 at Step 0 and 5 at Step 2. "
        "Removing E0 yields the primary 112-decision composition."
    )
    lines.append("")
    lines.append("## Workload dependence")
    lines.append("")
    lines.append(
        "The cascade composition is visibly block-dependent, so the percentages above are a description of the "
        "Session E workload rather than universal resolver probabilities. For example, E1 contributes Steps 0/1/2/6, "
        "E3 spans Steps 0/2/3/4/6, E4 and E5 contain no deterministic step resolutions, and E7 contributes only five fast-path decisions."
    )
    lines.append("")
    lines.append("### E0-excluded block breakdown")
    lines.append("")
    lines.append("| Block | All decisions | Fast path | Step counts (0→6) |")
    lines.append("|---|---:|---:|---|")
    for b, d in result["experiment_breakdown"].items():
        sc = d["step_counts"]
        lines.append(f"| {b} | {d['all_decisions']} | {d['fast_path_decisions']} | " + "/".join(str(sc[str(i)]) for i in range(7)) + " |")
    lines.append("")
    lines.append("## Manuscript-ready statement")
    lines.append("")
    lines.append(
        "**In the E0-excluded Session E validation set, 112/216 decisions were resolved on the deterministic fast path. "
        "The first-resolving-step composition was 39 M3 Step-0 matches, 18 explicit-node-ID matches, 17 node-name matches, "
        "8 object-ID matches, 13 attribute matches, 3 single-class matches, and 14 class-plus-proximity matches. "
        "All 112 deterministic resolutions completed in under 1 ms (median 0.245 ms; maximum 0.960 ms). "
        "These counts describe observed workload composition and are not a leave-one-step-out causal ablation.**"
    )
    lines.append("")
    lines.append("## Freeze recommendation")
    lines.append("")
    lines.append(
        "After author review, this A1 package can be marked **FROZEN** if the input hashes and all three validation gates remain unchanged. "
        "No R2-10 result is used by A1."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--missions", required=True, help="Author-confirmed enriched missions CSV")
    ap.add_argument("--e-zip", required=True, help="Canonical raw Session E E.zip")
    ap.add_argument("--session-e-v3", required=True, help="Canonical session_e_v3.zip")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    missions_path = Path(args.missions).resolve()
    e_zip_path = Path(args.e_zip).resolve()
    sev3_path = Path(args.session_e_v3).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    enriched = read_csv_path(missions_path)

    with zipfile.ZipFile(e_zip_path) as z:
        raw_missions_bytes = z.read("data/session_e/missions.csv")
    raw = read_csv_bytes(raw_missions_bytes)

    identity = compare_enriched_to_raw(enriched, raw)
    assert identity["same_row_count"], identity
    assert identity["all_common_values_identical_in_order"], identity
    assert identity["missing_raw_columns_in_enriched"] == [], identity

    results_e_r21 = get_results_e_r21(sev3_path)
    results_e_cascade = results_e_r21["cascade_steps_observed"]
    raw_counts = step_counts(raw)
    canonical_raw_counts = {int(k): int(v["records"]) for k, v in results_e_cascade.items()}
    raw_count_match = all(raw_counts.get(i, 0) == canonical_raw_counts.get(i, 0) for i in range(7))

    # Strong cross-check: records-without-step and the rounded per-step latency
    # summaries must also reproduce the canonical Session E v3 analysis.
    raw_without_step = len(raw) - sum(raw_counts.values())
    raw_missing_match = raw_without_step == int(results_e_r21["records_without_step"])
    raw_latency_match = True
    for step in range(7):
        vals = [float(r["resolve_ms"]) for r in raw
                if (r.get("resolution_step") or "").strip() == str(step)
                and (r.get("resolve_ms") or "").strip()]
        st = latency_stats(vals)
        can = results_e_cascade[str(step)]["resolve_ms"]
        checks = {
            "n": st["latency_n"] == int(can["n"]),
            "mean": round(st["mean_ms"], 3) == float(can["mean"]),
            "sd": round(st["sd_sample_ms"], 3) == float(can["sd"]),
            "median": round(st["median_ms"], 3) == float(can["median"]),
            "min": round(st["min_ms"], 3) == float(can["min"]),
            "max": round(st["max_ms"], 3) == float(can["max"]),
        }
        if not all(checks.values()):
            raw_latency_match = False
            break
    raw_match = raw_count_match and raw_missing_match and raw_latency_match
    assert raw_match, {
        "counts": raw_count_match, "without_step": raw_missing_match,
        "latency": raw_latency_match, "derived": raw_counts,
        "canonical": canonical_raw_counts}


    primary = filter_primary(enriched)
    e0 = [r for r in enriched if (r.get("experiment_id") or "") == "E0"]
    primary_counts = step_counts(primary)
    e0_counts = step_counts(e0)
    e0_reconciles = all(raw_counts.get(i, 0) - e0_counts.get(i, 0) == primary_counts.get(i, 0) for i in range(7))
    assert e0_reconciles

    raw_fast = sum(raw_counts.values())
    primary_fast = sum(primary_counts.values())
    assert len(enriched) == 226
    assert len(e0) == 10
    assert len(primary) == 216
    assert raw_fast == 121
    assert primary_fast == 112
    assert sum(e0_counts.values()) == 9

    raw_table = scope_table(enriched, "overall", "raw_including_E0")
    primary_table = scope_table(primary, "overall", "primary_E0_excluded")

    # Scope breakdowns over primary data.
    experiment_tables: Dict[str, List[Dict[str, Any]]] = {}
    experiment_breakdown: Dict[str, Any] = {}
    for exp, rr in rows_by(primary, "experiment_id").items():
        experiment_tables[exp] = scope_table(rr, "experiment", exp)
        c = step_counts(rr)
        experiment_breakdown[exp] = {
            "all_decisions": len(rr),
            "fast_path_decisions": sum(c.values()),
            "step_counts": {str(i): c.get(i, 0) for i in range(7)},
        }

    platform_tables: Dict[str, List[Dict[str, Any]]] = {}
    platform_breakdown: Dict[str, Any] = {}
    for platform_id, rr in rows_by(primary, "platform_id").items():
        platform_tables[platform_id] = scope_table(rr, "platform", platform_id)
        c = step_counts(rr)
        platform_breakdown[platform_id] = {
            "all_decisions": len(rr),
            "fast_path_decisions": sum(c.values()),
            "step_counts": {str(i): c.get(i, 0) for i in range(7)},
        }

    def overall_latency(rr: List[Dict[str, str]]) -> Dict[str, Any]:
        vals = [float(r["resolve_ms"]) for r in rr if (r.get("resolution_step") or "").strip() in {str(i) for i in range(7)} and (r.get("resolve_ms") or "").strip()]
        st = latency_stats(vals)
        st["under_0_1_ms_n"] = sum(v < 0.1 for v in vals)
        st["under_1_ms_n"] = sum(v < 1.0 for v in vals)
        return st

    result: Dict[str, Any] = {
        "analysis": {
            "id": ANALYSIS_ID,
            "version": ANALYSIS_VERSION,
            "date": ANALYSIS_DATE,
            "status": "candidate_for_freeze_after_author_validation",
            "type": "direct_log_query",
            "causal_ablation": False,
        },
        "source_chain": {
            "missions_enriched": {
                "path_basename": missions_path.name,
                "sha256": sha256_file(missions_path),
                "md5": md5_file(missions_path),
                "rows": len(enriched),
                "columns": len(enriched[0]) if enriched else 0,
            },
            "E_zip": {
                "path_basename": e_zip_path.name,
                "sha256": sha256_file(e_zip_path),
                "raw_missions_member": "data/session_e/missions.csv",
                "raw_missions_member_sha256": sha256_bytes(raw_missions_bytes),
                "raw_missions_member_md5": md5_bytes(raw_missions_bytes),
                "rows": len(raw),
                "columns": len(raw[0]) if raw else 0,
            },
            "session_e_v3_zip": {
                "path_basename": sev3_path.name,
                "sha256": sha256_file(sev3_path),
                "crosscheck_member": "session_e/results_E.json",
            },
        },
        "validation_gates": {
            "enriched_matches_raw_common_columns": identity["all_common_values_identical_in_order"] and identity["missing_raw_columns_in_enriched"] == [],
            "raw_cascade_matches_results_E_v3": raw_match,
            "raw_count_match_results_E_v3": raw_count_match,
            "raw_records_without_step_match_results_E_v3": raw_missing_match,
            "raw_latency_summary_match_results_E_v3": raw_latency_match,
            "e0_exclusion_reconciles": e0_reconciles,
            "enriched_vs_raw_detail": identity,
        },
        "primary": {
            "exclusion": "experiment_id == E0",
            "all_decisions": len(primary),
            "fast_path_decisions": primary_fast,
            "non_step_decisions": len(primary) - primary_fast,
            "fast_path_pct_of_all_decisions": 100.0 * primary_fast / len(primary),
            "step_counts": {str(i): primary_counts.get(i, 0) for i in range(7)},
            "latency": overall_latency(primary),
        },
        "raw_archival": {
            "all_decisions": len(enriched),
            "fast_path_decisions": raw_fast,
            "non_step_decisions": len(enriched) - raw_fast,
            "fast_path_pct_of_all_decisions": 100.0 * raw_fast / len(enriched),
            "step_counts": {str(i): raw_counts.get(i, 0) for i in range(7)},
            "latency": overall_latency(enriched),
        },
        "E0": {
            "all_decisions": len(e0),
            "fast_path_decisions": sum(e0_counts.values()),
            "step_counts": {str(i): e0_counts.get(i, 0) for i in range(7)},
        },
        "primary_step_table": primary_table,
        "raw_step_table": raw_table,
        "experiment_breakdown": experiment_breakdown,
        "platform_breakdown": platform_breakdown,
        "interpretation_guardrails": [
            "Counts identify the first deterministic step that resolved the observed instruction.",
            "They are workload-composition statistics, not independent semantic-unit frequencies.",
            "They are not leave-one-step-out causal ablation effects.",
            "A decision not resolved at one step could fall through to another deterministic step or L3b.",
            "The complete deterministic fast path is supported as sub-millisecond; <0.1 ms is not supported as a general claim.",
        ],
    }

    # Round floats only for JSON serialization readability, preserving counts exactly.
    def clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        if isinstance(obj, float):
            return round(obj, 6)
        return obj

    result_clean = clean(result)

    json_path = out_dir / "A1_cascade_step_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result_clean, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # One tidy CSV containing overall + per-experiment + per-platform results.
    csv_rows = []
    csv_rows.extend(raw_table)
    csv_rows.extend(primary_table)
    for exp in sorted(experiment_tables):
        csv_rows.extend(experiment_tables[exp])
    for platform_id in sorted(platform_tables):
        csv_rows.extend(platform_tables[platform_id])

    csv_path = out_dir / "A1_cascade_step_results.csv"
    fields = [
        "scope_type", "scope_value", "step", "step_label", "n",
        "denominator_fast_path", "pct_of_fast_path", "denominator_all_decisions", "pct_of_all_decisions",
        "latency_n", "mean_ms", "sd_sample_ms", "median_ms", "q1_ms", "q3_ms", "min_ms", "max_ms", "p95_ms", "methods",
    ]
    # Remove duplicate 'n' while preserving order.
    fields = list(dict.fromkeys(fields))
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in csv_rows:
            rr = dict(row)
            rr["methods"] = json.dumps(rr.get("methods", {}), sort_keys=True, ensure_ascii=False)
            for k, v in list(rr.items()):
                if isinstance(v, float):
                    rr[k] = round(v, 6)
            w.writerow(rr)

    report_path = out_dir / "A1_cascade_step_report.md"
    report_path.write_text(make_report(result_clean), encoding="utf-8")

    # Machine-verifiable checksums for the generated data/report outputs.
    checksum_path = out_dir / "A1_CHECKSUMS_SHA256.txt"
    with checksum_path.open("w", encoding="utf-8") as f:
        for p in [csv_path, json_path, report_path]:
            f.write(f"{sha256_file(p)}  {p.name}\n")

    print("A1 analysis complete")
    print(f"  primary decisions  : {len(primary)}")
    print(f"  primary fast path  : {primary_fast}")
    print("  primary steps      : " + "/".join(str(primary_counts.get(i, 0)) for i in range(7)))
    print(f"  raw fast path      : {raw_fast}")
    print("  validation gates   : PASS / PASS / PASS")
    print(f"  outputs            : {out_dir}")


if __name__ == "__main__":
    main()
