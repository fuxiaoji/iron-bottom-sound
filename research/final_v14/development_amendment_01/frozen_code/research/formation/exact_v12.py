"""Independent full finite-tree backward induction (no DO, no Monte Carlo)."""
from __future__ import annotations
import itertools,time
import numpy as np
from research.formation.commitment_v12 import trajectory_batch,paired_stage,initial_states,enumerate_sequences,matrix_lp,GRIDS


def terminal_payoff_matrix(game,levels=GRIDS['3'],T=6,chunk=96):
    """All complete history pairs; causal trajectories and full prefix payoffs."""
    seqs=enumerate_sequences(levels,T);b,r=initial_states(game)
    pb,hb=trajectory_batch(b,seqs,game);pr,hr=trajectory_batch(r,seqs,game)
    n=len(seqs);A=np.empty((n,n))
    for i in range(0,n,chunk):
        L=paired_stage(game,pb[i:i+chunk,None],hb[i:i+chunk,None],pr[None],hr[None])
        A[i:i+chunk]=(L[...,:-1]+L[...,1:]).sum(-1)/2
    return A


def values_3x3(mats,tol=1e-8):
    """Batched support enumeration, with full saddle certificates and LP fallback.

    Candidate supports are hypotheses, not assumed equilibria. Each accepted
    candidate is checked against ALL actions. Singular/degenerate cases go
    through the independent general LP if no certified candidate was found.
    """
    A=np.asarray(mats,float);N=len(A);vals=np.full(N,np.nan);gaps=np.zeros(N)
    lows=A.min(2).max(1);highs=A.max(1).min(1)
    pure=highs-lows<=tol;vals[pure]=(lows[pure]+highs[pure])/2;gaps[pure]=highs[pure]-lows[pure]
    for k in (2,3):
        for I in itertools.combinations(range(3),k):
            for J in itertools.combinations(range(3),k):
                ids=np.flatnonzero(np.isnan(vals))
                if not len(ids):return vals,gaps,0
                sub=A[ids][:,I][:,:,J]
                # Solve augmented linear systems for p, q, and support value.
                C=np.zeros((len(ids),k+1,k+1));C[:,:k,:k]=sub
                C[:,:k,k]=-1.;C[:,k,:k]=1.
                nonsingular=np.abs(np.linalg.det(C))>1e-12
                ids=ids[nonsingular];C=C[nonsingular];sub=sub[nonsingular]
                if not len(ids):continue
                rhs=np.zeros((len(ids),k+1,1));rhs[:,k]=1.
                q=np.linalg.solve(C,rhs)[:,:k,0]
                C[:,:k,:k]=sub.transpose(0,2,1)
                p=np.linalg.solve(C,rhs)[:,:k,0]
                nonneg=(p.min(1)>=-1e-10)&(q.min(1)>=-1e-10)
                ids=ids[nonneg];p=p[nonneg];q=q[nonneg]
                if not len(ids):continue
                p=np.maximum(p,0);p/=p.sum(1)[:,None];q=np.maximum(q,0);q/=q.sum(1)[:,None]
                fullp=np.zeros((len(ids),3));fullq=fullp.copy();fullp[:,I]=p;fullq[:,J]=q
                lb=np.einsum('bi,bij->bj',fullp,A[ids]).min(1)
                ub=np.einsum('bij,bj->bi',A[ids],fullq).max(1)
                ok=ub-lb<=tol;ix=ids[ok];vals[ix]=(lb[ok]+ub[ok])/2;gaps[ix]=np.maximum(0,ub[ok]-lb[ok])
    remaining=np.flatnonzero(np.isnan(vals))
    for ix in remaining:
        s=matrix_lp(A[ix]);vals[ix]=s['V'];gaps[ix]=s['gap']
    return vals,gaps,len(remaining)


def backward_induction(A,base=3,T=6,h=1):
    """Public executed-history block game, preserving simultaneous sealed blocks.

    Leaf entries already contain total rewards. At a fixed prefix its past
    payoff is a common constant, so minimax reduction of total rewards equals
    the Bellman reward-plus-continuation recursion without double counting.
    """
    if A.shape!=(base**T,base**T):raise ValueError('wrong terminal matrix shape')
    boundaries=list(range(0,T,h))+[T];current=A.copy();trace=[];error=0.
    for t0,t1 in reversed(list(zip(boundaries[:-1],boundaries[1:]))):
        n=base**t0;block=base**(t1-t0)
        mats=current.reshape(n,block,n,block).transpose(0,2,1,3).reshape(n*n,block,block)
        start=time.perf_counter()
        if block==3:vals,gaps,fallback=values_3x3(mats)
        else:
            vals=np.empty(n*n);gaps=np.empty(n*n);fallback=n*n
            for i,Ai in enumerate(mats):
                s=matrix_lp(Ai);vals[i]=s['V'];gaps[i]=s['gap']
        maxgap=float(np.max(gaps));error+=maxgap
        trace.append({'t_start':t0,'t_end':t1,'nodes':n*n,'matrix_order':block,
                      'max_local_duality_gap':maxgap,'lp_calls':fallback,'seconds':time.perf_counter()-start})
        current=vals.reshape(n,n)
    value=float(current[0,0])
    return {'V':value,'numeric_error_budget':error,'LB':value-error,'UB':value+error,
            'trace':trace,'algorithm':'complete backward induction','T':T,'h':h,'base':base,
            'leaves':base**(2*T),'certification_scope':'finite game, floating-point payoff evaluation and LP precision'}
