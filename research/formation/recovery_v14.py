"""Recover causal full-update policies without a monolithic equilibrium LP.

Each accepted 3x3 support is checked against all actions. This extends the
archived value-only batched solver by retaining actual behavioral policies;
singular and degenerate cases use the general matrix-game LP.
"""
import itertools
import time
import numpy as np
from research.formation.commitment_v12 import matrix_lp
from research.formation.schedule_v14 import build_flow
from research.formation.policy_v14 import from_behavior,conditional_flow
from research.formation.pricing_v14 import price,hybrid


def matrix_policies(mats):
    A=np.asarray(mats,float);N,b,_=A.shape
    P=np.zeros((N,b));Q=np.zeros((N,b));done=np.zeros(N,bool)
    tol=1e-9*max(1.,float(np.max(abs(A))))
    if b==3:
        i=A.min(2).argmax(1);j=A.max(1).argmin(1)
        lo=A[np.arange(N),i].min(1);hi=A[np.arange(N),:,j].max(1)
        good=hi-lo<=tol;idx=np.flatnonzero(good)
        P[idx,i[idx]]=1.;Q[idx,j[idx]]=1.;done[idx]=True
        for k in (2,3):
          for I in itertools.combinations(range(3),k):
            for J in itertools.combinations(range(3),k):
                ids=np.flatnonzero(~done)
                if not len(ids):break
                sub=A[ids][:,I][:,:,J]
                C=np.zeros((len(ids),k+1,k+1));C[:,:k,:k]=sub
                C[:,:k,k]=-1.;C[:,k,:k]=1.
                valid=abs(np.linalg.det(C))>1e-12
                ids,C,sub=ids[valid],C[valid],sub[valid]
                if not len(ids):continue
                rhs=np.zeros((len(ids),k+1,1));rhs[:,k]=1.
                q=np.linalg.solve(C,rhs)[:,:k,0]
                C[:,:k,:k]=sub.transpose(0,2,1)
                p=np.linalg.solve(C,rhs)[:,:k,0]
                valid=(p.min(1)>=-1e-10)&(q.min(1)>=-1e-10)
                ids,p,q=ids[valid],p[valid],q[valid]
                if not len(ids):continue
                p=np.maximum(p,0);p/=p.sum(1)[:,None]
                q=np.maximum(q,0);q/=q.sum(1)[:,None]
                fp=np.zeros((len(ids),3));fq=fp.copy();fp[:,I]=p;fq[:,J]=q
                lo=np.einsum('ni,nij->nj',fp,A[ids]).min(1)
                hi=np.einsum('nij,nj->ni',A[ids],fq).max(1)
                good=hi-lo<=tol;ix=ids[good]
                P[ix]=fp[good];Q[ix]=fq[good];done[ix]=True
    fallback=int(np.sum(~done))
    for i in np.flatnonzero(~done):
        r=matrix_lp(A[i]);P[i]=r['x'];Q[i]=r['y']
    lo=np.einsum('ni,nij->nj',P,A).min(1)
    hi=np.einsum('nij,nj->ni',A,Q).max(1)
    value=np.einsum('ni,nij,nj->n',P,A,Q)
    if np.max(hi-lo)>1e-6*max(1.,float(np.max(abs(A)))):
        raise RuntimeError('recovered local policy gap exceeds tolerance')
    return value,P,Q,hi-lo,fallback


def full_update_policies(A,base,T):
    tick=time.perf_counter();current=np.asarray(A).copy();blue={};red={};trace=[]
    for t in reversed(range(T)):
        n=base**t
        mats=current.reshape(n,base,n,base).transpose(0,2,1,3).reshape(n*n,base,base)
        values,p,q,gaps,lp=matrix_policies(mats)
        blue[t]=p;red[t]=q.reshape(n,n,base).transpose(1,0,2).reshape(n*n,base)
        trace.append({'t':t,'subgames':n*n,'max_local_gap':float(max(gaps)),'lp_fallback':lp})
        current=values.reshape(n,n)
    S=tuple(range(1,T));flow=build_flow(base,base,T,S)
    x=from_behavior(flow,blue);y=from_behavior(flow,red)
    CB=conditional_flow(flow,x);CR=conditional_flow(flow,y)
    upper=price(A*CR.T,np.ones(base**T),base,T,S)[0]
    lower=-price(-A.T*CB.T,np.ones(base**T),base,T,S)[0]
    pad=1e-8*max(1.,float(np.max(abs(A))))
    r={'V':float(current[0,0]),'LB':lower-pad,'UB':upper+pad,'gap':upper-lower+2*pad,
       'trace':trace,'seconds':time.perf_counter()-tick,'S':list(S),
       'flow_residual':max(float(np.max(abs(flow.E@x-flow.e))),float(np.max(abs(flow.E@y-flow.e)))),
       'certification_scope':'recovered feasible full-update policies and independent exact causal best responses; floating point'}
    r['status']='certified_numeric' if r['gap']<=1e-6*max(1.,float(np.max(abs(A)))) else 'unresolved'
    saved={'representation':np.array('sequence_form'),'x':x,'y':y,'S':np.array(S,dtype=int),'S_R':np.array(S,dtype=int)}
    return r,saved


def calendar_against_f(A,base,T,S,upper):
    """Recover the maximizer at its common boundaries with an F opponent.

    Inside each block the maximizer commits. The inverted local game has a
    committed minimizing player, whose complete-path distribution is exactly
    the required block distribution. Every executed prefix is kept separate.
    """
    tick=time.perf_counter();current=np.asarray(A).copy();beh={};trace=[]
    bounds=(0,)+tuple(S)+(T,)
    for t,end in reversed(list(zip(bounds[:-1],bounds[1:]))):
        n,m=base**t,base**(end-t)
        mats=current.reshape(n,m,n,m).transpose(0,2,1,3).reshape(n*n,m,m)
        if m==3:
            values,p,q,gaps,fallback=matrix_policies(mats);beh[t]=p
        else:
            values=np.empty(n*n);p=np.empty((n*n,m));fallback=n*n
            for i,sub in enumerate(mats):
                r,policy=hybrid(-sub.T,base,end-t,tuple(range(1,end-t)),return_strategies=True)
                values[i]=-r['V']
                p[i]=policy['y'][1:] if 'representation' in policy else policy['q']
            beh[t]=p
        trace.append({'t':t,'end':end,'subgames':n*n,'local_games_solved':fallback})
        current=values.reshape(n,n)
    flow=build_flow(base,base,T,S);x=from_behavior(flow,beh)
    C=conditional_flow(flow,x)
    lower=-price(-A.T*C.T,np.ones(base**T),base,T,tuple(range(1,T)))[0]
    pad=1e-8*max(1.,float(np.max(abs(A))))
    if lower-pad>upper+1e-7*max(1.,float(np.max(abs(A)))):
        raise RuntimeError('recovered policy exceeds independent value upper bound')
    r={'V':float(current[0,0]),'LB':lower-pad,'UB':upper,'gap':upper-lower+pad,
       'S':list(S),'trace':trace,'seconds':time.perf_counter()-tick,
       'flow_residual':float(np.max(abs(flow.E@x-flow.e))),
       'certification_scope':'feasible recovered calendar policy full-response lower bound and independent enumeration upper bound'}
    r['status']='certified_numeric' if r['gap']<=1e-6*max(1.,float(np.max(abs(A)))) else 'unresolved'
    return r,{'representation':np.array('sequence_form'),'x':x,'S':np.array(S,dtype=int)}
