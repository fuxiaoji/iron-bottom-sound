"""Calendar-feasible policy reconstruction and full-response certificates."""
import numpy as np
from research.formation.schedule_v14 import build_flow,repair_flow,calendar
from research.formation.pricing_v14 import conditional_matrix,price


def behavior(flow,x):
    out={}
    for t,end,offset,row in flow.blocks:
        ninfo,na=(flow.own*flow.opp)**t,flow.own**(end-t)
        children=np.maximum(x[offset:offset+ninfo*na].reshape(ninfo,na),0.)
        total=children.sum(1)
        out[t]=np.divide(children,total[:,None],out=np.full_like(children,1./na),where=total[:,None]>0)
    return out


def from_behavior(flow,beh):
    seed=np.zeros(flow.E.shape[1]);seed[0]=1.
    for t,end,offset,row in flow.blocks:
        probabilities=beh[t]
        n=(flow.own*flow.opp)**t*flow.own**(end-t)
        seed[offset:offset+n]=probabilities.ravel()
    return repair_flow(seed,flow)


def conditional_flow(flow,x):
    n=flow.own**flow.T;m=flow.opp**flow.T
    out=x[flow.terminal_ids(np.arange(n)[:,None],np.arange(m)[None,:])]
    if np.min(out)<-1e-10 or np.max(abs(out.sum(0)-1))>1e-7:
        raise RuntimeError('invalid realization conditional distribution')
    return out


def conditional_saved(policy,base,T,S):
    if 'representation' in policy and str(policy['representation'])=='sequence_form':
        return conditional_flow(build_flow(base,base,T,S),policy['x'])
    return conditional_matrix(policy,base**T)


def full_flow(policy,base,T):
    S=tuple(range(1,T));F=build_flow(base,base,T,S)
    if 'representation' in policy and str(policy['representation'])=='sequence_form':
        if tuple(policy['S'])!=S:raise ValueError('source must update every epoch')
        return F,policy['x']
    C=conditional_matrix(policy,base**T);beh={}
    for t,end,offset,row in F.blocks:
        # Fix arbitrary unseen opponent continuation to zeros, and marginalize
        # own future controls. Causality makes this choice irrelevant.
        op=np.arange(base**t)*base**(T-t)
        marginal=C[:,op].reshape(base**(t+1),base**(T-t-1),base**t).sum(1)
        child=marginal.reshape(base**t,base,base**t).transpose(0,2,1).reshape((base*base)**t,base)
        denom=child.sum(1)
        beh[t]=np.divide(child,denom[:,None],out=np.full_like(child,1/base),where=denom[:,None]>0)
    return F,from_behavior(F,beh)


def coarsen_full_behavior(policy,base,T,target_S):
    """Shadow continuation of source behavior; legal actual own prefix retained.

    At each coarse update, follow the source's conditional action kernels along
    the hypothetical straight opponent continuation. This defines an exact
    block distribution, including source-zero-reach histories by uniform play.
    No sampled approximation or hidden future input is used.
    """
    F,x=full_flow(policy,base,T);source=behavior(F,x)
    target=build_flow(base,base,T,target_S);beh={}
    straight=base//2
    for t,end,offset,row in target.blocks:
        na=base**(end-t);ni=base**t
        own=np.repeat(np.arange(ni),ni)[:,None]
        opp=np.tile(np.arange(ni),ni)[:,None]
        actions=np.arange(na)[None,:];prob=np.ones((ni*ni,na))
        for u in range(t,end):
            own_pref=own*base**(u-t)+actions//base**(end-u)
            delta=u-t
            ref=straight*(base**delta-1)//(base-1) if base>1 else 0
            opp_pref=opp*base**delta+ref
            a=(actions//base**(end-u-1))%base
            prob*=source[u][own_pref*base**u+opp_pref,a]
        if np.max(abs(prob.sum(1)-1))>1e-8:raise RuntimeError('coarsened block does not sum to one')
        beh[t]=prob
    tx=from_behavior(target,beh)
    return target,tx


def certify_coarsening(A,source_upper,policy,base,T,target_S,opponent='C'):
    flow,x=coarsen_full_behavior(policy,base,T,target_S)
    P=conditional_flow(flow,x);sr=tuple(range(1,T)) if opponent=='F' else ()
    red_value,_,red_map=price(-A.T*P.T,np.ones(base**T),base,T,sr)
    padding=1e-8*max(1.,float(np.max(abs(A))))
    lower=-red_value-padding
    return {'S':list(target_S),'lower_value':lower,'source_upper':source_upper,
            'loss_upper':source_upper-lower,'opponent':opponent,
            'construction':'exact block distribution from full source behavior and hypothetical straight opponent continuation'},(flow,x,red_map)
