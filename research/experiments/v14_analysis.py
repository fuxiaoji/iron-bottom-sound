"""Deterministic complete-calendar analysis; incomplete cells stay incomplete."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from research.experiments.v14_setup import ROOT,save
from research.formation.schedule_v14 import schedules
from research.formation.frontier_v14 import enumerate_frontier,retention_budget,uniform


def csvwrite(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def analyze():
    design=json.loads((ROOT/'DESIGN.json').read_text());front=[];ret=[];struct=[];comparisons=[];summary=[];mirrors=[]
    for c in design['cells']:
        directory=ROOT/'runs'/c['id'];T=c['T'];S_all=schedules(T)
        if not (directory/'payoff.json').exists():continue
        scale=json.loads((directory/'payoff.json').read_text())['scale']
        for k in ['F','C']:
            values={}
            for mask,S in enumerate(S_all):
                p=directory/f'blue_{k}_S{mask:03d}.json'
                if p.exists():values[S]=json.loads(p.read_text())
            meta={'cell':c['id'],'geometry':c['geometry'],'speed':c['speed'],'distance':c['distance'],
                  'T':T,'grid':c['grid'],'ablation':c['ablation'],'phases':';'.join(c['phases']),'opponent':k,'scale':scale}
            if len(values)!=len(S_all):
                summary.append({**meta,'complete':False,'available':len(values),'expected':len(S_all)});continue
            ff=enumerate_frontier(T,values)
            for row in ff:
                front.append({**meta,**row,'S':','.join(map(str,row['S'])),'gap':row['UB']-row['LB']})
                K=row['K'];v=values[uniform(T,K)]
                comparisons.append({**meta,'K':K,'optimized_S':','.join(map(str,row['S'])),
                       'uniform_S':','.join(map(str,uniform(T,K))),
                       'gain_LB':row['LB']-v['UB'],'gain_UB':row['UB']-v['LB'],
                       'gain':None if row['V'] is None or v['V'] is None else row['V']-v['V'],
                       'strict_numeric_improvement':row['LB']-v['UB']>0})
            for rho in [.90,.95,.99]:
                b=retention_budget(ff,rho,scale)
                ret.append({**meta,**{a:v for a,v in b.items() if a!='comparisons'}})
            nsub=nmono=nunresolved=0;max_sub=-float('inf');witness=None
            for S in S_all:
                missing=[t for t in range(1,T) if t not in S]
                for t in missing:
                    U=tuple(sorted(S+(t,)))
                    if values[S]['LB']>values[U]['UB']:nmono+=1
                for i,a in enumerate(missing):
                    for b in missing[i+1:]:
                        sa=tuple(sorted(S+(a,)));sb=tuple(sorted(S+(b,)));sab=tuple(sorted(S+(a,b)))
                        lo=values[sab]['LB']+values[S]['LB']-values[sa]['UB']-values[sb]['UB']
                        hi=values[sab]['UB']+values[S]['UB']-values[sa]['LB']-values[sb]['LB']
                        if lo>0:nsub+=1
                        elif hi>=0:nunresolved+=1
                        if lo>max_sub:max_sub=lo;witness=[list(S),a,b,lo,hi]
            if nmono:raise RuntimeError('calendar monotonicity violation '+c['id']+' '+k)
            struct.append({**meta,'submodularity_violations':nsub,'undetermined_second_differences':nunresolved,
                           'max_violation_LB':max_sub,'witness':json.dumps(witness),'monotonicity_violations':nmono})
            summary.append({**meta,'complete':True,'available':len(values),'expected':len(S_all),
                            'unresolved':sum(v['status']!='certified_numeric' for v in values.values()),
                            'V_empty':values[()]['V'],'V_full':values[tuple(range(1,T))]['V'],
                            'adaptation_LB':ff[-1]['LB']-ff[0]['UB'],'adaptation_UB':ff[-1]['UB']-ff[0]['LB'],
                            'max_gap':max(v['UB']-v['LB'] for v in values.values()),
                            'total_worker_seconds':sum(v.get('execution',{}).get('wall_seconds',0) for v in values.values())})
            if c['mirror_solve_all']:
                for mask,S in enumerate(S_all):
                    p=directory/f'red_{k}_S{mask:03d}.json'
                    if not p.exists():continue
                    m=json.loads(p.read_text());v=values[S]
                    error=None if m['V'] is None or v['V'] is None else abs(m['V']-v['V'])
                    budget=(v['UB']-v['LB'])+(m['UB']-m['LB'])+1e-7*scale
                    if error is not None and error>budget:raise RuntimeError('mirror calendar value failure')
                    mirrors.append({**meta,'mask':mask,'error':error,'numerical_budget':budget})
    out=ROOT/'analysis'
    for name,rows in [('frontiers',front),('retention',ret),('structure',struct),('uniform_comparisons',comparisons),('cells',summary),('mirror_values',mirrors)]:
        csvwrite(out/f'{name}.csv',rows)
    report={'physical_configs':len(design['cells']),'complete_conditions':sum(r['complete'] for r in summary),
            'expected_conditions':2*len(design['cells']),'partial_conditions':sum(not r['complete'] for r in summary),
            'unresolved_values':sum(r.get('unresolved',0) for r in summary),
            'complete_test_conditions':sum(r['complete'] and 'test' in r['phases'].split(';') for r in summary),
            'conditions_with_submodularity_violation':sum(r['submodularity_violations']>0 for r in struct),
            'mirror_values_checked':len(mirrors),'final':sum(r['complete'] for r in summary)==2*len(design['cells'])}
    save(out/'SUMMARY.json',report);print(json.dumps(report,indent=2));return report

if __name__=='__main__':analyze()
