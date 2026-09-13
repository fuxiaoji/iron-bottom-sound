"""Calendar search comparisons: explicit trace replay versus actual cold runs."""
import argparse,json,time,resource,signal
from pathlib import Path
import numpy as np
from research.experiments.v14_setup import ROOT,save,sha
from research.formation.schedule_v14 import schedules,decompose
from research.formation.pricing_v14 import hybrid,price
from research.formation.policy_v14 import conditional_saved
from research.formation.frontier_v14 import branch_bound,uniform,greedy
from research.experiments.v14_analysis import csvwrite
from research.experiments.v14_resources import bounded

METHODS=['enumeration','branch_bound','response_bound','greedy','uniform','front','back']

def alarm_timeout(signum,frame):raise TimeoutError('ordinary calendar oracle wall limit')


class Oracle:
    def __init__(self,c,k,mode,truth):
        self.c,self.k,self.mode,self.truth=c,k,mode,truth
        self.T,self.base=c['T'],c['grid'];self.dir=ROOT/'runs'/c['id']
        self.A=np.load(self.dir/'blue_payoff.npy');self.scale=max(1.,float(np.max(abs(self.A))))
        self.cache={};self.pool=[];self.oracle_seconds=0.;self.response_seconds=0.;self.response_calls=0
        self.calls=[]
        self.journal=None
    def __call__(self,S):
        S=tuple(S)
        if S in self.cache:return self.cache[S]
        tick=time.perf_counter();mask=sum(1<<(t-1) for t in S);pol=None
        if self.mode=='trace':
            r=self.truth[S]
            self.oracle_seconds+=r.get('seconds_total',r.get('seconds',0.))
            if self.k=='C':
                p=self.dir/f'blue_C_S{mask:03d}_policy.npz'
                if p.exists():
                    with np.load(p) as d:pol=dict(d)
            elif not S:
                p=ROOT/'benchmarks/pools'/f'{self.c["id"]}_R_F.npz'
                if p.exists():
                    with np.load(p) as d:self.pool.append(d['conditional'])
        else:
            old_handler=signal.signal(signal.SIGALRM,alarm_timeout);signal.setitimer(signal.ITIMER_REAL,1200.)
            try:
                if self.k=='C':r,pol=hybrid(self.A,self.base,self.T,S,return_strategies=True)
                elif not S:
                    inv,rpol=hybrid(-self.A.T,self.base,self.T,tuple(range(1,self.T)),return_strategies=True)
                    r={**inv,'V':-inv['V'],'LB':-inv['UB'],'UB':-inv['LB'],'S':[]}
                    C=conditional_saved(rpol,self.base,self.T,tuple(range(1,self.T)))
                    self.pool.append(C)
                    p=ROOT/'benchmarks/pools'/f'{self.c["id"]}_R_F.npz';p.parent.mkdir(parents=True,exist_ok=True)
                    np.savez_compressed(p,conditional=C)
                else:r=decompose(self.A,self.base,self.T,S,tuple(range(1,self.T)),pricing=True)
            except (TimeoutError,RuntimeError) as exc:
                if not isinstance(exc,TimeoutError) and 'Time limit' not in str(exc):raise
                r={'S':list(S),'V':None,'LB':float(self.A.min()),'UB':float(self.A.max()),
                   'status':'unresolved','termination':'oracle_time_limit'}
            finally:
                signal.setitimer(signal.ITIMER_REAL,0.);signal.signal(signal.SIGALRM,old_handler)
            self.oracle_seconds+=time.perf_counter()-tick
            ref=self.truth[S]
            if r['LB']>ref['UB']+1e-7*self.scale or r['UB']<ref['LB']-1e-7*self.scale:
                raise RuntimeError('cold benchmark and frozen enumeration disagree')
        if pol is not None:
            q=pol['y'][1:] if 'representation' in pol else pol['q']
            if abs(q.sum()-1)>1e-8 or min(q)<-1e-10:raise RuntimeError('invalid reusable committed opponent')
            self.pool.append(q)
        self.cache[S]=r;self.calls.append(list(S))
        if self.journal is not None:
            save(self.journal,{'oracle_schedules':self.calls,'values':list(self.cache.values()),
                              'oracle_seconds':self.oracle_seconds,'response_seconds':self.response_seconds,
                              'response_calls':self.response_calls})
        return r
    def upper(self,U):
        tick=time.perf_counter();best=float('inf')
        for q in self.pool:
            if q.ndim==1:u=price(self.A,q,self.base,self.T,U)[0]
            else:u=price(self.A*q.T,np.ones(self.base**self.T),self.base,self.T,U)[0]
            self.response_calls+=1;best=min(best,u+1e-8*self.scale)
        self.response_seconds+=time.perf_counter()-tick
        return best


def run_case(c,k,mode,only_method=None):
    T=c['T'];truth={};directory=ROOT/'runs'/c['id']
    for mask,S in enumerate(schedules(T)):
        p=directory/f'blue_{k}_S{mask:03d}.json'
        if not p.exists():return None
        truth[S]=json.loads(p.read_text())
    results=[]
    for method in ([only_method] if only_method else METHODS):
        oracle=Oracle(c,k,mode,truth);tick=time.perf_counter();budgets=[]
        oracle.journal=ROOT/'benchmarks'/mode/f'{c["id"]}_{k}_{method}_progress.json'
        if method=='enumeration':
            for S in schedules(T):oracle(S)
        for K in range(T):
            if method in ['branch_bound','response_bound']:
                r=branch_bound(T,K,oracle,1e-6*oracle.scale,oracle.upper if method=='response_bound' else None)
            elif method=='greedy':r=greedy(T,K,oracle)
            elif method=='enumeration':
                s=max((s for s in oracle.cache if len(s)<=K),key=lambda s:oracle.cache[s]['LB'])
                r={**oracle.cache[s],'S':list(s),'UB':max(v['UB'] for s,v in oracle.cache.items() if len(s)<=K)}
            else:
                s=uniform(T,K) if method=='uniform' else (tuple(range(1,K+1)) if method=='front' else tuple(range(T-K,T)))
                r={**oracle(s),'S':list(s)}
            optlo=max(v['LB'] for s,v in truth.items() if len(s)<=K)
            opthi=max(v['UB'] for s,v in truth.items() if len(s)<=K)
            if method in ['branch_bound','response_bound'] and r['UB']<optlo-1e-7*oracle.scale:
                raise RuntimeError('search pruned optimum')
            budgets.append({'K':K,'S':r['S'],'LB':r['LB'],'UB':r['UB'],
                            'regret_LB':max(0,optlo-r['UB']),'regret_UB':max(0,opthi-r['LB']),
                            'search_status':r.get('status','baseline')})
        elapsed=time.perf_counter()-tick
        out={'cell':c['id'],'opponent':k,'mode':mode,'method':method,'budgets':budgets,
             'oracle_calls':len(oracle.cache),'response_calls':oracle.response_calls,
             'oracle_seconds':oracle.oracle_seconds,'response_seconds':oracle.response_seconds,
             'wall_seconds':elapsed,'accounted_seconds':oracle.oracle_seconds+oracle.response_seconds,
             'oracle_schedules':oracle.calls,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'timing_scope':('actual serial cold solver calls, shared payoff loaded before timer; intra-method calendar cache across budgets' if mode=='cold'
                             else 'online decision trace replay; oracle time charged from stored individual solves, not wall-clock speedup'),
             'policy_pool_count':len(oracle.pool)}
        out['status']='completed' if all(v['status']=='certified_numeric' for v in oracle.cache.values()) else 'completed_with_unresolved_oracles'
        results.append(out)
        p=ROOT/'benchmarks'/mode/f'{c["id"]}_{k}_{method}.json';save(p,out)
        print(c['id'],k,mode,method,len(oracle.cache),round(out['accounted_seconds'],2),flush=True)
    return results


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['trace','cold'],default='trace')
    p.add_argument('--phase',choices=['development','test'],default='development');p.add_argument('--cell')
    p.add_argument('--worker-method',choices=METHODS);p.add_argument('--opponent',choices=['F','C'])
    a=p.parse_args();design=json.loads((ROOT/'DESIGN.json').read_text());rows=[]
    if a.worker_method:
        c=next(c for c in design['cells'] if c['id']==a.cell)
        run_case(c,a.opponent,a.mode,a.worker_method);return
    for c in design['cells']:
        if a.phase not in c['phases'] or (a.cell and a.cell!=c['id']):continue
        if a.mode=='cold' and not c['mirror_solve_all']:continue
        for k in ['C','F']:
            if not all((ROOT/'runs'/c['id']/f'blue_{k}_S{m:03d}.json').exists() for m in range(2**(c['T']-1))):continue
            used=0.
            for method in METHODS:
                dest=ROOT/'benchmarks'/a.mode/f'{c["id"]}_{k}_{method}.json'
                if dest.exists():
                    out=json.loads(dest.read_text());used+=out.get('execution',{}).get('wall_seconds',0.)
                else:
                    remaining=max(0.,21600-used)
                    perf=bounded('research.experiments.v14_benchmark',
                         ['--mode',a.mode,'--cell',c['id'],'--opponent',k,'--worker-method',method],
                         remaining,ROOT/'benchmarks'/a.mode/f'{c["id"]}_{k}_{method}.log') if remaining>1 else {'reason':'instance_budget','wall_seconds':0,'tree_peak_rss_bytes':0}
                    used+=perf['wall_seconds']
                    if perf['reason']=='worker_error':raise RuntimeError('benchmark worker failed; inspect method log')
                    if dest.exists():out=json.loads(dest.read_text())
                    else:
                        progress=dest.with_name(dest.stem+'_progress.json')
                        prog=json.loads(progress.read_text()) if progress.exists() else {'values':[],'oracle_schedules':[]}
                        pay=json.loads((ROOT/'runs'/c['id']/'payoff.json').read_text());budgets=[]
                        for K in range(c['T']):
                            feasible=[v for v in prog['values'] if len(v['S'])<=K]
                            best=max(feasible,key=lambda v:v['LB']) if feasible else {'S':[],'LB':pay['minimum']}
                            budgets.append({'K':K,'S':best['S'],'LB':best['LB'],'UB':pay['maximum'],
                                            'search_status':'unresolved'})
                        out={'cell':c['id'],'opponent':k,'mode':a.mode,'method':method,'status':'unresolved',
                             'budgets':budgets,'oracle_calls':len(prog['values']),'oracle_schedules':prog['oracle_schedules'],
                             'termination':perf['reason'],'wall_seconds':perf['wall_seconds'],
                             'bound_source':'completed feasible oracle lower bounds and global maximum terminal payoff'}
                    out['execution']=perf;save(dest,out)
                rows.append({key:v for key,v in out.items() if key not in ('budgets','oracle_schedules','execution')})
    if rows:csvwrite(ROOT/'benchmarks'/f'{a.mode}_{a.phase}.csv',rows)

if __name__=='__main__':main()
