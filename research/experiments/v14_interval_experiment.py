"""Predeclared supplemental F-opponent interval-loss experiment."""
import argparse
import json
import resource
import numpy as np
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.v14_resources import bounded
from research.experiments.v14_analysis import csvwrite
from research.formation.interval_bound_v14 import interval_certificates,shortest_calendars
from research.formation.schedule_v14 import schedules
from research.formation.frontier_v14 import enumerate_frontier


def worker(c):
    d=ROOT/'runs'/c['id'];out=ROOT/'interval_bounds'/c['id'];out.mkdir(parents=True,exist_ok=True)
    A=np.load(d/'blue_payoff.npy');scale=max(1.,float(np.max(abs(A))))
    r=interval_certificates(A,c['grid'],c['T'],lambda x:save(out/'progress.json',x))
    values={s:json.loads((d/f'blue_F_S{m:03d}.json').read_text()) for m,s in enumerate(schedules(c['T']))}
    ff=enumerate_frontier(c['T'],values);rows=shortest_calendars(r)
    if r['V_full_LB']>ff[-1]['UB'] or r['V_full_UB']<ff[-1]['LB']:raise RuntimeError('interval source tree disagrees with frozen full value')
    edge={(x['t'],x['end']):x['loss_UB'] for x in r['edges']}
    for s,v in values.items():
        b=(0,)+s+(c['T'],);bound=sum(edge[t,e] for t,e in zip(b[:-1],b[1:]))
        if r['V_full_LB']-v['UB']>bound+1e-7*scale:raise RuntimeError('interval certificate violated by independent calendar value')
    for row in rows:
        ref=values[tuple(row['S'])];K=row['K']
        row.update({'cell':c['id'],'geometry':c['geometry'],'speed':c['speed'],'T':c['T'],'ablation':c['ablation'],
                    'phases':';'.join(c['phases']),'actual_loss_LB':max(0.,ff[-1]['LB']-ref['UB']),
                    'actual_loss_UB':max(0.,ff[-1]['UB']-ref['LB']),
                    'regret_to_optimum_LB':max(0.,ff[K]['LB']-ref['UB']),
                    'regret_to_optimum_UB':max(0.,ff[K]['UB']-ref['LB']),
                    'calendar_value_LB':ref['LB'],'calendar_value_UB':ref['UB']})
    decisions=[]
    for rho in [.90,.95,.99]:
        adaptation_LB=ff[-1]['LB']-ff[0]['UB']
        acceptable=[row['K'] for row in rows if row['loss_UB']<=(1-rho)*adaptation_LB]
        decisions.append({'rho':rho,'K_sufficient_by_bound':min(acceptable) if acceptable and adaptation_LB>1e-6*scale else None,
                          'scope':'sufficient conservative budget only; does not certify minimality of actual value budget'})
    r.update({'cell':c['id'],'rows':rows,'decisions':decisions,'status':'completed',
              'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'payoff_sha256':sha(d/'blue_payoff.npy'),'source_freeze_sha256':sha(ROOT/'INTERVAL_BOUND_FREEZE.json')})
    save(out/'COMPLETE.json',r)


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','test','controls'],required=True)
    p.add_argument('--worker');a=p.parse_args();design=json.loads((ROOT/'DESIGN.json').read_text())
    freeze=json.loads((ROOT/'INTERVAL_BOUND_FREEZE.json').read_text())
    if any(sha(p)!=h for p,h in freeze['source_hashes'].items()):raise RuntimeError('interval method freeze mismatch')
    if a.worker:worker(next(c for c in design['cells'] if c['id']==a.worker));return
    rows=[]
    for c in design['cells']:
        chosen=(a.phase in c['phases']) if a.phase!='controls' else (c['T']==4 and c['grid']==3 and c['speed']==1 and c['distance']==16)
        if not chosen:continue
        out=ROOT/'interval_bounds'/c['id'];dest=out/'COMPLETE.json'
        if not dest.exists():
            perf=bounded('research.experiments.v14_interval_experiment',['--phase',a.phase,'--worker',c['id']],21600,out/'worker.log')
            save(out/'execution.json',perf)
            if perf['reason']=='worker_error':raise RuntimeError('interval worker failed; inspect log')
            if not dest.exists():save(out/'UNRESOLVED.json',{'cell':c['id'],'status':'unresolved','execution':perf,'bound_source':'partial edge map retained in progress.json; complete calendar frontier not asserted'})
        if dest.exists():rows.extend(json.loads(dest.read_text())['rows'])
    if rows:csvwrite(ROOT/'interval_bounds'/f'{a.phase}.csv',rows)


if __name__=='__main__':main()
