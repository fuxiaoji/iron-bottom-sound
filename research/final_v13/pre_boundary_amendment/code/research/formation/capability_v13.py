"""Exact small-horizon nested per-turn speed capability experiment.

Full public executed actions (speed and turn) with hidden current/suffix
actions; variable arc-length LF sampling and rectangular sequence form.
"""
import itertools
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from research.formation.commitment_v12 import initial_states,paired_stage,matrix_lp

def sequences(base,T):return np.array(list(itertools.product(range(base),repeat=T)),dtype=int)
def action_menu(speeds):return np.array([(6.*v,turn) for v in speeds for turn in (-60.,0.,60.)])

def variable_trajectories(state,actions,game):
    n,T,_=actions.shape;nh=len(state.stations);sub=state.n_sub
    st=np.empty((n,nh+sub*T,2));arc=np.empty((n,nh+sub*T));st[:,:nh]=state.stations
    arc[:,:nh]=np.arange(nh)*state.seg;j=nh-1
    for t in range(T):
        for _ in range(sub):
            d=st[:,j]-st[:,j-1];phi=np.arctan2(d[:,1],d[:,0])+np.radians(actions[:,t,1]/sub)
            ds=actions[:,t,0]/sub
            st[:,j+1]=st[:,j]+ds[:,None]*np.column_stack((np.cos(phi),np.sin(phi)))
            arc[:,j+1]=arc[:,j]+ds;j+=1
    P=np.empty((n,T+1,game.n_ships,2));H=np.empty((n,T+1,game.n_ships));row=np.arange(n)
    for t in range(T+1):
        end=nh-1+t*sub
        for k in range(game.n_ships):
            target=arc[:,end]-k*game.spacing
            ix=np.sum(arc[:,:end+1]<=target[:,None]+1e-10,axis=1)-1
            if np.any(ix<1):raise ValueError('insufficient initial arc history')
            frac=target-arc[row,ix];jp=np.minimum(ix+1,end);den=arc[row,jp]-arc[row,ix]
            w=np.where(den>1e-12,frac/np.maximum(den,1e-12),0.)
            interior=frac>1e-10
            d=np.where(interior[:,None],st[row,jp]-st[row,ix],st[row,ix]-st[row,ix-1])
            P[:,t,k]=st[row,ix]+np.where(interior,w,0.)[:,None]*(st[row,jp]-st[row,ix])
            H[:,t,k]=np.degrees(np.arctan2(d[:,1],d[:,0]))
    return P,H

def terminal_matrix(game,speedsB,speedsR,T,chunk=96):
    b,r=initial_states(game);mb=action_menu(speedsB);mr=action_menu(speedsR)
    pb,hb=variable_trajectories(b,mb[sequences(len(mb),T)],game)
    pr,hr=variable_trajectories(r,mr[sequences(len(mr),T)],game)
    A=np.empty((len(pb),len(pr)))
    for i in range(0,len(pb),chunk):
        L=paired_stage(game,pb[i:i+chunk,None],hb[i:i+chunk,None],pr[None],hr[None]);A[i:i+chunk]=(L[...,:-1]+L[...,1:]).sum(-1)/2
    return A

def flow(own,opp,T,flex):
    if not flex:
        N=own**T;E=sparse.csr_matrix((np.r_[1.,-1.,np.ones(N)],
            (np.r_[0,1,np.ones(N,dtype=int)],np.r_[0,0,np.arange(1,N+1)])),shape=(2,N+1))
        return E,np.array([1.,0.]),[1]
    rr=[0];cc=[0];dd=[1.];offsets=[];seq=1;ir=1
    for t in range(T):
        no=own**t;np_=opp**t;offsets.append(seq)
        for i in range(no):
            for j in range(np_):
                parent=0 if t==0 else offsets[t-1]+((i//own)*(np_//opp)+j//opp)*own+i%own
                rr.append(ir);cc.append(parent);dd.append(-1.)
                for a in range(own):rr.append(ir);cc.append(seq);dd.append(1.);seq+=1
                ir+=1
    E=sparse.csr_matrix((dd,(rr,cc)),shape=(ir,seq));e=np.zeros(ir);e[0]=1.;return E,e,offsets

def sequence_value(A,b,r,T,structure):
    if A.shape!=(b**T,r**T):raise ValueError('rectangular terminal matrix shape')
    eb,bb,ob=flow(b,r,T,structure[0]=='F');er,br,orr=flow(r,b,T,structure[1]=='F')
    nb,nr=eb.shape[1],er.shape[1];I=np.repeat(np.arange(b**T),r**T);J=np.tile(np.arange(r**T),b**T)
    B=1+I if structure[0]=='C' else ob[-1]+((I//b)*(r**(T-1))+J//r)*b+I%b
    R=1+J if structure[1]=='C' else orr[-1]+((J//r)*(b**(T-1))+I//b)*r+J%r
    P=sparse.coo_matrix((A.ravel(),(B,R)),shape=(nb,nr)).tocsr()
    opts={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9}
    sol=linprog(np.r_[np.zeros(nb),-br],A_ub=sparse.hstack((-P.T,er.T),format='csr'),b_ub=np.zeros(nr),
       A_eq=sparse.hstack((eb,sparse.csr_matrix((len(bb),len(br)))),format='csr'),b_eq=bb,
       bounds=[(0,None)]*nb+[(None,None)]*len(br),method='highs',options=opts)
    if not sol.success:raise RuntimeError(sol.message)
    x=sol.x[:nb];y=-sol.ineqlin.marginals
    lb=linprog(P.T@x,A_eq=er,b_eq=br,bounds=(0,None),method='highs',options=opts)
    ub=linprog(-P@y,A_eq=eb,b_eq=bb,bounds=(0,None),method='highs',options=opts)
    if not(lb.success and ub.success):raise RuntimeError('full rectangular best response failed')
    lo=float(lb.fun);hi=float(-ub.fun);val=float(x@(P@y))
    residual=max(float(abs(eb@x-bb).max()),float(abs(er@y-br).max()),float(-x.min()),float(-y.min()),
                 float(np.max(er.T@sol.x[nb:]-P.T@x)),0.)
    if residual>1e-6 or hi-lo>1e-6:raise RuntimeError('rectangular sequence certificate failed')
    return {'V':val,'LB':lo,'UB':hi,'gap':max(0.,hi-lo),'flow_inequality_residual':residual,
      'base_B':b,'base_R':r,'T':T,'structure':structure,'sequences_B':nb,'sequences_R':nr,
      'infosets_B':len(bb)-1,'infosets_R':len(br)-1,'algorithm':'complete rectangular sequence-form LP and full best responses'}

def flexible_value(A,b,r,T):
    if A.shape!=(b**T,r**T):raise ValueError('wrong shape')
    current=A.copy();error=0.;trace=[]
    for t in reversed(range(T)):
        nb=b**t;nr=r**t;mats=current.reshape(nb,b,nr,r).transpose(0,2,1,3).reshape(nb*nr,b,r)
        lower=mats.min(2).max(1);upper=mats.max(1).min(1);gap=upper-lower
        pure=gap<=1e-9;values=(lower+upper)/2;gaps=np.where(pure,gap,0.)
        ids=np.flatnonzero(~pure)
        for i in ids:s=matrix_lp(mats[i]);values[i]=s['V'];gaps[i]=s['gap']
        error+=float(gaps.max());current=values.reshape(nb,nr)
        trace.append({'t':t,'nodes':len(mats),'mixed_lp_nodes':len(ids),'max_gap':float(gaps.max())})
    v=float(current[0,0]);return {'V':v,'LB':v-error,'UB':v+error,'numeric_error_budget':error,'T':T,'trace':trace,'algorithm':'complete rectangular backward induction'}

def negate_plan_permutation(nspeeds,T):
    base=3*nspeeds;s=sequences(base,T);mapped=3*(s//3)+2-s%3
    return mapped@(base**np.arange(T-1,-1,-1))
