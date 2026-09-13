"""Certified calendar search. Monotonicity, not submodularity, drives pruning."""
from __future__ import annotations
import heapq,time
import numpy as np


def uniform(T,K):return tuple(j*T//(K+1) for j in range(1,K+1))


def branch_bound(T,K,oracle,epsilon,cheap_upper=None):
    """Max over |S|<=K using finite calendar-lattice branch and bound.

    oracle(S) returns LB,UB for the same opponent and physical game.
    cheap_upper(U) may bound ANY calendar subset of U. It is evaluated before
    solving a relaxation. Its cost and all oracle calls must be accounted for.
    """
    start=time.perf_counter();N=tuple(range(1,T));cache={};trace=[];cuts=0;counter=0
    def get(S):
        S=tuple(S)
        if S not in cache:cache[S]=oracle(S)
        return cache[S]
    best=uniform(T,K);inc=get(best)['LB'];terminal_bounds=[]
    queue=[(-float('inf'),0,(),N)]
    while queue:
        neg,c,inside,undecided=heapq.heappop(queue)
        if len(inside)>K:continue
        if -neg<=inc+epsilon:
            terminal_bounds.append(-neg);cuts+=1;continue
        allowed=tuple(sorted(inside+undecided))
        if cheap_upper is not None:
            u=float(cheap_upper(allowed))
            if u<=inc+epsilon:
                terminal_bounds.append(u);cuts+=1;continue
        else:u=float('inf')
        if len(inside)==K:
            candidates=[inside]
        elif len(allowed)<=K:
            candidates=[allowed]
        else:candidates=[]
        if candidates:
            s=tuple(sorted(candidates[0]));r=get(s)
            if r['LB']>inc:
                inc=r['LB'];best=s
            terminal_bounds.append(r['UB']);continue
        r=get(allowed);u=min(u,r['UB'])
        if u<=inc+epsilon:
            terminal_bounds.append(u);cuts+=1;continue
        next_t=undecided[0];rest=undecided[1:]
        # Both branches remain represented even if their bounds are tied.
        counter+=1;heapq.heappush(queue,(-u,counter,tuple(sorted(inside+(next_t,))),rest))
        counter+=1;heapq.heappush(queue,(-u,counter,inside,rest))
        trace.append({'expanded':counter//2,'incumbent_LB':inc,'node_UB':u,'queue_size':len(queue)})
    upper=max([inc,*terminal_bounds]);gap=max(0.,upper-inc)
    return {'K':K,'S':list(best),'LB':inc,'UB':upper,'gap':gap,
            'epsilon':epsilon,'status':'certified_numeric' if gap<=epsilon*(1+1e-8) else 'unresolved',
            'calendar_oracle_calls':len(cache),'pruned_nodes':cuts,'seconds':time.perf_counter()-start,
            'trace':trace,'oracle_schedules':[list(s) for s in cache]}


def greedy(T,K,oracle):
    S=();seen={S:oracle(S)}
    while len(S)<K:
        cand=[tuple(sorted(S+(t,))) for t in range(1,T) if t not in S]
        for c in cand:
            if c not in seen:seen[c]=oracle(c)
        S=max(cand,key=lambda c:(seen[c]['LB'],tuple(-x for x in c)))
    return {'S':list(S),**{k:seen[S][k] for k in ('V','LB','UB')},'calendar_oracle_calls':len(seen)}


def enumerate_frontier(T,values):
    rows=[]
    for K in range(T):
        available=[(s,v) for s,v in values.items() if len(s)<=K]
        best=max(available,key=lambda sv:(sv[1]['LB'],-len(sv[0]),tuple(-t for t in sv[0])))
        rows.append({'K':K,'S':list(best[0]),'LB':max(v['LB'] for s,v in available),
                     'UB':max(v['UB'] for s,v in available),
                     'V':best[1].get('V'),'selected_UB':best[1]['UB']})
    return rows


def retention_budget(frontier,rho,scale):
    zero,full=frontier[0],frontier[-1]
    if full['LB']-zero['UB']<=1e-6*scale:
        return {'rho':rho,'status':'small_or_unresolved_adaptation','K_possible':None,'K_certified':None}
    possible=[];certified=[];comparisons=[]
    for row in frontier:
        lo=row['LB']-rho*full['UB']-(1-rho)*zero['UB']
        hi=row['UB']-rho*full['LB']-(1-rho)*zero['LB']
        if hi>=0:possible.append(row['K'])
        if lo>=0:certified.append(row['K'])
        comparisons.append({'K':row['K'],'margin_LB':lo,'margin_UB':hi})
    kp=min(possible) if possible else None;kc=min(certified) if certified else None
    return {'rho':rho,'K_possible':kp,'K_certified':kc,
            'status':'certified_minimal' if kp==kc and kp is not None else 'unresolved',
            'comparisons':comparisons}
