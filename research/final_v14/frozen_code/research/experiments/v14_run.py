"""Serial, resource-bounded v14 benchmark runner; each result is resumable."""
from __future__ import annotations
import argparse,datetime,json,os,signal,subprocess,sys,time,resource
from pathlib import Path
import numpy as np
from research.experiments.v14_setup import ROOT,sha,save
from research.formation.schedule_v14 import schedules,decompose,solve
from research.formation.pricing_v14 import hybrid
from research.formation.physical_v14 import matrix

def core_hashes():
    paths=['research/formation/schedule_v14.py','research/formation/pricing_v14.py',
           'research/formation/physical_v14.py','research/experiments/v14_run.py',
           'research/formation/commitment_v12.py','research/formation/payoff_v13.py',
           'research/formation/path_following.py','research/formation/matched_horizon.py',
           'research/formation/exact_v12.py','research/experiments/v13_exact.py',
           'research/results/e01/kernel_fits.json']
    return {p:sha(p) for p in paths}

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def rss_tree(pid):
    raw=subprocess.check_output(['ps','-axo','pid=,ppid=,rss='],text=True)
    entries=[tuple(map(int,line.split())) for line in raw.splitlines() if len(line.split())==3]
    ids={pid}
    for _ in range(6):
        grown=ids|{p for p,parent,rss in entries if parent in ids}
        if grown==ids:break
        ids=grown
    return sum(rss*1024 for p,parent,rss in entries if p in ids)

def directory(c):return ROOT/'runs'/c['id']
def result_path(c,side,k,mask):return directory(c)/f'{side}_{k}_S{mask:03d}.json'

def worker(args,c):
    out=directory(c);out.mkdir(parents=True,exist_ok=True)
    if args.worker=='payoff':
        tick=time.perf_counter();A=matrix(c);M=matrix(c,True)
        expected=-A.T if c['geometry']!='parallel' else -A.T[::-1,::-1]
        error=float(np.max(abs(M-expected)))
        if error>1e-8:raise RuntimeError(f'INDEPENDENT_PAYOFF_MIRROR_FAILED {error}')
        np.save(out/'blue_payoff.npy',A);np.save(out/'red_payoff.npy',M)
        save(out/'payoff.json',{'config':c,'seconds':time.perf_counter()-tick,'mirror_error':error,
               'blue_sha256':sha(out/'blue_payoff.npy'),'red_sha256':sha(out/'red_payoff.npy'),
               'shape':list(A.shape),'scale':max(1.,float(np.max(abs(A)))),
               'minimum':float(A.min()),'maximum':float(A.max()),'created_utc':stamp(),
               'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        return
    A=np.load(out/f'{args.side}_payoff.npy');T=c['T'];base=c['grid']
    # Red focal experiments are generated physically; negative transpose only
    # presents that same physical payoff in focal-maximizer coordinates.
    if args.side=='red':A=-A.T
    S=schedules(T)[args.mask]
    tick=time.perf_counter()
    if args.opponent=='C':
        r,policy=hybrid(A,base,T,S,time_limit=args.limit,return_strategies=True)
        np.savez_compressed(out/f'{args.side}_C_S{args.mask:03d}_policy.npz',**policy)
    else:
        r=decompose(A,base,T,S,tuple(range(1,T)),time_limit=args.limit,pricing=True)
    r.update({'config_id':c['id'],'side':args.side,'opponent':args.opponent,'mask':args.mask,
              'seconds_total':time.perf_counter()-tick,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'created_utc':stamp(),'core_hashes':core_hashes(),'design_sha256':sha(ROOT/'DESIGN.json')})
    save(result_path(c,args.side,args.opponent,args.mask),r)


def launch(arguments,wall_limit,log):
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    start=time.perf_counter();peak=0;reason='completed'
    with log.open('a') as f:
        p=subprocess.Popen([sys.executable,'-u','-m','research.experiments.v14_run',*arguments],
                           stdout=f,stderr=f,env=env,start_new_session=True)
        while p.poll() is None:
            peak=max(peak,rss_tree(p.pid))
            if peak>8*1024**3:reason='memory_limit'
            elif time.perf_counter()-start>wall_limit:reason='wall_limit'
            if reason!='completed':
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                break
            time.sleep(1.)
    if p.returncode and reason=='completed':reason='worker_error'
    return {'reason':reason,'returncode':p.returncode,'wall_seconds':time.perf_counter()-start,'tree_peak_rss_bytes':peak}


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','test','robustness','ablation','all'],default='development')
    p.add_argument('--worker',choices=['payoff','solve']);p.add_argument('--cell');p.add_argument('--mask',type=int,default=0)
    p.add_argument('--opponent',default='C',choices=['C','F']);p.add_argument('--side',default='blue',choices=['blue','red'])
    p.add_argument('--limit',type=float,default=1200.);args=p.parse_args()
    design=json.loads((ROOT/'DESIGN.json').read_text())
    if args.worker:
        c=next(c for c in design['cells'] if c['id']==args.cell);worker(args,c);return
    freeze=ROOT/'RUN_FREEZE.json'
    metadata={'core_hashes':core_hashes(),'design_sha256':sha(ROOT/'DESIGN.json')}
    if freeze.exists():
        if json.loads(freeze.read_text())!=metadata:raise RuntimeError('frozen execution code/config mismatch')
    else:
        save(freeze,metadata)
        import shutil
        for src in metadata['core_hashes']:
            dest=ROOT/'frozen_code'/src;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    cells=[c for c in design['cells'] if args.phase=='all' or args.phase in c['phases']]
    for c in cells:
        out=directory(c);out.mkdir(parents=True,exist_ok=True);log=out/'worker.log'
        if not (out/'payoff.json').exists():
            perf=launch(['--worker','payoff','--cell',c['id']],21600,log)
            save(out/'payoff_execution.json',perf)
            if perf['reason']!='completed':raise RuntimeError('PAYOFF_TASK_FAILED '+c['id'])
        for side in ['blue']+(['red'] if c['mirror_solve_all'] else []):
          for k in ['C','F']:
            full=2**(c['T']-1)-1
            masks=[full,0]+[m for m in range(1,full)]
            used=0.
            for mask in masks:
                dest=result_path(c,side,k,mask)
                if dest.exists():
                    r=json.loads(dest.read_text());used+=r.get('execution',{}).get('wall_seconds',r.get('seconds_total',0.));continue
                remaining=21600-used
                perf=launch(['--worker','solve','--cell',c['id'],'--side',side,'--opponent',k,'--mask',str(mask),
                             '--limit',str(min(1200,max(1,remaining)))],min(1200,max(1,remaining)),log) if remaining>0 else {'reason':'instance_budget','wall_seconds':0,'tree_peak_rss_bytes':0}
                used+=perf['wall_seconds']
                if perf['reason']=='worker_error':raise RuntimeError('SOLVER_ERROR '+str(dest))
                if not dest.exists():
                    pay=json.loads((out/'payoff.json').read_text())
                    lo,hi=pay['minimum'],pay['maximum']
                    if side=='red':lo,hi=-hi,-lo
                    r={'config_id':c['id'],'side':side,'opponent':k,'mask':mask,'S':list(schedules(c['T'])[mask]),
                       'T':c['T'],'base':c['grid'],'V':None,'LB':lo,'UB':hi,'gap':hi-lo,'status':'unresolved',
                       'termination':perf['reason'],'bound_source':'global minimum and maximum terminal payoff',
                       'core_hashes':core_hashes(),'design_sha256':sha(ROOT/'DESIGN.json')}
                else:r=json.loads(dest.read_text())
                r['execution']=perf;save(dest,r)
                state={'updated_utc':stamp(),'phase':args.phase,'cell':c['id'],'side':side,'opponent':k,'mask':mask,
                       'latest_status':r['status'],'complete_value_files':len(list((ROOT/'runs').glob('*/*_S[0-9][0-9][0-9].json')))}
                save(ROOT/'PROGRESS.json',state)
                print(c['id'],side,k,mask,r['status'],round(perf['wall_seconds'],1),flush=True)
    save(ROOT/f'{args.phase.upper()}_RUN_COMPLETE.json',{'completed_utc':stamp(),'cells':len(cells)})

if __name__=='__main__':main()
