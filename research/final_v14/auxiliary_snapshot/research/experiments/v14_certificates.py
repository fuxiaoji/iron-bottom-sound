"""Evaluate deletion certificates and exact adversarial policy replays.

Certificate construction is fixed before the held-out calendar experiments.
All calendars enter the loss comparison; no favorable replay is selected by
payoff. The displayed path is the most probable leaf of a full-response law.
"""
import argparse
import json
import resource
import time
import numpy as np
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.v14_resources import bounded
from research.experiments.v14_analysis import csvwrite
from research.formation.schedule_v14 import schedules
from research.formation.frontier_v14 import enumerate_frontier,retention_budget
from research.formation.policy_v14 import certify_coarsening,conditional_saved,coarsen_full_behavior
from research.formation.recovery_v14 import full_update_policies,calendar_against_f
from research.formation.pricing_v14 import price
from research.formation.physical_v14 import make_game
from research.formation.commitment_v12 import initial_states,trajectory_batch,enumerate_sequences,GRIDS
from research.formation.payoff_v13 import paired_stage


def read_policy(path):
    with np.load(path) as d:return dict(d)


def replay(c,k,s,A,policy,out):
    base,T=c['grid'],c['T'];C=conditional_saved(policy,base,T,s)
    rs=tuple(range(1,T)) if k=='F' else ()
    red_value,_,red_map=price(-A.T*C.T,np.ones(base**T),base,T,rs)
    mass=C[np.arange(base**T),red_map]
    expected=float(np.dot(mass,A[np.arange(base**T),red_map]))
    if abs(mass.sum()-1)>1e-8 or abs(expected+red_value)>1e-7:
        raise RuntimeError('adversarial replay law disagrees with full response')
    i=int(mass.argmax());j=int(red_map[i]);seqs=enumerate_sequences(GRIDS[str(base)],T)
    g=make_game(c);b,r=initial_states(g)
    pb,hb=trajectory_batch(b,seqs[i:i+1],g);pr,hr=trajectory_batch(r,seqs[j:j+1],g)
    stage=paired_stage(g,pb,hb,pr,hr)[0];cum=np.r_[0.,np.cumsum((stage[:-1]+stage[1:])/2)]
    if abs(cum[-1]-A[i,j])>1e-8:raise RuntimeError('physical replay and stored payoff disagree')
    meta={'cell':c['id'],'opponent':k,'S':list(s),'own_leaf':i,'opponent_leaf':j,
          'blue_turns_deg':seqs[i].tolist(),'red_turns_deg':seqs[j].tolist(),
          'representative_probability':float(mass[i]),'representative_payoff':float(A[i,j]),
          'expected_payoff_all_leaves':expected,'probability_sum':float(mass.sum()),
          'selection':'maximum-probability joint leaf, lexicographic tie; not maximum-payoff leaf',
          'interpretation':'one illustration of a mixed policy; guarantee is the expectation under the complete worst-response law'}
    save(out.with_suffix('.json'),meta)
    np.savez_compressed(out.with_suffix('.npz'),blue_position=pb[0],red_position=pr[0],
                        blue_heading=hb[0],red_heading=hr[0],stage=stage,cumulative=cum)
    csvwrite(out.with_name(out.name+'_law.csv'),
             [{'own_leaf':int(i),'opponent_leaf':int(red_map[i]),'probability':float(mass[i]),
               'payoff':float(A[i,red_map[i]])} for i in np.flatnonzero(mass>0)])
    return meta


def worker(c):
    start=time.perf_counter();d=ROOT/'runs'/c['id'];out=ROOT/'certificates'/c['id'];out.mkdir(parents=True,exist_ok=True)
    A=np.load(d/'blue_payoff.npy');base,T=c['grid'],c['T'];ss=schedules(T);full=len(ss)-1
    values={k:{s:json.loads((d/f'blue_{k}_S{m:03d}.json').read_text()) for m,s in enumerate(ss)} for k in ['C','F']}
    fullF=out/'F_full_policy.npz'
    if not fullF.exists():
        rec,p=full_update_policies(A,base,T)
        ref=values['F'][ss[-1]]
        if rec['LB']>ref['UB'] or rec['UB']<ref['LB']:raise RuntimeError('FF reconstruction contradicts frozen solve')
        save(out/'F_full_recovery.json',rec);np.savez_compressed(fullF,**p)
    rows=[];replays=[]
    for k in ['C','F']:
        source_path=d/f'blue_C_S{full:03d}_policy.npz' if k=='C' else fullF
        source_missing=not source_path.exists()
        source=read_policy(fullF if source_missing else source_path)
        save(out/f'{k}_source.json',{'source':str(fullF if source_missing else source_path),
             'status':'feasible_F_opponent_source_reused_due_to_missing_C_solution' if source_missing else 'matched_full_update_source',
             'scope':'source optimality is not required for coarsening feasibility; its quality affects tightness'})
        upper=values[k][ss[-1]]['UB'];lower=values[k][ss[-1]]['LB']
        for m,s in enumerate(ss):
            tick=time.perf_counter();cert,_=certify_coarsening(A,upper,source,base,T,s,k)
            ref=values[k][s]
            if cert['lower_value']>ref['UB']+1e-7*max(1.,float(np.max(abs(A)))):
                raise RuntimeError('coarsening bound contradicts enumeration')
            rows.append({'cell':c['id'],'geometry':c['geometry'],'speed':c['speed'],'distance':c['distance'],
                         'phases':';'.join(c['phases']),'opponent':k,'mask':m,'S':','.join(map(str,s)),'K':len(s),
                         'coarsened_policy_LB':cert['lower_value'],'loss_certificate_UB':cert['loss_upper'],
                         'actual_loss_LB':max(0.,lower-ref['UB']),'actual_loss_UB':max(0.,upper-ref['LB']),
                         'certificate_seconds':time.perf_counter()-tick,'reference_status':ref['status']})
            rows[-1]['source_matched_opponent']=not source_missing
            csvwrite(out/'losses.csv',rows)
        if 'test' not in c['phases']:continue
        front=enumerate_frontier(T,values[k]);targets={tuple(r['S']) for r in front}
        scale=max(1.,float(np.max(abs(A))))
        decisions=[retention_budget(front,rho,scale) for rho in [.90,.95,.99]]
        save(out/f'{k}_decisions.json',{'frontier':front,'retention':decisions})
        for s in sorted(targets,key=lambda x:(len(x),x)):
            mask=sum(1<<(t-1) for t in s);name=f'{k}_S{mask:03d}'
            if k=='C' and (d/f'blue_C_S{mask:03d}_policy.npz').exists():pol=read_policy(d/f'blue_C_S{mask:03d}_policy.npz')
            elif k=='C':
                f,x=coarsen_full_behavior(source,base,T,s)
                pol={'representation':np.array('sequence_form'),'x':x,'S':np.array(s,dtype=int)}
            elif s==ss[-1]:pol=source
            elif (out/(name+'_policy.npz')).exists():pol=read_policy(out/(name+'_policy.npz'))
            else:
                rec,pol=calendar_against_f(A,base,T,s,values[k][s]['UB'])
                save(out/(name+'_recovery.json'),rec)
                np.savez_compressed(out/(name+'_policy.npz'),**pol)
            meta=replay(c,k,s,A,pol,out/(name+'_replay'))
            meta['reference_LB']=values[k][s]['LB'];meta['reference_UB']=values[k][s]['UB']
            meta['policy_gap_UB']=values[k][s]['UB']-meta['expected_payoff_all_leaves']+1e-8*scale
            meta['policy_status']='certified_numeric' if meta['policy_gap_UB']<=1e-6*scale else 'unresolved_policy_quality'
            save(out/(name+'_replay.json'),meta);replays.append(meta)
    save(out/'COMPLETE.json',{'cell':c['id'],'loss_rows':len(rows),'replays':len(replays),
          'seconds':time.perf_counter()-start,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'payoff_sha256':sha(d/'blue_payoff.npy'),'design_sha256':sha(ROOT/'DESIGN.json')})


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','test'],required=True)
    p.add_argument('--worker');a=p.parse_args();design=json.loads((ROOT/'DESIGN.json').read_text())
    if a.worker:worker(next(c for c in design['cells'] if c['id']==a.worker));return
    allrows=[]
    for c in design['cells']:
        if a.phase not in c['phases']:continue
        out=ROOT/'certificates'/c['id']
        if not (out/'COMPLETE.json').exists():
            perf=bounded('research.experiments.v14_certificates',['--phase',a.phase,'--worker',c['id']],21600,out/'worker.log')
            save(out/'execution.json',perf)
            if perf['reason']=='worker_error':raise RuntimeError('certificate worker failed; inspect log')
        import csv
        if (out/'losses.csv').exists():allrows.extend(list(csv.DictReader((out/'losses.csv').open())))
    if allrows:csvwrite(ROOT/'certificates'/f'{a.phase}_losses.csv',allrows)


if __name__=='__main__':main()
