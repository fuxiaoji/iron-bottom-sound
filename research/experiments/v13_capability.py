"""Prospectively scoped T=4 nested absolute-speed capability check and mirrors."""
import json,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from research.experiments.v13_exact import game,differences,write,digest
from research.formation.capability_v13 import terminal_matrix,sequences,sequence_value,flexible_value,negate_plan_permutation
from research.formation.commitment_v12 import matrix_lp

ROOT=Path('research/final_v13');OUT=ROOT/'capability';OUT.mkdir(exist_ok=True)

def solve(geo,high,mirror):
    speeds=[.75,1.,1.3] if high else [.75,1.];b=[1.] if mirror else speeds;r=speeds if mirror else [1.]
    nb=3*len(b);nr=3*len(r);name=f"{geo}_{'high' if high else 'low'}_{'red' if mirror else 'blue'}";p=OUT/f'{name}.json';npz=OUT/f'{name}_payoff.npz'
    config={'geometry':geo,'T':4,'speed_menu_B':b,'speed_menu_R':r,'initial_history_speed_ratio':1.,'range_ratio':1.,
            'turn_bound_deg':60.,'formation':'leader_follower','protocol_sha256':digest(ROOT/'MECHANISM_PROTOCOL.md'),
            'core_sha256':digest('research/formation/capability_v13.py'),
            'payoff_sha256':digest('research/formation/payoff_v13.py'),
            'implementation_amendment_sha256':digest(ROOT/'IMPLEMENTATION_AMENDMENT_01.md'),
            'scope':'limited-horizon genuine nested per-turn speed capability'}
    if p.exists():
        d=json.loads(p.read_text())
        if d['config']!=config:raise RuntimeError('capability config changed')
        if d.get('complete'):return d
    else:d={'config':config,'values':{},'complete':False}
    if npz.exists():A=np.load(npz)['A']
    else:A=terminal_matrix(game(geo,1.,T=4),b,r,4);np.savez_compressed(npz,A=A)
    for s in ('FF','CC','FC','CF'):
        if s in d['values']:continue
        t=time.time()
        if s=='FF':v=flexible_value(A,nb,nr,4)
        elif s=='CC':
            z=matrix_lp(A);v={k:z[k] for k in ('V','LB','UB','gap')};v['algorithm']='complete matrix LP'
        else:v=sequence_value(A,nb,nr,4,s)
        v['seconds']=time.time()-t
        if v['UB']-v['LB']>2e-6:raise RuntimeError('capability scientific gap failed')
        d['values'][s]=v;write(p,d);print(name,s,v['V'],round(v['seconds'],1),flush=True)
    d['conditional_flexibility']=differences(d['values'],mirror);d['complete']=True;write(p,d);return d

def job(geo):
    data={}
    for high in (False,True):
        key='high' if high else 'low';data[key]={}
        for mirror in (False,True):data[key]['red' if mirror else 'blue']=solve(geo,high,mirror)
        A=np.load(OUT/f'{geo}_{key}_blue_payoff.npz')['A'];B=np.load(OUT/f'{geo}_{key}_red_payoff.npz')['A']
        expected=-A.T
        if geo=='parallel':expected=expected[np.ix_(negate_plan_permutation(1,4),negate_plan_permutation(3 if high else 2,4))]
        err=float(np.max(abs(B-expected)));data[key]['mirror_payoff_error']=err
        if err>1e-8:raise RuntimeError('capability mirror payoff failed')
        for s in ('FF','FC','CF','CC'):
            a=data[key]['blue']['values'][s];b=data[key]['red']['values'][s[::-1]]
            if abs(a['V']+b['V'])>a['UB']-a['LB']+b['UB']-b['LB']+1e-7:raise RuntimeError('capability mirror value failed')
    low=np.load(OUT/f'{geo}_low_blue_payoff.npz')['A'];high=np.load(OUT/f'{geo}_high_blue_payoff.npz')['A']
    ix=sequences(6,4)@(9**np.arange(3,-1,-1));nested=float(np.max(abs(low-high[ix])))
    if nested>1e-10:raise RuntimeError('payoffs not identical on nested action subset')
    rows=[]
    for k in ('F','C'):
        lo=data['low']['blue']['conditional_flexibility'][k];hi=data['high']['blue']['conditional_flexibility'][k]
        rows.append({'geometry':geo,'opponent_policy':k,'M':hi['F']-lo['F'],'LB':hi['LB']-lo['UB'],'UB':hi['UB']-lo['LB'],
                     'F_low':lo['F'],'F_high':hi['F'],'T':4,'nested_payoff_error':nested})
    for s in ('FF','FC','CF','CC'):
        if data['high']['blue']['values'][s]['V']<data['low']['blue']['values'][s]['V']-1e-6:raise RuntimeError('nested capability value monotonicity failed')
    d={'geometry':geo,'four_values':data,'interactions':rows};write(OUT/f'{geo}_summary.json',d);return d

def main():
    with ProcessPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,['head_on','parallel','crossing']))
    write(OUT/'all_results.json',rows)
if __name__=='__main__':main()
