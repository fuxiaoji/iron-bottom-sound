"""Causal LF payoff and certified finite open-loop solver for the v12 audit.

The v11 module is frozen and retained for reproduction. Open-loop DO bounds
never certify a feedback equilibrium or a receding-policy episode value.
"""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
import math
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import linprog
from research.formation.matched_horizon import LeaderState, initial_states, enumerate_sequences, state_key
from research.formation.path_following import line_ahead_offsets, RigidLineAheadGame
from research.experiments.t1_exact_discrete_certification import fire_vec

GRIDS = {'3': (-1.,0.,1.), '5':(-1.,-.5,0.,.5,1.),
         '7':(-1.,-2/3,-1/3,0.,1/3,2/3,1.)}


def angle(a):
    # Resolve binary floating-point noise at the kernel's piecewise boundaries.
    return np.round((np.asarray(a)+180.) % 360.-180., 10)


def aspect(a):
    z=np.abs(angle(a))
    return np.where((z<=30.) | (z>=150.), 'bow_stern','broadside')


def formation_snapshot(s, game):
    """Scalar independent reference at the CURRENT executed head; no future read."""
    offs=line_ahead_offsets(game.spacing,game.n_ships)
    if isinstance(game,RigidLineAheadGame):
        p=s.stations[-1]; d=p-s.stations[-2]; d=d/np.linalg.norm(d)
        return p-offs[:,None]*d, np.full(len(offs),math.degrees(math.atan2(d[1],d[0])))
    pos=[]; headings=[]
    for ell in offs:
        q=s.head-ell/s.seg
        # Integer arc-length stations have an incoming, causal heading.
        nearest=round(q)
        if abs(q-nearest)<1e-10: q=float(nearest)
        i=math.floor(q); w=q-i; j=i+s.M
        if j<1 or j>=len(s.stations): raise ValueError('insufficient LF history')
        p=s.stations[j].copy()
        if w>0:
            if j+1>=len(s.stations): raise ValueError('future station requested')
            d=s.stations[j+1]-s.stations[j]; p+=w*d
        else: d=s.stations[j]-s.stations[j-1]
        pos.append(p); headings.append(math.degrees(math.atan2(d[1],d[0])))
    return np.asarray(pos),np.asarray(headings)


def scalar_stage(game,sB,sR):
    pB,hB=formation_snapshot(sB,game);pR,hR=formation_snapshot(sR,game)
    out=0.
    for i in range(game.n_ships):
        for j in range(game.n_ships):
            dx,dy=pR[j]-pB[i];r=max(math.hypot(dx,dy),.5)
            b=math.degrees(math.atan2(dy,dx))
            db=float(angle(b-hB[i]));dr=float(angle(b+180.-hR[j]))
            out+=game.kB.fire(r,db,6,str(aspect(dr)))-game.kR.fire(r,dr,6,str(aspect(db)))
    return out


def scalar_interval_payoff(game,sB,sR,seqB,seqR,R=None):
    R=len(seqB) if R is None else R
    b=sB.clone();r=sR.clone();total=0.;prev=scalar_stage(game,b,r)
    for t in range(R):
        b.extend_plan([seqB[t]]);r.extend_plan([seqR[t]])
        cur=scalar_stage(game,b,r);total+=(prev+cur)/2;prev=cur
    return float(total)


def trajectory_batch(state,seqs,game):
    """Return causal positions/headings at all R+1 endpoints, each prefix stable."""
    seqs=np.asarray(seqs,float);n,R=seqs.shape
    hist=state.stations; nh=len(hist)
    st=np.empty((n,nh+state.n_sub*R,2));st[:,:nh]=hist
    j=nh-1
    for t in range(R):
        for _ in range(state.n_sub):
            d=st[:,j]-st[:,j-1]
            phi=np.arctan2(d[:,1],d[:,0])+np.radians(seqs[:,t]/state.n_sub)
            st[:,j+1]=st[:,j]+state.seg*np.stack((np.cos(phi),np.sin(phi)),axis=-1);j+=1
    offs=line_ahead_offsets(game.spacing,game.n_ships)
    pos=np.empty((n,R+1,len(offs),2));hd=np.empty((n,R+1,len(offs)))
    for t in range(R+1):
        head=state.head+t*state.n_sub
        if isinstance(game,RigidLineAheadGame):
            j=head+state.M;p=st[:,j];d=st[:,j]-st[:,j-1]
            d/=np.linalg.norm(d,axis=1)[:,None]
            pos[:,t]=p[:,None,:]-offs[None,:,None]*d[:,None,:]
            hd[:,t]=np.degrees(np.arctan2(d[:,1],d[:,0]))[:,None]
            continue
        for k,ell in enumerate(offs):
            q=head-ell/state.seg
            if abs(q-round(q))<1e-10:q=float(round(q))
            i=math.floor(q);w=q-i;j=i+state.M
            if j<1:raise ValueError('insufficient LF history')
            pos[:,t,k]=st[:,j]
            if w>0:
                d=st[:,j+1]-st[:,j];pos[:,t,k]+=w*d
            else:d=st[:,j]-st[:,j-1]
            hd[:,t,k]=np.degrees(np.arctan2(d[:,1],d[:,0]))
    return pos,hd


def paired_stage(game,pB,hB,pR,hR):
    shape=np.broadcast_shapes(pB.shape[:-2],pR.shape[:-2]);out=np.zeros(shape)
    for i in range(game.n_ships):
        for j in range(game.n_ships):
            dx=pR[...,j,0]-pB[...,i,0];dy=pR[...,j,1]-pB[...,i,1]
            r=np.maximum(np.hypot(dx,dy),.5);b=np.degrees(np.arctan2(dy,dx))
            db=angle(b-hB[...,i]);dr=angle(b+180.-hR[...,j])
            out+=fire_vec(game.kB,r,db,aspect(dr))-fire_vec(game.kR,r,dr,aspect(db))
    return out


def batch_interval_payoff(game,sB,sR,cands,opp,blue,R):
    cands=np.asarray(cands);opp=np.asarray(opp)[None,:]
    b=trajectory_batch(sB,cands if blue else opp,game)
    r=trajectory_batch(sR,opp if blue else cands,game)
    L=paired_stage(game,*b,*r)
    return (L[:,:-1]+L[:,1:]).sum(axis=1)/2


def kernel_key(k):
    return json.dumps({'fit':asdict(k.fit),'eta_r':k.eta_r,'eta_g':k.eta_g},sort_keys=True)


def _side_bytes(s,k):
    meta=json.dumps((s.M,s.head,s.v,s.n_sub,s.seg,s.spacing,s.n_ships),separators=(',',':'))
    return meta.encode()+np.ascontiguousarray(s.stations,dtype='<f8').tobytes()+kernel_key(k).encode()


def full_lf_state_fingerprint(game,sB,sR,R,levels):
    h=hashlib.blake2b(digest_size=32)
    for s,k in ((sB,game.kB),(sR,game.kR)):
        z=_side_bytes(s,k);h.update(len(z).to_bytes(8,'little'));h.update(z)
    h.update(json.dumps((R,tuple(levels),game.spacing,game.n_ships,type(game).__name__)).encode())
    return h.hexdigest()


def swap_game(game):
    g=copy.copy(game)
    g.kB,g.kR=game.kR,game.kB;g.vB,g.vR=game.vR,game.vB
    return g


def exchange_mirror(game,sB,sR):
    """Return action multiplier for a verified exchange isometry, else None."""
    if kernel_key(game.kB)!=kernel_key(game.kR):return None
    if (sB.v,sB.n_sub,sB.head,sB.M)!=(sR.v,sR.n_sub,sR.head,sR.M):return None
    p=sB.stations[-1];q=sR.stations[-1];d=q-p
    candidates=[(-np.eye(2),1)]
    if np.dot(d,d)>1e-16:
        unit=d/np.linalg.norm(d);candidates.append((np.eye(2)-2*np.outer(unit,unit),-1))
    for Q,m in candidates:
        if m==-1 and any(v.get('port',0)!=v.get('starboard',0) for v in game.kB.fit.kind_sector_fp.values()):continue
        translated=(sB.stations-p)@Q.T+q
        reverse=(sR.stations-q)@Q.T+p
        if np.allclose(translated,sR.stations,rtol=0,atol=1e-9) and np.allclose(reverse,sB.stations,rtol=0,atol=1e-9):return m
    return None


def canonical_orientation(game, sB, sR):
    """Choose one Euclidean/player-exchange orientation; retain exact coordinates.

    Rounded values ONLY order equivalent orientation candidates. They are not
    evaluated states or cache keys. Actual transformed coordinates remain float64.
    """
    candidates=[]
    reflection_ok=all(all(v.get('port',0)==v.get('starboard',0)
                         for v in k.fit.kind_sector_fp.values()) for k in (game.kB,game.kR))
    for swapped in (False,True):
        g=swap_game(game) if swapped else game
        b,r=(sR,sB) if swapped else (sB,sR)
        origin=b.stations[-1];ex=origin-b.stations[-2];ex=ex/np.linalg.norm(ex)
        rotation=np.array([[ex[0],ex[1]],[-ex[1],ex[0]]])
        for sign in ((1,-1) if reflection_ok else (1,)):
            Q=np.diag([1,sign])@rotation
            bb=b.clone();rr=r.clone()
            bb.stations=(b.stations-origin)@Q.T;rr.stations=(r.stations-origin)@Q.T
            key=(kernel_key(g.kB),kernel_key(g.kR),b.v,r.v,
                 tuple(np.round(rr.stations[-1],8)),
                 tuple(np.round(bb.stations[::-1].ravel(),8)),
                 tuple(np.round(rr.stations[::-1].ravel(),8)))
            candidates.append((key,g,bb,rr,swapped,sign))
    _,g,b,r,swapped,sign=min(candidates,key=lambda x:x[0])
    return g,b,r,swapped,sign


def matrix_lp(A,coupled=False):
    A=np.asarray(A,float);m,n=A.shape
    if coupled and (m!=n or np.max(np.abs(A+A.T))>1e-8):
        raise ValueError('not a skew-symmetric restricted game; projection forbidden')
    opts={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9}
    B=np.column_stack((-A.T,np.ones(n)))
    sol=linprog(np.r_[np.zeros(m),-1.],A_ub=B,b_ub=np.zeros(n),
                A_eq=[np.r_[np.ones(m),0]],b_eq=[1.],
                bounds=[(0,None)]*m+[(None,None)],method='highs',options=opts)
    if not sol.success:raise RuntimeError('LP_FAILED: '+sol.message)
    x=np.maximum(sol.x[:m],0);x/=x.sum()
    if coupled:y=x.copy()
    else:
        # Independent column LP, retained to quantify equilibrium selection.
        solR=linprog(np.r_[np.zeros(n),1.],A_ub=np.column_stack((A,-np.ones(m))),
                     b_ub=np.zeros(m),A_eq=[np.r_[np.ones(n),0]],b_eq=[1.],
                     bounds=[(0,None)]*n+[(None,None)],method='highs',options=opts)
        if not solR.success:raise RuntimeError('LP_FAILED: '+solR.message)
        y=np.maximum(solR.x[:n],0);y/=y.sum()
    lo=float(np.min(x@A));hi=float(np.max(A@y))
    if hi-lo>1e-6*max(1,np.max(np.abs(A))):raise RuntimeError('LP certificate failure')
    return {'V':float(x@A@y),'x':x,'y':y,'LB':lo,'UB':hi,'gap':max(0.,hi-lo)}


@dataclass
class SolverConfig:
    cache_mode:str='exact_history'
    symmetry:bool=True
    canonical:bool=True
    max_iters:int=200
    rel_tol:float=.005
    abs_tol:float=.1


class RemainingHorizonGame:
    def __init__(self,game,sB,sR,R,levels,cache=None,config=None):
        self.game=game;self.sB=sB.clone();self.sR=sR.clone();self.R=R;self.levels=tuple(levels)
        self.seqs=enumerate_sequences(levels,R);self.n=len(self.seqs)
        self.cache={} if cache is None else cache;self.config=config or SolverConfig()
        if self.config.cache_mode not in ('off','exact_history','old_pose_key'):raise ValueError('invalid cache mode')
        self.sk=state_key(sB,sR) if self.config.cache_mode=='old_pose_key' else full_lf_state_fingerprint(game,sB,sR,R,levels)
        self.hits=0;self.misses=0
        self.local_matrix_vectors={}
        self._trajB=None;self._trajR=None

    def _vector(self,index,blue):
        key=(self.sk,self.R,self.levels,'col' if blue else 'row',index)
        if self.config.cache_mode!='off' and key in self.cache:
            self.hits+=1;return self.cache[key]
        if self.config.cache_mode=='off' and (index,blue) in self.local_matrix_vectors:
            return self.local_matrix_vectors[index,blue]
        self.misses+=1
        if self._trajB is None:
            self._trajB=trajectory_batch(self.sB,self.seqs,self.game)
            self._trajR=trajectory_batch(self.sR,self.seqs,self.game)
        b=self._trajB if blue else tuple(a[index:index+1] for a in self._trajB)
        r=tuple(a[index:index+1] for a in self._trajR) if blue else self._trajR
        L=paired_stage(self.game,*b,*r);v=(L[:,:-1]+L[:,1:]).sum(axis=1)/2
        if self.config.cache_mode!='off':self.cache[key]=v
        else:self.local_matrix_vectors[index,blue]=v
        return v

    def _columns(self,j):return self._vector(j,True)
    def _rows(self,i):return self._vector(i,False)

    def solve(self):
        c=self.config
        if c.canonical:
            game,b,r,swapped,sign=canonical_orientation(self.game,self.sB,self.sR)
            cfg=copy.copy(c);cfg.canonical=False
            other=RemainingHorizonGame(game,b,r,self.R,self.levels,self.cache,cfg)
            s=other.solve()
            if sign==-1:
                s['x']=s['x'][::-1].copy();s['y']=s['y'][::-1].copy()
            if swapped:
                s['x'],s['y']=s['y'],s['x'];s['V']=-s['V'];s['LB'],s['UB']=-s['UB'],-s['LB']
                for row in s['trace']:
                    row['V']=-row['V'];row['LB'],row['UB']=-row['UB'],-row['LB']
            s['canonical_swapped']=swapped;s['canonical_action_sign']=sign
            return s
        mirror=exchange_mirror(self.game,self.sB,self.sR) if c.symmetry else None
        perm=np.arange(self.n) if mirror!= -1 else np.arange(self.n-1,-1,-1)
        X=sorted(set(int(np.argmin(abs(self.seqs-a*60).sum(axis=1))) for a in self.levels))
        Y=X.copy();trace=[]
        for it in range(1,c.max_iters+1):
            actualY=perm[Y] if mirror is not None else np.asarray(Y)
            pay=np.column_stack([self._columns(int(j))[X] for j in actualY])
            sol=matrix_lp(pay,coupled=mirror is not None)
            x=np.zeros(self.n);y=np.zeros(self.n);x[X]=sol['x'];y[actualY]=sol['y']
            er=sum(x[i]*self._rows(int(i)) for i in np.flatnonzero(x))
            eb=sum(y[j]*self._columns(int(j)) for j in np.flatnonzero(y))
            hi=float(np.max(eb));lo=float(np.min(er))
            imin=int(np.flatnonzero(eb>=hi-1e-10)[0]);jmin=int(np.flatnonzero(er<=lo+1e-10)[0])
            gap=max(0.,hi-lo);v=sol['V'];target=min(c.abs_tol,c.rel_tol*max(1.,abs(v)))
            trace.append({'iteration':it,'LB':lo,'V':v,'UB':hi,'gap':gap,'rel_gap':gap/max(1.,abs(v)),
                          'n_X':len(X),'n_Y':len(Y),'target':target})
            if gap<=target:break
            if mirror is not None:
                enlarged=sorted(set(X+[imin,int(perm[jmin])]))
                if enlarged==X:break
                X=enlarged;Y=X.copy()
            else:
                xn=sorted(set(X+[imin]));yn=sorted(set(Y+[jmin]))
                if xn==X and yn==Y:break
                X,Y=xn,yn
        converged=gap<=target
        return {**trace[-1],'x':x,'y':y,'converged':converged,
                'status':'CONVERGED' if converged else 'SOLVER_NOT_CONVERGED','trace':trace,
                'symmetry_mirror':mirror,'canonical_swapped':False,
                'cache_hits':self.hits,'cache_misses':self.misses,
                'support_B':int(np.count_nonzero(x)),'support_R':int(np.count_nonzero(y))}


def run_cadence(game,sB0,sR0,h,T,levels,cache,rng,config=None):
    b=sB0.clone();r=sR0.clone();total=0.;t=0;epochs=[]
    while t<T:
        rg=RemainingHorizonGame(game,b,r,T-t,levels,cache,config);sol=rg.solve()
        ep={k:v for k,v in sol.items() if k not in ('x','y','trace')};ep.update(t=t,R=T-t)
        epochs.append(ep)
        if not sol['converged']:
            return {'J':None,'epochs':epochs,'status':'SOLVER_NOT_CONVERGED','final_B':b,'final_R':r}
        ib=int(rng.choice(rg.n,p=sol['x']));ir=int(rng.choice(rg.n,p=sol['y']))
        run=min(h,T-t);pb=rg.seqs[ib,:run];pr=rg.seqs[ir,:run]
        total+=scalar_interval_payoff(game,b,r,pb,pr)
        b.extend_plan(pb);r.extend_plan(pr);t+=run
    return {'J':total,'epochs':epochs,'status':'CONVERGED','final_B':b,'final_R':r,
            'local_open_loop_gap_sum':sum(e['gap'] for e in epochs)}
