#!/usr/bin/env python3
"""Extract the minimal Session E reference needed by R210-AN-02.

This script reads the internal Session E archive and exports only selected
decision/provenance fields. It does NOT copy or expose protected SAS runtime
source files. The exported JSON is analysis evidence, not a replacement for
the raw Session E archive.
"""
from __future__ import annotations
import argparse, csv, io, json, hashlib, zipfile
from pathlib import Path

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):
            h.update(b)
    return h.hexdigest()

def maybe_float(x):
    try:
        if x is None or x == "": return None
        return float(x)
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--session-e-zip", required=True)
    ap.add_argument("--out", required=True)
    a=ap.parse_args()

    zpath=Path(a.session_e_zip)
    with zipfile.ZipFile(zpath) as z:
        missions_b=z.read("data/session_e/missions.csv")
        sessions_b=z.read("data/session_e/sessions.csv")
        missions=list(csv.DictReader(io.StringIO(missions_b.decode("utf-8"))))
        sessions=list(csv.DictReader(io.StringIO(sessions_b.decode("utf-8"))))

        out=[]
        cache={}
        for m in missions:
            rel=m["audit_file"]
            path="data/session_e/"+rel
            if path not in cache:
                records=[]
                for line in z.read(path).decode("utf-8").splitlines():
                    if not line.strip(): continue
                    r=json.loads(line)
                    if r.get("_type")=="decision":
                        records.append(r)
                cache[path]={int(r["_seq"]):r for r in records}
            seq=int(m["record_seq"])
            d=cache[path][seq]
            ex=d.get("extra") or {}
            timing=d.get("timing") or {}
            images=d.get("images") or {}
            validation=d.get("validation") or {}
            rec={
                "audit_file": rel,
                "record_seq": seq,
                "run_id": m.get("run_id"),
                "experiment_id": ex.get("experiment_id", m.get("experiment_id")),
                "experiment_phase": ex.get("experiment_phase", m.get("experiment_phase")),
                "semantic_intent_id": ex.get("semantic_intent_id", m.get("semantic_intent_id")),
                "repetition_index": ex.get("repetition_index"),
                "instruction": d.get("instruction"),
                "resolution_method": d.get("resolution_method"),
                "node_id": d.get("node_id"),
                "nav_outcome": d.get("nav_outcome"),
                "validation_allowed": validation.get("allowed"),
                "validation_reason": validation.get("reason"),
                "vlm_ms": timing.get("vlm_ms"),
                "image_start_persisted": bool(images.get("start")),
                "image_start_md5": images.get("start_md5"),
                "escalation_reason": ex.get("escalation_reason"),
                "negation_intent": ex.get("negation_intent"),
                "negation_forbidden_nodes": ex.get("negation_forbidden_nodes"),
                "vlm_proposed_node": ex.get("vlm_proposed_node"),
                "vlm_negation_check": ex.get("vlm_negation_check"),
                "m3_promotion_triggered": ex.get("m3_promotion_triggered"),
                "m3_preferences_count": ex.get("m3_preferences_count"),
                "digest_content_md5": ex.get("digest_content_md5"),
            }
            # Internal consistency with canonical missions.csv for key columns.
            if str(rec["resolution_method"]) != str(m["resolution_method"]):
                raise AssertionError((rel,seq,"resolution_method",rec["resolution_method"],m["resolution_method"]))
            if str(rec["instruction"]) != str(m["instruction_text"]):
                raise AssertionError((rel,seq,"instruction"))
            out.append(rec)

    payload={
        "schema":"R210_SESSION_E_REFERENCE_V1",
        "source":{
            "session_e_zip_name":zpath.name,
            "session_e_zip_sha256":sha256_file(zpath),
            "missions_csv_sha256":hashlib.sha256(missions_b).hexdigest(),
            "sessions_csv_sha256":hashlib.sha256(sessions_b).hexdigest(),
        },
        "counts":{
            "audit_sessions":len(sessions),
            "decision_cycles":len(missions),
        },
        "decisions":out,
    }
    assert len(sessions)==214
    assert len(out)==226
    Path(a.out).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(a.out)

if __name__=="__main__":
    main()
