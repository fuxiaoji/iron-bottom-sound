"""Perfect-recall sequence form on executed-history information sets.

Blue's current sealed action and either player's unexecuted committed suffix
are absent from the opponent's information-set ID. The deterministic LF
history observation identifies executed controls; this full public executed
history observation model is part of the finite game definition.
"""
from __future__ import annotations
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from research.formation.commitment_v12 import matrix_lp


def realization_structure(base,T,flexible):
    if not flexible:
        n=base**T
        E=sparse.csr_matrix((np.r_[1.,np.ones(n),-1.],
            (np.r_[0,np.ones(n,dtype=int),1],np.r_[0,np.arange(1,n+1),0])),shape=(2,n+1))
        e=np.array([1.,0.]);return E,e,[1]
    offsets=[];next_seq=1;row=1;rr=[0];cc=[0];dd=[1.]
    for t in range(T):
        n=base**t;offsets.append(next_seq)
        for own in range(n):
            for opp in range(n):
                parent=0 if t==0 else offsets[t-1]+((own//base)*(n//base)+opp//base)*base+own%base
                rr.append(row);cc.append(parent);dd.append(-1.)
                for a in range(base):
                    rr.append(row);cc.append(next_seq);dd.append(1.);next_seq+=1
                row+=1
    E=sparse.csr_matrix((dd,(rr,cc)),shape=(row,next_seq));e=np.zeros(row);e[0]=1.
    return E,e,offsets


def payoff_sequence_matrix(A,base,T,flexB,flexR,offB,offR,nB,nR):
    N=base**T;i=np.repeat(np.arange(N),N);j=np.tile(np.arange(N),N)
    b=1+i if not flexB else offB[-1]+((i//base)*(N//base)+j//base)*base+i%base
    r=1+j if not flexR else offR[-1]+((j//base)*(N//base)+i//base)*base+j%base
    return sparse.coo_matrix((A.ravel(),(b,r)),shape=(nB,nR)).tocsr()


def solve_sequence_form(A,base=3,T=6,structure='FC'):
    """Primal/dual LP with realization-flow feasibility and saddle gap checks."""
    if A.shape!=(base**T,base**T):raise ValueError('wrong payoff matrix')
    if structure not in ('FF','FC','CF','CC'):raise ValueError('invalid structure')
    if structure=='CF':
        s=solve_sequence_form(-A.T,base,T,'FC');s['V']=-s['V'];s['LB'],s['UB']=-s['UB'],-s['LB'];s['structure']='CF'
        s['flow_residual_B'],s['flow_residual_R']=s['flow_residual_R'],s['flow_residual_B']
        s['sequences_B'],s['sequences_R']=s['sequences_R'],s['sequences_B']
        s['infosets_B'],s['infosets_R']=s['infosets_R'],s['infosets_B']
        s['solved_via']='negative-transpose FC'
        return s
    EB,eB,offB=realization_structure(base,T,structure[0]=='F')
    ER,eR,offR=realization_structure(base,T,structure[1]=='F')
    nB=EB.shape[1];nR=ER.shape[1]
    P=payoff_sequence_matrix(A,base,T,structure[0]=='F',structure[1]=='F',offB,offR,nB,nR)
    # max eR^T u, P^T x >= ER^T u, EB x=eB, x>=0, u free.
    ub=sparse.hstack((-P.T,ER.T),format='csr')
    eq=sparse.hstack((EB,sparse.csr_matrix((EB.shape[0],ER.shape[0]))),format='csr')
    c=np.r_[np.zeros(nB),-eR]
    options={'dual_feasibility_tolerance':1e-8,'primal_feasibility_tolerance':1e-8}
    sol=linprog(c,A_ub=ub,b_ub=np.zeros(nR),A_eq=eq,b_eq=eB,
                bounds=[(0,None)]*nB+[(None,None)]*len(eR),method='highs',options=options)
    if not sol.success:raise RuntimeError('SEQUENCE_LP_FAILED: '+sol.message)
    x=sol.x[:nB];u=sol.x[nB:]
    # LP inequality dual multipliers supply opponent realization plan.
    y=-sol.ineqlin.marginals
    flowB=float(np.max(abs(EB@x-eB)));flowR=float(np.max(abs(ER@y-eR)))
    # Independently solve best responses in both full realization polytopes.
    brR=linprog(P.T@x,A_eq=ER,b_eq=eR,bounds=(0,None),method='highs',options=options)
    brB=linprog(-(P@y),A_eq=EB,b_eq=eB,bounds=(0,None),method='highs',options=options)
    if not(brR.success and brB.success):raise RuntimeError('SEQUENCE_BR_FAILED')
    lo=float(brR.fun);hi=float(-brB.fun);value=float(x@(P@y));gap=hi-lo
    violation=max(float(np.max(ER.T@u-P.T@x)),float(-x.min()),float(-y.min()),0.)
    scale=max(1.,float(np.max(abs(A))))
    if max(flowB,flowR,violation)>1e-6 or gap>1e-6*scale:raise RuntimeError('SEQUENCE_CERTIFICATE_FAILED')
    return {'V':value,'LB':lo,'UB':hi,'gap':max(0.,gap),'flow_residual_B':flowB,'flow_residual_R':flowR,
            'inequality_violation':violation,'structure':structure,'base':base,'T':T,
            'sequences_B':nB,'sequences_R':nR,'infosets_B':len(eB)-1,'infosets_R':len(eR)-1,
            'payoff_nonzeros':P.nnz,'lp_iterations':sol.nit,
            'algorithm':'sparse perfect-recall sequence-form LP with full realization best responses'}
