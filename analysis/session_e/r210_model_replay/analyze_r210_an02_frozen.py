#!/usr/bin/env python3
"""R210-AN-02 frozen controlled-replay analyzer.

Inputs:
  --acquisition   frozen v3 acquisition tar.gz
  --replay-package corrected R2-10 input package ZIP
  --session-e-reference public-safe JSON extracted from the raw Session E archive
  --runner        executed run_replay_v3.py (for provenance hash)
  --out-prefix    output path prefix

The script uses only Python's standard library. It derives the Session E
105/91/69/22/14 population and the 39/35/22/13/4 negation accounting from
the supplied Session E reference; these values are not hard-coded as results.
"""
from __future__ import annotations
import argparse, collections, csv, glob, hashlib, itertools, json, math, os, re, statistics, tarfile, tempfile, zipfile
from pathlib import Path

MODELS=["qwen3.5:4b","gemma4:e2b","qwen3.5:9b"]
CONTROL="qwen3.5:4b"
SEEDS=[1,2,3]
EXPECTED_CONTROL_DIGEST="0c8faadc50c205b83c634430c1dae6d1a4896c9b818cb8f290aa34d535265018"
EXPECTED_SAMPLER_MD5="17d8f94f0f63578f4116e53d39219fff"

def rows(p):
    with open(p,encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def as_int(x):
    try:return int(str(x).strip())
    except:return None
def as_float(x):
    try:return float(str(x).strip())
    except:return None
def pct(k,n):return 100*k/n if n else math.nan
def med(x):return statistics.median(x) if x else math.nan
def mean(x):return statistics.mean(x) if x else math.nan
def qtile(xs,q):
    if not xs:return math.nan
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return ys[lo]
    return ys[lo]*(hi-pos)+ys[hi]*(pos-lo)
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def parse_forbidden(s):
    if isinstance(s,list):return {int(x) for x in s}
    if not s:return set()
    return {int(x) for x in re.findall(r"-?\d+",str(s))}
def load_result_csvs(results_dir,noimage=False):
    pat="results_*_noimage_*.csv" if noimage else "results_*.csv"
    fs=sorted(glob.glob(os.path.join(results_dir,pat)))
    if not noimage:fs=[p for p in fs if "_noimage_" not in os.path.basename(p)]
    out=[]
    for p in fs:
        for r in rows(p):
            r["_file"]=os.path.basename(p)
            r["node"]=as_int(r.get("node_id_int"))
            r["contract"]=r.get("contract_ok")=="True"
            r["seed_base_i"]=as_int(r.get("seed_base"))
            r["wall"]=as_float(r.get("client_wall_ms"))
            r["eval_count_i"]=as_int(r.get("eval_count"))
            out.append(r)
    return fs,out
def promo_eval(nodes,methods):
    cnt=collections.Counter(nodes); dominant,dom=cnt.most_common(1)[0]; total=len(nodes)
    consistency=round(dom/total,2)
    return {"nodes":nodes,"dominant":dominant,"consistency":consistency,
            "promote":bool(total>=3 and consistency>=0.80 and methods.count("L3b_vlm")>=1)}
def fpc(x):return f"{x:.1f}%"
def fs(ms):return f"{ms/1000:.2f} s"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--acquisition",required=True)
    ap.add_argument("--replay-package",required=True)
    ap.add_argument("--session-e-reference",required=True)
    ap.add_argument("--runner",required=True)
    ap.add_argument("--out-prefix",required=True)
    a=ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="r210_an02_") as td:
        td=Path(td)
        with tarfile.open(a.acquisition,"r:gz") as t:t.extractall(td/"acq")
        with zipfile.ZipFile(a.replay_package) as z:z.extractall(td/"pkg")
        results_dir=td/"acq"/"results_v3"
        pkg_roots=[p for p in (td/"pkg").iterdir() if p.is_dir()]
        package_dir=pkg_roots[0] if len(pkg_roots)==1 else td/"pkg"

        manifest=rows(package_dir/"manifest_inputs.csv")
        no_manifest=rows(package_dir/"manifest_escalated_no_image.csv")
        ref=rows(package_dir/"sealed"/"reference_key.csv")
        man={r["record_key"]:r for r in manifest}
        refd={r["record_key"]:r for r in ref}

        main_files,mainrows=load_result_csvs(results_dir,False)
        no_files,norows=load_result_csvs(results_dir,True)
        assert len(main_files)==9 and len(no_files)==9
        assert len(mainrows)==621 and len(norows)==126
        primary=[r for r in mainrows if r["experiment_id"]!="E0"]
        assert len(primary)==612
        record_keys=sorted({r["record_key"] for r in primary})
        assert len(record_keys)==68

        # Environment invariants.
        envfiles=sorted(glob.glob(str(results_dir/"environment_*.json")))
        envs=[json.load(open(p,encoding="utf-8")) for p in envfiles]
        assert len(envs)==6
        hosts={e["host"] for e in envs}; ollamas={e["ollama_version"] for e in envs}; gpus={e["gpu"] for e in envs}
        digests={m:{e["models"][m]["digest"] for e in envs} for m in MODELS}
        samplers={e["models"][m]["sampler_options_md5"] for e in envs for m in MODELS}
        assert len(hosts)==len(ollamas)==len(gpus)==1
        assert digests[CONTROL]=={EXPECTED_CONTROL_DIGEST}
        assert samplers=={EXPECTED_SAMPLER_MD5}
        transport=sum(r.get("json_parse")=="transport_failed" for r in mainrows+norows)
        retries=sum((as_int(r.get("attempt")) or 1)>1 for r in mainrows+norows)
        assert transport==0 and retries==0

        # Session E reference: derive population and negation accounting.
        eref=json.load(open(a.session_e_reference,encoding="utf-8"))
        ed=eref["decisions"]
        assert len(ed)==226 and eref["counts"]["audit_sessions"]==214
        methods=collections.Counter(r["resolution_method"] for r in ed)
        vlm_methods={"L3b_vlm","L3b_vlm_negation_blocked","escalated"}
        vlm_attempts=sum(methods[x] for x in vlm_methods)
        timed=sum(1 for r in ed if r["resolution_method"] in vlm_methods and r.get("vlm_ms") not in (None,""))
        accepted=methods["L3b_vlm"]; blocked=methods["L3b_vlm_negation_blocked"]; errors=methods["escalated"]
        assert (vlm_attempts,timed,accepted,blocked,errors)==(105,91,69,22,14)

        neg_all=[r for r in ed if r.get("escalation_reason")=="negation_detected"]
        guard=[r for r in neg_all if r.get("vlm_negation_check") in ("ok","vlm_requested_clarification","vlm_violated_negation")]
        clar=[r for r in guard if r.get("vlm_negation_check")=="vlm_requested_clarification"]
        ok=[r for r in guard if r.get("vlm_negation_check")=="ok"]
        viol=[r for r in guard if r.get("vlm_negation_check")=="vlm_violated_negation"]
        neg_err=[r for r in neg_all if r not in guard]
        assert (len(neg_all),len(guard),len(clar),len(ok),len(neg_err),len(viol))==(39,35,22,13,4,0)
        assert all(as_int(r.get("vlm_proposed_node"))==-1 for r in clar)

        # Populate replay metadata/outcomes.
        for r in primary:
            mm=man[r["record_key"]]
            r["escalation_reason"]=mm.get("escalation_reason","")
            r["negation_intent"]=mm.get("negation_intent","")
            r["forbidden"]=parse_forbidden(mm.get("negation_forbidden_nodes",""))
            r["orig_node"]=as_int(refd[r["record_key"]]["original_node_id"])
            r["archive_agree"]=bool(r["contract"] and r["node"]==r["orig_node"])
            isneg=r["escalation_reason"]=="negation_detected"
            if not r["contract"] or r["node"] is None:
                r["outcome"]="contract_failure"
            elif isneg and r["node"]==-1:
                r["outcome"]="negation_abstention"
            elif isneg and r["node"] in r["forbidden"]:
                r["outcome"]="forbidden_selection"
            elif 0<=r["node"]<=23:
                r["outcome"]="accepted_node"
            elif r["node"]==-1:
                r["outcome"]="other_abstention"
            else:
                r["outcome"]="other_invalid"

        # Primary model summary.
        aggregate={}; per_seed=[]
        for m in MODELS:
            md=[r for r in primary if r["model"]==m]
            for s in SEEDS:
                d=[r for r in md if r["seed_base_i"]==s]; assert len(d)==68
                per_seed.append({"model":m,"seed":s,"contract_ok":sum(r["contract"] for r in d),
                                 "archive_agree":sum(r["archive_agree"] for r in d)})
            c=collections.Counter(r["outcome"] for r in md)
            aggregate[m]={
                "contract_ok":sum(r["contract"] for r in md),
                "accepted_node":c["accepted_node"],
                "negation_abstention":c["negation_abstention"],
                "other_abstention":c["other_abstention"],
                "contract_failure":c["contract_failure"],
                "forbidden_selection":c["forbidden_selection"],
                "archive_agree":sum(r["archive_agree"] for r in md),
                "median_wall_ms":med([r["wall"] for r in md]),
                "mean_wall_ms":mean([r["wall"] for r in md]),
                "p95_wall_ms":qtile([r["wall"] for r in md],.95),
                "max_wall_ms":max(r["wall"] for r in md),
            }
        expected={
          "qwen3.5:4b":(181,160,21,0,23,137),
          "gemma4:e2b":(204,194,10,0,0,131),
          "qwen3.5:9b":(199,165,33,1,5,120),
        }
        for m,v in expected.items():
            x=aggregate[m]
            got=(x["contract_ok"],x["accepted_node"],x["negation_abstention"],x["other_abstention"],x["contract_failure"],x["archive_agree"])
            assert got==v,(m,got,v)

        # Seed stability.
        by={(r["model"],r["seed_base_i"],r["record_key"]):r for r in primary}
        stability={}
        for m in MODELS:
            allvalid=unanim=0
            for k in record_keys:
                vals=[by[(m,s,k)]["node"] if by[(m,s,k)]["contract"] else None for s in SEEDS]
                if all(v is not None for v in vals):
                    allvalid+=1
                    if len(set(vals))==1:unanim+=1
            stability[m]={"all_three_contract_valid":allvalid,"unanimous_exact_node":unanim}
        assert [stability[m]["unanimous_exact_node"] for m in MODELS]==[40,66,50]

        # Cross-model agreement same-seed.
        pair_agree={}
        for aa,bb in itertools.combinations(MODELS,2):
            agree=both=0
            for s in SEEDS:
                for k in record_keys:
                    ra,rb=by[(aa,s,k)],by[(bb,s,k)]
                    va=ra["node"] if ra["contract"] else None
                    vb=rb["node"] if rb["contract"] else None
                    if va is not None and vb is not None:
                        both+=1
                        if va==vb:agree+=1
            pair_agree[f"{aa} vs {bb}"]={"agree":agree,"both_valid":both}
        all3=all3valid=0
        for s in SEEDS:
            for k in record_keys:
                vals=[]
                for m in MODELS:
                    r=by[(m,s,k)]; vals.append(r["node"] if r["contract"] else None)
                if all(v is not None for v in vals):
                    all3valid+=1
                    if len(set(vals))==1:all3+=1
        assert (all3,all3valid)==(97,177)

        # Replay negation subset.
        neg=[r for r in primary if r["escalation_reason"]=="negation_detected"]
        neg_records={r["record_key"] for r in neg}
        assert len(neg_records)==13 and len(neg)==117
        negation={}
        for m in MODELS:
            dm=[r for r in neg if r["model"]==m]
            p=[r for r in dm if r["negation_intent"]=="prohibition"]
            e=[r for r in dm if r["negation_intent"]=="exclusion_request"]
            negation[m]={
                "overall_minus1":sum(r["outcome"]=="negation_abstention" for r in dm),
                "prohibition_minus1":sum(r["outcome"]=="negation_abstention" for r in p),
                "exclusion_minus1":sum(r["outcome"]=="negation_abstention" for r in e),
                "exclusion_actionable":sum(r["outcome"]=="accepted_node" for r in e),
                "forbidden":sum(r["outcome"]=="forbidden_selection" for r in dm),
            }
        assert sum(x["forbidden"] for x in negation.values())==0

        # Failure morphology from frozen raw responses.
        rawfiles={}
        for p in glob.glob(str(results_dir/"raw_*.jsonl")):
            if "_noimage_" in os.path.basename(p):continue
            rawfiles[os.path.basename(p)]={x["record_key"]:x for x in [json.loads(line) for line in open(p,encoding="utf-8")]}
        recover_re=re.compile(r'["\']?node_id["\']?\s*:\s*["\']?(-?\d+)')
        failure_morph={}
        for m in MODELS:
            d=[r for r in primary if r["model"]==m and not r["contract"]]
            modes=collections.Counter()
            recover=0
            for r in d:
                raw=rawfiles[f"raw_{m.replace(':','_')}_seed{r['seed_base_i']}.jsonl"][r["record_key"]]
                txt=raw["raw_content"]
                if recover_re.search(txt):recover+=1
                if r.get("done_reason")=="length":
                    modes["truncation"]+=1
                elif '\\"' in txt:
                    modes["backslash_escaping"]+=1
                elif re.search(r"\{'node_id'|'node_id'\s*:",txt):
                    modes["python_literal_quoting"]+=1
                else:
                    modes["other"]+=1
            failure_morph[m]={"failures":len(d),"unique_records":len({r["record_key"] for r in d}),
                              "modes":dict(modes),"recoverable_integer":recover}

        # Latency paired ratios.
        ratios={}
        for aa,bb in [("gemma4:e2b","qwen3.5:4b"),("qwen3.5:9b","qwen3.5:4b")]:
            rs=[by[(aa,s,k)]["wall"]/by[(bb,s,k)]["wall"] for s in SEEDS for k in record_keys]
            ratios[f"{aa}/{bb}"]={"median":med(rs),"iqr":[qtile(rs,.25),qtile(rs,.75)]}

        # Promotion archived from safe Session E reference.
        quiet="find me a quiet corner to read"
        delivery="take me to the place where deliveries arrive"
        gloves="my gloves are wet, where can I dry them"
        def archive_group(exp,phase,text):
            q=[r for r in ed if r["experiment_id"]==exp and r["experiment_phase"]==phase and r["instruction"]==text]
            q=sorted(q,key=lambda r:as_int(r.get("repetition_index")) or 0)
            return promo_eval([as_int(r["node_id"]) for r in q],[r["resolution_method"] for r in q])
        promotion={"archived":{
            "quiet":archive_group("E4","E4.1",quiet),
            "delivery":archive_group("E4","E4.1",delivery),
            "gloves":archive_group("E4b","E4b.1",gloves),
        },"replay":{}}
        assert promotion["archived"]["quiet"]["nodes"]==[9,15,9,9]
        assert promotion["archived"]["delivery"]["nodes"]==[10,None,10,5]
        assert promotion["archived"]["gloves"]["nodes"]==[9,9,9,9]

        quiet_keys=[r["record_key"] for r in manifest if r["experiment_id"]=="E4" and r["experiment_phase"]=="E4.1" and r["instruction_text"]==quiet]
        delivery_keys=[r["record_key"] for r in manifest if r["experiment_id"]=="E4" and r["experiment_phase"]=="E4.1" and r["instruction_text"]==delivery]
        gloves_keys=[r["record_key"] for r in manifest if r["experiment_id"]=="E4b" and r["experiment_phase"]=="E4b.1" and r["instruction_text"]==gloves]
        assert (len(quiet_keys),len(delivery_keys),len(gloves_keys))==(4,3,4)
        for m in MODELS:
            promotion["replay"][m]={}
            for s in SEEDS:
                def outcome(k):
                    r=by[(m,s,k)]
                    if r["contract"] and r["node"] is not None and 0<=r["node"]<=23:return r["node"],"L3b_vlm"
                    return None,"escalated"
                q=sorted(quiet_keys,key=lambda k:as_int(man[k]["repetition_index"]))
                g=sorted(gloves_keys,key=lambda k:as_int(man[k]["repetition_index"]))
                d=sorted(delivery_keys,key=lambda k:as_int(man[k]["repetition_index"]))
                qv=[outcome(k) for k in q]; gv=[outcome(k) for k in g]
                # Repetition 2 is the image-missing historical None.
                dv=[outcome(d[0]),(None,"escalated"),outcome(d[1]),outcome(d[2])]
                promotion["replay"][m][str(s)]={
                    "quiet":promo_eval([x[0] for x in qv],[x[1] for x in qv]),
                    "gloves":promo_eval([x[0] for x in gv],[x[1] for x in gv]),
                    "delivery_partial":promo_eval([x[0] for x in dv],[x[1] for x in dv]),
                }
        quiet_prom=sum(promotion["replay"][m][str(s)]["quiet"]["promote"] for m in MODELS for s in SEEDS)
        gloves_prom=sum(promotion["replay"][m][str(s)]["gloves"]["promote"] for m in MODELS for s in SEEDS)
        delivery_prom=sum(promotion["replay"][m][str(s)]["delivery_partial"]["promote"] for m in MODELS for s in SEEDS)
        assert (quiet_prom,gloves_prom,delivery_prom)==(8,9,0)

        # Supplementary no-image.
        for r in norows:
            r["contract"]=r.get("contract_ok")=="True"; r["seed_base_i"]=as_int(r.get("seed_base")); r["node"]=as_int(r.get("node_id_int")); r["wall"]=as_float(r.get("client_wall_ms"))
        noimage={}
        for m in MODELS:
            d=[r for r in norows if r["model"]==m]
            noimage[m]={"n":len(d),"contract_ok":sum(r["contract"] for r in d),"median_wall_ms":med([r["wall"] for r in d])}
        assert [noimage[m]["contract_ok"] for m in MODELS]==[3,42,37]

        summary={
          "analysis_id":"R210-AN-02",
          "status":"FROZEN",
          "core_claim":"L3b interface-level model portability, not semantic model invariance.",
          "provenance":{
            "acquisition_sha256":sha256_file(a.acquisition),
            "replay_package_sha256":sha256_file(a.replay_package),
            "session_e_reference_sha256":sha256_file(a.session_e_reference),
            "session_e_source_zip_sha256":eref["source"]["session_e_zip_sha256"],
            "runner_sha256":sha256_file(a.runner),
            "host":next(iter(hosts)),"ollama":next(iter(ollamas)),"gpu":next(iter(gpus)),
            "sampler_md5":next(iter(samplers)),"control_model_digest":next(iter(digests[CONTROL])),
            "transport_failures":transport,"retried_calls":retries,
          },
          "population":{
            "session_e_audit_sessions":eref["counts"]["audit_sessions"],
            "session_e_decisions":eref["counts"]["decision_cycles"],
            "vlm_call_path_attempts":vlm_attempts,"timed_vlm_records":timed,
            "accepted_node_image_complete_cohort":accepted,
            "negation_blocked_clarification":blocked,"error_parse":errors,
            "primary_records_excluding_E0":68,"primary_replay_outputs":612,
            "clustering_unit":"68 records, not 612 repeated outputs",
          },
          "primary_model_comparison":aggregate,
          "per_seed":per_seed,
          "intra_model_stability":stability,
          "cross_model_pairwise":pair_agree,
          "three_model":{"same_exact_node":all3,"all_three_valid":all3valid},
          "session_e_negation":{
            "activations":len(neg_all),"reached_guard":len(guard),
            "clarification_minus1":len(clar),"actionable_nonforbidden":len(ok),
            "error_parse_before_guard":len(neg_err),"forbidden_proposals":len(viol),
            "full_population_clarification_rate":len(clar)/len(guard),
            "comparability_note":"22/35 is descriptive full-population context and is not directly comparable with replay rates on the 13 outcome-conditioned cases.",
          },
          "replay_negation":{"records":len(neg_records),"outcomes":len(neg),"by_model":negation,"forbidden_selections_total":0},
          "failure_morphology":failure_morph,
          "latency_ratios":ratios,
          "promotion":promotion,
          "promotion_summary":{"quiet_promote_arms":quiet_prom,"gloves_promote_arms":gloves_prom,"delivery_promote_arms":delivery_prom},
          "noimage":noimage,
          "limitations":[
            "Multimodal replay is outcome-conditioned on original accepted-node, image-complete L3b outcomes.",
            "Archived node is a reference outcome, not semantic ground truth.",
            "Three seed bases characterize but do not exhaust decoder variability.",
            "Replay covers L3b destination selection, not the separate post-arrival visual-confirmation VLM interface.",
            "Delivery promotion is only a partial multimodal counterfactual because one original image is missing.",
            "Latency is same-machine descriptive evidence.",
            "The 22 guard-handled original clarification cases preserve parsed node_id=-1 but lack raw reply text/reason and image_start."
          ],
        }

        # Strong provenance checks for the already-frozen acquisition/runner.
        assert summary["provenance"]["acquisition_sha256"]=="f59063c0e55fbc9a021c80c97c2e0897f161f620ebb374a887ba0ee4ed54ad04"
        assert summary["provenance"]["runner_sha256"]=="58cafa07d7dca62ea249218bb317590fe9d8874c0456f804a12bc9137a4e4c7e"

        outp=Path(a.out_prefix)
        jout=outp.with_suffix(".json")
        mout=outp.with_suffix(".md")
        jout.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

        L=[]; A=L.append
        A("# R210-AN-02 — Frozen computational verification")
        A("")
        A("**Status:** FROZEN")
        A("")
        A("**Core claim:** **L3b interface-level model portability, not semantic model invariance.**")
        A("")
        A("## Integrity and population")
        A("")
        A(f"- Session E: {eref['counts']['audit_sessions']} audit sessions / {eref['counts']['decision_cycles']} decisions.")
        A(f"- VLM call path: **{vlm_attempts} attempts = {accepted} accepted-node + {blocked} clarification/blocked + {errors} error/parse; {timed} timed records**.")
        A("- Frozen replay: **69 × 3 models × 3 seeds = 621 outcomes**; primary E0-excluded analysis: **68 × 3 × 3 = 612**.")
        A("- Clustering unit: **68 records**, not the 612 repeated outputs.")
        A("")
        A("## Primary model comparison")
        A("")
        A("| Model | Parser-contract compliance | Accepted node | Negation `-1` | Other `-1` | Contract failure | Archive reference agreement | Median latency |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|")
        for m in MODELS:
            x=aggregate[m]
            A(f"| {m}{' (control)' if m==CONTROL else ''} | {x['contract_ok']}/204 = {fpc(pct(x['contract_ok'],204))} | {x['accepted_node']}/204 = {fpc(pct(x['accepted_node'],204))} | {x['negation_abstention']}/204 = {fpc(pct(x['negation_abstention'],204))} | {x['other_abstention']}/204 = {fpc(pct(x['other_abstention'],204))} | {x['contract_failure']}/204 = {fpc(pct(x['contract_failure'],204))} | {x['archive_agree']}/204 = {fpc(pct(x['archive_agree'],204))} | {fs(x['median_wall_ms'])} |")
        A("")
        A("## Negation accounting")
        A("")
        A(f"- Full Session E negation population: **{len(neg_all)} activations**; **{len(guard)}** reached the post-VLM guard.")
        A(f"- Original model: **{len(clar)}/{len(guard)} = {fpc(pct(len(clar),len(guard)))}** clarification (`-1`), **{len(ok)}/{len(guard)}** actionable non-forbidden, **{len(viol)}** forbidden proposals; **{len(neg_err)}** error/parse before guard.")
        A("- The full-population 22/35 rate is **descriptive only and is not directly compared** with replay rates.")
        A(f"- Replayable outcome-conditioned subset: **{len(neg_records)} records / {len(neg)} outcomes**, **0 forbidden selections**.")
        A("- The post-VLM guard is interpreted as a **defense-in-depth mechanism**; no observed Session E or replayable-subset case required it to block a forbidden-node proposal.")
        A("")
        A("## M3 promotion stability")
        A("")
        A(f"- Quiet corner: archived `[9,15,9,9]` reject; **{quiet_prom}/9 replay arms promote** → historical decision is not robust.")
        A(f"- Gloves: archived `[9,9,9,9]` promote; **{gloves_prom}/9 replay arms promote** → robust.")
        A(f"- Delivery: one image missing; **{delivery_prom}/9 replay arms promote** under the fixed-missing partial counterfactual → rejection remains, but this is not a full multimodal substitution.")
        A("- Frozen interpretation: **the gate measures sampled-output stability, not semantic truth**.")
        A("")
        A("## Verification")
        A("")
        A("All frozen headline assertions embedded in this script passed. Any change to the acquisition, runner, population accounting, or headline counts causes the analyzer to fail rather than silently producing a different R210-AN-02 result.")
        mout.write_text("\n".join(L)+"\n",encoding="utf-8")
        print(mout); print(jout)

if __name__=="__main__":
    main()
