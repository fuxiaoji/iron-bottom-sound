"""Continue unresolved ordinary solves within the original six-hour case cap.

Original attempts and all later attempts are retained. No precision changes.
Numerically resolved neighbors strengthen intervals by calendar inclusion.
Run only after a phase's ordinary runner has finished.
"""
import argparse
import json
from pathlib import Path
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.v14_run import result_path,directory,core_hashes,stamp
from research.experiments.v14_resources import bounded
from research.formation.schedule_v14 import schedules


def strengthen(records):
    out={}
    for s,r in records.items():
        lower=max((v['LB'],list(t)) for t,v in records.items() if set(t)<=set(s))
        upper=min((v['UB'],list(t)) for t,v in records.items() if set(t)>=set(s))
        if lower[0]>upper[0]+1e-6:raise RuntimeError('incompatible calendar inclusion intervals')
        out[s]={**r,'LB':lower[0],'UB':upper[0],'gap':max(0.,upper[0]-lower[0]),
                'inclusion_lower_calendar':lower[1],'inclusion_upper_calendar':upper[1]}
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',required=True);a=p.parse_args()
    if not (ROOT/f'{a.phase.upper()}_RUN_COMPLETE.json').exists():
        raise RuntimeError('ordinary phase must finish before continuation')
    frozen=json.loads((ROOT/'RUN_FREEZE.json').read_text())
    if frozen!={'core_hashes':core_hashes(),'design_sha256':sha(ROOT/'DESIGN.json')}:
        raise RuntimeError('frozen code changed before continuation')
    design=json.loads((ROOT/'DESIGN.json').read_text());events=[]
    for c in design['cells']:
      if a.phase not in c['phases']:continue
      for side in ['blue']+(['red'] if c['mirror_solve_all'] else []):
       for opponent in ['C','F']:
        ss=schedules(c['T']);paths=[result_path(c,side,opponent,m) for m in range(len(ss))]
        records={s:json.loads(path.read_text()) for s,path in zip(ss,paths)}
        used=sum(r.get('execution',{}).get('wall_seconds',r.get('seconds_total',0.))
                 +sum(x['execution']['wall_seconds'] for x in r.get('continuations',[])) for r in records.values())
        scale=json.loads((directory(c)/'payoff.json').read_text())['scale']
        for mask,s in enumerate(ss):
            old=records[s]
            if old['status']=='certified_numeric':continue
            original=directory(c)/'ordinary_original'/f'{side}_{opponent}_S{mask:03d}.json'
            if not original.exists():save(original,old)
            bounds=strengthen(records)[s]
            if bounds['gap']<=1e-6*scale:
                old={**bounds,'status':'certified_numeric','termination':'neighbor_inclusion_certificate'}
                save(paths[mask],old);records[s]=old;continue
            remaining=21600-used
            if remaining<=1:
                records[s]={**bounds,'status':'unresolved','termination':'instance_budget'}
                save(paths[mask],records[s]);continue
            if old.get('execution',{}).get('reason')=='memory_limit':
                # More time cannot enlarge the declared memory allowance.
                records[s]={**bounds,'status':'unresolved','termination':'memory_limit_no_time_only_retry'}
                save(paths[mask],records[s]);continue
            attempt=len(old.get('continuations',[]))+1
            archive=directory(c)/'continuation'/f'{side}_{opponent}_S{mask:03d}_before_{attempt}.json'
            save(archive,old);paths[mask].unlink()
            perf=bounded('research.experiments.v14_run',
                         ['--worker','solve','--cell',c['id'],'--side',side,'--opponent',opponent,
                          '--mask',str(mask),'--limit',str(remaining)],remaining,directory(c)/'continuation.log')
            used+=perf['wall_seconds'];new=json.loads(paths[mask].read_text()) if paths[mask].exists() else old.copy()
            if perf['reason']=='worker_error':
                save(paths[mask],old)
                save(directory(c)/'CONTINUATION_ERROR.json',{'execution':perf,'prior_record':str(archive),'created_utc':stamp()})
                raise RuntimeError('continuation worker failed; original record restored, inspect log before proceeding')
            entry={'attempt':attempt,'execution':perf,'created_utc':stamp(),'prior_record':str(archive.relative_to(ROOT))}
            new['continuations']=old.get('continuations',[])+[entry]
            new['execution']=old.get('execution',{})
            new['LB']=max(old['LB'],new['LB']);new['UB']=min(old['UB'],new['UB'])
            new['gap']=max(0.,new['UB']-new['LB'])
            if new['gap']>1e-6*scale:new['status']='unresolved';new['termination']=perf['reason']
            save(paths[mask],new);records[s]=new;events.append({'cell':c['id'],'side':side,'opponent':opponent,'mask':mask,**entry})
        strengthened=strengthen(records)
        save(directory(c)/f'{side}_{opponent}_inclusion_intervals.json',
             [{'S':list(s),'LB':r['LB'],'UB':r['UB'],'lower_calendar':r['inclusion_lower_calendar'],
               'upper_calendar':r['inclusion_upper_calendar']} for s,r in strengthened.items()])
        for s,r in strengthened.items():
            if records[s]['status']=='certified_numeric':continue
            if r['gap']<=1e-6*scale:r['status']='certified_numeric'
            save(result_path(c,side,opponent,ss.index(s)),r)
    save(ROOT/f'{a.phase.upper()}_CONTINUATION_COMPLETE.json',{'created_utc':stamp(),'attempts':events})


if __name__=='__main__':main()
