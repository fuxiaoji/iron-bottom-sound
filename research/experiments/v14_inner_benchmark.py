"""Cold full sequence-form versus structured inner solver, T4 Grid3 anchors."""
import argparse
import json
import resource
import time
import numpy as np
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.v14_resources import bounded
from research.experiments.v14_analysis import csvwrite
from research.formation.schedule_v14 import solve,decompose,schedules
from research.formation.pricing_v14 import hybrid


def path(c,k,mask,method):return ROOT/'inner_benchmarks'/f'{c["id"]}_{k}_S{mask:03d}_{method}.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--cell')
    p.add_argument('--opponent',choices=['C','F']);p.add_argument('--mask',type=int)
    p.add_argument('--method',choices=['full_sequence_form','structured']);a=p.parse_args()
    design=json.loads((ROOT/'DESIGN.json').read_text())
    if a.worker:
        c=next(c for c in design['cells'] if c['id']==a.cell)
        A=np.load(ROOT/'runs'/c['id']/'blue_payoff.npy');S=schedules(c['T'])[a.mask];tick=time.perf_counter()
        if a.method=='full_sequence_form':r=solve(A,c['grid'],c['T'],S,a.opponent)
        elif a.opponent=='C':r=hybrid(A,c['grid'],c['T'],S)
        else:r=decompose(A,c['grid'],c['T'],S,tuple(range(1,c['T'])),pricing=True)
        r.update({'cell':c['id'],'opponent':a.opponent,'mask':a.mask,'method':a.method,
                  'cold_solver_seconds':time.perf_counter()-tick,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'payoff_sha256':sha(ROOT/'runs'/c['id']/'blue_payoff.npy')})
        ref=json.loads((ROOT/'runs'/c['id']/f'blue_{a.opponent}_S{a.mask:03d}.json').read_text())
        if r['LB']>ref['UB']+1e-7 or r['UB']<ref['LB']-1e-7:raise RuntimeError('inner solver benchmark contradicts enumeration')
        save(path(c,a.opponent,a.mask,a.method),r);return
    rows=[]
    for c in design['cells']:
      if not (c['T']==4 and c['grid']==3 and c['ablation']=='none' and c['speed']==1 and c['distance']==16):continue
      for k in ['C','F']:
        used=0.
        for mask in range(2**(c['T']-1)):
          for method in ['full_sequence_form','structured']:
            out=path(c,k,mask,method)
            if out.exists():r=json.loads(out.read_text())
            else:
                limit=max(0.,min(1200.,21600-used))
                perf=bounded('research.experiments.v14_inner_benchmark',
                  ['--worker','--cell',c['id'],'--opponent',k,'--mask',str(mask),'--method',method],
                  limit,out.with_suffix('.log')) if limit>1 else {'reason':'instance_budget','wall_seconds':0,'tree_peak_rss_bytes':0}
                if perf['reason']=='worker_error':raise RuntimeError('inner benchmark failed; inspect method log')
                if out.exists():r=json.loads(out.read_text())
                else:
                    pay=json.loads((ROOT/'runs'/c['id']/'payoff.json').read_text())
                    r={'cell':c['id'],'opponent':k,'mask':mask,'method':method,'status':'unresolved',
                       'LB':pay['minimum'],'UB':pay['maximum'],'termination':perf['reason']}
                r['execution']=perf;save(out,r)
            used+=r['execution']['wall_seconds']
            rows.append({key:v for key,v in r.items() if key not in ['trace','core_hashes','execution']})
    if rows:csvwrite(ROOT/'inner_benchmarks/summary.csv',rows)


if __name__=='__main__':main()
