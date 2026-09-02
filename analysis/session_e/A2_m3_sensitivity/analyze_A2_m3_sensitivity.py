#!/usr/bin/env python3
"""A2 — standalone Step-0 M3 Jaccard-threshold / abstention-margin sensitivity.

Public-safe analysis implementation for ROBOT-D-26-01090 major revision.
It uses only released tabular/config inputs plus the released sas_text.py utility.
It does NOT import or require the production SAS resolver/orchestration modules.

Scope: matcher-level Step-0 M3 replay only. Counterfactual threshold/margin results
must not be interpreted as full-resolver outcomes because downstream deterministic
steps and the separate location-conflict guard are outside this A2 replay.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, sys
from collections import Counter, OrderedDict
from pathlib import Path

NOMINAL_THRESHOLD=0.75
NOMINAL_MARGIN=0.10
EXPECTED={
    'missions_sha256':'f19f380877522c6c2db64a8c8d573226b83b713602e51fce3f1847ba67004bf7',
    'sessions_sha256':'e997c2a097ba2f2cbe45e594715d160556d5a480c9ebdbc48705e804e21683f2',
    'sas_text_sha256':'aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1',
    'standard_digest_sha256':'1fe64ed09a96343bac5abd0cae476545bd0100dd496dc25122b1ca4a2cd7c3ab',
    'e4b_digest_sha256':'ee981d9c6fb6b8c8e281d8bb6abc70b537bbb43d324c01b741b8dad694dcdc30',
    'standard_digest_content_md5':'0fd61f9e82e8fe6991f0311014384e0c',
    'e4b_digest_content_md5':'5b3f14bc71a1896da5b29a4e655479fa',
}

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def content_md5(d:dict)->str:
    body={k:v for k,v in d.items() if k not in ('generated_at','content_md5')}
    raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.md5(raw).hexdigest()

def load_sas_text(path:Path):
    spec=importlib.util.spec_from_file_location('sas_text',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def fnum(v):
    if v is None or v=='': return None
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except: return None

def fint(v):
    x=fnum(v)
    return None if x is None else int(x)

def build_index(digest:dict, sas_text):
    out=[]
    for idx,pref in enumerate(digest.get('l3a_promotions_ready',[])):
        examples=[]
        for ex in pref.get('instruction_examples',[]):
            toks=sas_text.tokenize(ex)
            if toks: examples.append((ex,toks))
        if examples:
            out.append({'idx':idx,'node_id':fint(pref.get('node_id')),
                        'frequency':int(pref.get('frequency',0)), 'examples':examples})
    return out

def rank_instruction(text,index,sas_text):
    neg,markers=sas_text.detect_negation(text)
    if neg:
        return {'negated':True,'negation_markers':markers,'tokens':sorted(sas_text.tokenize(text)),
                'top_node':None,'top_score':None,'runner_up_node':None,'runner_up_score':None,
                'gap':None,'matched_example':None,'candidate_nodes':0}
    toks=sas_text.tokenize(text)
    if not toks:
        return {'negated':False,'negation_markers':[],'tokens':[], 'top_node':None,
                'top_score':None,'runner_up_node':None,'runner_up_score':None,'gap':None,
                'matched_example':None,'candidate_nodes':0}
    # Ordered per-node aggregation: maximum Jaccard over examples mapping to each node.
    # Equal-score ordering follows first node appearance in the digest, matching the
    # documented deterministic ranking semantics used for the released analysis.
    best=OrderedDict(); best_ex={}
    for pref in index:
        nid=pref['node_id']
        if nid not in best: best[nid]=-1.0
        for raw,etok in pref['examples']:
            s=sas_text.jaccard(toks,etok)
            if s>best[nid]: best[nid]=s; best_ex[nid]=raw
    ranked=sorted(best.items(),key=lambda kv:-kv[1])
    if not ranked:
        return {'negated':False,'negation_markers':[],'tokens':sorted(toks),'top_node':None,
                'top_score':None,'runner_up_node':None,'runner_up_score':None,'gap':None,
                'matched_example':None,'candidate_nodes':0}
    tn,ts=ranked[0]; rn,rs=(ranked[1] if len(ranked)>1 else (None,None))
    return {'negated':False,'negation_markers':[],'tokens':sorted(toks),'top_node':tn,
            'top_score':ts,'runner_up_node':rn,'runner_up_score':rs,
            'gap':None if rs is None else ts-rs,'matched_example':best_ex.get(tn),
            'candidate_nodes':len(ranked)}

def classify(rank,threshold,margin):
    if rank['negated']: return ('abstain_negation',None)
    if rank['top_score'] is None: return ('abstain_no_candidate',None)
    if rank['top_score'] < threshold: return ('abstain_below_threshold',None)
    if rank['runner_up_score'] is not None and rank['gap'] < margin:
        return ('abstain_ambiguous_margin',None)
    return ('accept',rank['top_node'])

def pct(k,n): return None if n==0 else 100.0*k/n

def summarize(rows,threshold,margin,nominal_accept_keys):
    outcomes=[]
    for r in rows:
        status,node=classify(r['rank'],threshold,margin)
        outcomes.append((r,status,node))
    c=Counter(s for _,s,_ in outcomes)
    accepted=[(r,n) for r,s,n in outcomes if s=='accept']
    accepted_keys={r['record_key'] for r,_ in accepted}
    exp=[(r,n) for r,n in accepted if r['expected_node_id'] is not None]
    exp_agree=sum(1 for r,n in exp if n==r['expected_node_id'])
    exp_disagree=len(exp)-exp_agree
    runner=sum(1 for r,n in accepted if r['rank']['runner_up_score'] is not None)
    no_runner=len(accepted)-runner
    nonneg=sum(1 for r in rows if not r['rank']['negated'])
    return {
        'threshold':threshold,'margin':margin,'n_active_m3_records':len(rows),
        'n_nonnegated_records':nonneg,
        'accepted_records':len(accepted),'accepted_rate_all_active_pct':pct(len(accepted),len(rows)),
        'accepted_rate_nonnegated_pct':pct(len(accepted),nonneg),
        'accepted_unique_instruction_texts':len({r['instruction_text'] for r,_ in accepted}),
        'accepted_unique_semantic_intents':len({r['semantic_intent_id'] for r,_ in accepted if r['semantic_intent_id']}),
        'abstain_negation':c['abstain_negation'],'abstain_below_threshold':c['abstain_below_threshold'],
        'abstain_ambiguous_margin':c['abstain_ambiguous_margin'],'abstain_no_candidate':c['abstain_no_candidate'],
        'accepted_with_runner_up':runner,'accepted_without_runner_up':no_runner,
        'accepted_with_expected_node':len(exp),'expected_node_agree':exp_agree,
        'expected_node_disagree':exp_disagree,
        'expected_node_agreement_pct':pct(exp_agree,len(exp)),
        'new_accepts_vs_nominal':len(accepted_keys-nominal_accept_keys),
        'lost_accepts_vs_nominal':len(nominal_accept_keys-accepted_keys),
    }

def main():
    ap=argparse.ArgumentParser()
    base=Path(__file__).resolve().parent
    ap.add_argument('--missions',type=Path,default=base/'inputs/missions.csv')
    ap.add_argument('--sessions',type=Path,default=base/'inputs/sessions.csv')
    ap.add_argument('--sas-text',type=Path,default=base/'inputs/sas_text.py')
    ap.add_argument('--standard-digest',type=Path,default=base/'inputs/memory_digest_standard.json')
    ap.add_argument('--e4b-digest',type=Path,default=base/'inputs/memory_digest_E4b.json')
    ap.add_argument('--outdir',type=Path,default=base)
    args=ap.parse_args(); args.outdir.mkdir(parents=True,exist_ok=True)

    hashes={'missions':sha256(args.missions),'sessions':sha256(args.sessions),'sas_text':sha256(args.sas_text),
            'standard_digest':sha256(args.standard_digest),'e4b_digest':sha256(args.e4b_digest)}
    assert hashes['missions']==EXPECTED['missions_sha256']
    assert hashes['sessions']==EXPECTED['sessions_sha256']
    assert hashes['sas_text']==EXPECTED['sas_text_sha256']
    assert hashes['standard_digest']==EXPECTED['standard_digest_sha256']
    assert hashes['e4b_digest']==EXPECTED['e4b_digest_sha256']

    sas_text=load_sas_text(args.sas_text)
    assert getattr(sas_text,'SAS_TEXT_VERSION',None)=='1.2.0'
    standard=json.loads(args.standard_digest.read_text(encoding='utf-8'))
    e4b=json.loads(args.e4b_digest.read_text(encoding='utf-8'))
    hstd=content_md5(standard); he4b=content_md5(e4b)
    assert hstd==EXPECTED['standard_digest_content_md5']; assert he4b==EXPECTED['e4b_digest_content_md5']
    indices={hstd:build_index(standard,sas_text),he4b:build_index(e4b,sas_text)}

    with args.sessions.open(newline='',encoding='utf-8-sig') as f: sessions=list(csv.DictReader(f))
    assert len(sessions)==214
    assert {round(float(r['m3_jaccard_threshold']),10) for r in sessions}=={NOMINAL_THRESHOLD}
    assert {round(float(r['m3_abstention_margin']),10) for r in sessions}=={NOMINAL_MARGIN}
    assert {r.get('sas_text_version') for r in sessions}=={'1.2.0'}

    with args.missions.open(newline='',encoding='utf-8-sig') as f: missions=list(csv.DictReader(f))
    assert len(missions)==226
    primary=[r for r in missions if r.get('experiment_id')!='E0']
    assert len(primary)==216
    active=[r for r in primary if (fint(r.get('m3_preferences_count')) or 0)>0]
    no_m3=[r for r in primary if (fint(r.get('m3_preferences_count')) or 0)==0]
    assert len(active)==212 and len(no_m3)==4
    digest_dist=Counter(r.get('digest_content_md5','') for r in active)
    assert digest_dist==Counter({hstd:207,he4b:5})

    rows=[]
    for r in active:
        dh=r['digest_content_md5']; assert dh in indices
        rank=rank_instruction(r['instruction_text'],indices[dh],sas_text)
        rows.append({
            'record_key':f"{r['audit_file']}#{r['record_seq']}", 'audit_file':r['audit_file'],
            'record_seq':int(r['record_seq']), 'experiment_id':r['experiment_id'],
            'semantic_intent_id':r.get('semantic_intent_id',''), 'instruction_text':r['instruction_text'],
            'digest_content_md5':dh,'m3_preferences_count':fint(r.get('m3_preferences_count')),
            'observed_resolution_step':fint(r.get('resolution_step')),
            'observed_node_id':fint(r.get('node_id')),'expected_node_id':fint(r.get('expected_node_id')),
            'rank':rank,
        })

    # Mandatory reproduction gate at frozen operating point.
    mismatches=[]; node_mismatches=[]
    nominal_accept_keys=set()
    for r in rows:
        status,node=classify(r['rank'],NOMINAL_THRESHOLD,NOMINAL_MARGIN)
        obs=(r['observed_resolution_step']==0)
        sim=(status=='accept')
        if obs!=sim: mismatches.append(r['record_key'])
        if sim:
            nominal_accept_keys.add(r['record_key'])
            if r['observed_node_id']!=node: node_mismatches.append(r['record_key'])
    assert not mismatches, f'reproduction accept/abstain mismatches: {mismatches[:10]}'
    assert not node_mismatches, f'reproduction node mismatches: {node_mismatches[:10]}'
    assert len(nominal_accept_keys)==39

    # Record-level replay table.
    recpath=args.outdir/'A2_m3_record_replay.csv'
    with recpath.open('w',newline='',encoding='utf-8') as f:
        fields=['record_key','audit_file','record_seq','experiment_id','semantic_intent_id','instruction_text',
                'digest_content_md5','m3_preferences_count','negated','negation_markers','candidate_nodes',
                'top_node','top_score','runner_up_node','runner_up_score','gap','matched_example',
                'observed_resolution_step','observed_node_id','expected_node_id','nominal_status','nominal_node']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            st,n=classify(r['rank'],NOMINAL_THRESHOLD,NOMINAL_MARGIN); q=r['rank']
            w.writerow({
                'record_key':r['record_key'],'audit_file':r['audit_file'],'record_seq':r['record_seq'],
                'experiment_id':r['experiment_id'],'semantic_intent_id':r['semantic_intent_id'],
                'instruction_text':r['instruction_text'],'digest_content_md5':r['digest_content_md5'],
                'm3_preferences_count':r['m3_preferences_count'],'negated':q['negated'],
                'negation_markers':'|'.join(q['negation_markers']),'candidate_nodes':q['candidate_nodes'],
                'top_node':q['top_node'],'top_score':q['top_score'],'runner_up_node':q['runner_up_node'],
                'runner_up_score':q['runner_up_score'],'gap':q['gap'],'matched_example':q['matched_example'],
                'observed_resolution_step':r['observed_resolution_step'],'observed_node_id':r['observed_node_id'],
                'expected_node_id':r['expected_node_id'],'nominal_status':st,'nominal_node':n})

    # Fine deterministic sensitivity surface: J in [0.20,1.00], margin in [0,0.30], step 0.01.
    grid=[]
    for ti in range(20,101):
        th=ti/100.0
        for mi in range(0,31):
            mar=mi/100.0
            grid.append(summarize(rows,th,mar,nominal_accept_keys))
    gpath=args.outdir/'A2_m3_sensitivity_grid.csv'
    with gpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(grid[0].keys())); w.writeheader(); w.writerows(grid)

    threshold_points=[0.20,0.25,0.375,0.50,0.60,0.625,0.65,0.70,0.75,0.85,1.00]
    tpoints=[summarize(rows,x,NOMINAL_MARGIN,nominal_accept_keys) for x in threshold_points]
    tpath=args.outdir/'A2_m3_threshold_keypoints.csv'
    with tpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(tpoints[0].keys())); w.writeheader(); w.writerows(tpoints)

    margin_points=[0.00,0.05,0.10,0.15,0.20,0.30,0.50,0.80,0.90,1.00]
    mpoints=[summarize(rows,NOMINAL_THRESHOLD,x,nominal_accept_keys) for x in margin_points]
    mpath=args.outdir/'A2_m3_margin_keypoints.csv'
    with mpath.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(mpoints[0].keys())); w.writeheader(); w.writerows(mpoints)

    # Score/gap distributions are deterministic and useful for interpreting plateaus.
    nonneg=[r for r in rows if not r['rank']['negated']]
    score_counts=Counter(round(r['rank']['top_score'],9) for r in nonneg if r['rank']['top_score'] is not None)
    gap_counts=Counter('NONE' if r['rank']['gap'] is None else round(r['rank']['gap'],9) for r in nonneg)
    nominal=summarize(rows,NOMINAL_THRESHOLD,NOMINAL_MARGIN,nominal_accept_keys)
    old060=summarize(rows,0.60,NOMINAL_MARGIN,nominal_accept_keys)
    # Records newly admitted at the manuscript's former 0.60 threshold.
    newly=[]
    for r in rows:
        s075,n075=classify(r['rank'],0.75,0.10); s060,n060=classify(r['rank'],0.60,0.10)
        if s060=='accept' and s075!='accept':
            newly.append({'record_key':r['record_key'],'experiment_id':r['experiment_id'],
                          'semantic_intent_id':r['semantic_intent_id'],'instruction_text':r['instruction_text'],
                          'candidate_node':n060,'top_score':r['rank']['top_score'],'gap':r['rank']['gap'],
                          'expected_node_id':r['expected_node_id']})

    results={
      'analysis_id':'A2','status':'candidate_not_frozen','scope':'Step-0 M3 matcher sensitivity only',
      'nominal':{'jaccard_threshold':NOMINAL_THRESHOLD,'abstention_margin':NOMINAL_MARGIN},
      'inputs':{'sha256':hashes,'digest_content_md5':{'standard':hstd,'E4b':he4b},
                'sas_text_version':sas_text.SAS_TEXT_VERSION},
      'population':{'session_e_raw_decisions':226,'E0_excluded_primary_decisions':216,
                    'M3_active_primary_records':212,'M3_empty_E6_records_excluded':4,
                    'digest_distribution':dict(digest_dist),
                    'unique_instruction_texts':len({r['instruction_text'] for r in rows}),
                    'unique_semantic_intents':len({r['semantic_intent_id'] for r in rows if r['semantic_intent_id']}),
                    'negation_detected_records':sum(r['rank']['negated'] for r in rows),
                    'nonnegated_matcher_records':sum(not r['rank']['negated'] for r in rows)},
      'reproduction_gate':{'pass':True,'accept_abstain_agreement':'212/212','accepted_node_agreement':'39/39',
                           'observed_step0_matches':39,'nominal_simulated_matches':39},
      'nominal_summary':nominal,'former_threshold_0_60_summary':old060,
      'score_distribution_nonnegated':{str(k):v for k,v in sorted(score_counts.items(),key=lambda x:float(x[0]))},
      'gap_distribution_nonnegated':{str(k):v for k,v in gap_counts.items()},
      'newly_admitted_at_0_60_vs_0_75':newly,
      'interpretation_flags':{
         'threshold_plateau':'At the frozen margin 0.10, thresholds >0.625 and <=1.0 retain the same 39 matcher-level accepts in this released primary population.',
         'margin_nominal_inactive':'At threshold 0.75, no accepted multi-candidate record has a runner-up gap below 0.80; margin 0.10 therefore does not trigger.',
         'not_full_resolver':'Counterfactual matcher accepts are not final navigation decisions; downstream cascade steps and the separate location-conflict guard are outside A2.',
         'not_parameter_tuning':'This is a post-hoc sensitivity analysis of a threshold/margin pair frozen before Session E, not optimization on Session E outcomes.'
      }
    }
    (args.outdir/'A2_m3_sensitivity_results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'reproduction_gate':'PASS','active_records':212,'nominal_matches':39,
                      'former_0.60_matches':old060['accepted_records'],'grid_rows':len(grid)},indent=2))

if __name__=='__main__': main()
