"""Phase A MC controls, with exact policy memoization and per-epoch certificates."""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
from research.formation.commitment_v12 import *
from research.formation.path_following import make_lf_game
OUT=Path('research/final_v12/audit')
KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']


def ci(values):
    d=np.asarray(values,float);rng=np.random.default_rng(12345)
    boot=d[rng.integers(0,len(d),(10000,len(d)))].mean(1)
    return float(d.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))


def control(geo,n,mode,sym,cap,tol,tag,cadences=(1,2,3,6)):
    game=make_lf_game(KD,geo,1.,1.,6);levels=GRIDS['5'];cfg=SolverConfig(cache_mode=mode,symmetry=sym,canonical=sym,max_iters=cap,rel_tol=tol)
    values={};policies={};paycache={};epochrows=[];t0=time.time()
    for h in cadences:
        vals=[];failed=0
        for seed in range(120000,120000+n):
            b,r=initial_states(game);rng=np.random.default_rng(seed);t=0;total=0.;episode=[]
            while t<6:
                sk=full_lf_state_fingerprint(game,b,r,6-t,levels)
                if sk not in policies:
                    rg=RemainingHorizonGame(game,b,r,6-t,levels,paycache,cfg)
                    sol=rg.solve();policies[sk]=(sol,rg.seqs)
                    # Bounded payoff cache; policy memoization is always full-state.
                    # Cache mode controls PAYOFF reuse, not deterministic policy reuse.
                    if len(paycache)>4096:paycache.clear()
                sol,seqs=policies[sk]
                ep={'geometry':geo,'h':h,'seed':seed,'t':t,'R':6-t,
                    **{k:sol[k] for k in ('LB','V','UB','gap','rel_gap','iteration','status')}}
                episode.append(ep)
                if not sol['converged']:
                    failed+=1;total=None;break
                ib=int(rng.choice(len(seqs),p=sol['x']));ir=int(rng.choice(len(seqs),p=sol['y']))
                run=min(h,6-t);p,q=seqs[ib,:run],seqs[ir,:run]
                total+=scalar_interval_payoff(game,b,r,p,q)
                b.extend_plan(p);r.extend_plan(q);t+=run
            epochrows.extend(episode);vals.append(total)
            if seed%25==0:print(f'{tag} {geo} h={h} {seed-120000+1}/{n} policies={len(policies)} {time.time()-t0:.1f}s',flush=True)
        values[h]=vals
        payload={'geometry':geo,'mode':mode,'symmetry':sym,'cap':cap,'tol':tol,'n':n,
                 'values':values,'epochs':epochrows,'seconds':time.time()-t0,'policy_states':len(policies),
                 'note':'Full-state policy memoization is distinct from payoff cache ablation; failures never enter means.'}
        (OUT/f'{tag}_{geo}.json').write_text(json.dumps(payload,indent=2))
    summary=[]
    for h in cadences:
        complete=all(v is not None for v in values[1]+values[h])
        row={'geometry':geo,'h':h,'mode':mode,'symmetry':sym,'cap':cap,'tol':tol,'n':n,'complete':complete}
        if complete:
            d=np.array(values[h])-values[1];mean,lo,hi=ci(d)
            row.update(C=mean,CI_lo=lo,CI_hi=hi,near_zero=abs(mean)<.25,CI_contains_zero=lo<=0<=hi)
        else:row.update(C=None,CI_lo=None,CI_hi=None,near_zero=False,CI_contains_zero=False)
        summary.append(row)
    (OUT/f'{tag}_{geo}_summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--geometry',required=True);p.add_argument('--n',type=int,default=200)
    p.add_argument('--mode',default='exact_history');p.add_argument('--ordinary',action='store_true');p.add_argument('--cap',type=int,default=200)
    p.add_argument('--tol',type=float,default=.005);p.add_argument('--tag',default='control');a=p.parse_args()
    control(a.geometry,a.n,a.mode,not a.ordinary,a.cap,a.tol,a.tag)
