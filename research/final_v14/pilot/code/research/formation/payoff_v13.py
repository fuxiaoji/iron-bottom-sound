"""v13-only sector-boundary numerical completion; frozen v12 is untouched.

At the fixed directional-sector boundaries, snap angular discrepancies within
1e-8 degrees to the boundary. Both scalar and vector paths share this rule.
This prevents near-contact coordinate roundoff selecting different sectors
under reflection. All pre-fix v13 outputs are archived and recomputed.
"""
import math
import numpy as np
from research.formation.commitment_v12 import trajectory_batch,formation_snapshot,initial_states,enumerate_sequences,GRIDS
from research.experiments.t1_exact_discrete_certification import fire_vec

BOUNDARY_TOL_DEG=1e-8
def angle(a):
    z=np.round((np.asarray(a)+180.)%360.-180.,10)
    for boundary in (-150.,-30.,30.,150.):z=np.where(abs(z-boundary)<=BOUNDARY_TOL_DEG,boundary,z)
    return z

def aspect(a):
    z=np.abs(angle(a));return np.where((z<=30.)|(z>=150.),'bow_stern','broadside')

def paired_stage(game,pB,hB,pR,hR):
    shape=np.broadcast_shapes(pB.shape[:-2],pR.shape[:-2]);out=np.zeros(shape)
    for i in range(game.n_ships):
        for j in range(game.n_ships):
            dx=pR[...,j,0]-pB[...,i,0];dy=pR[...,j,1]-pB[...,i,1]
            r=np.maximum(np.hypot(dx,dy),.5);b=np.degrees(np.arctan2(dy,dx))
            db=angle(b-hB[...,i]);dr=angle(b+180.-hR[...,j])
            out+=fire_vec(game.kB,r,db,aspect(dr))-fire_vec(game.kR,r,dr,aspect(db))
    return out

def scalar_stage(game,sB,sR):
    pB,hB=formation_snapshot(sB,game);pR,hR=formation_snapshot(sR,game);total=0.
    for i in range(game.n_ships):
        for j in range(game.n_ships):
            dx,dy=pR[j]-pB[i];r=max(math.hypot(dx,dy),.5);b=math.degrees(math.atan2(dy,dx))
            db=float(angle(b-hB[i]));dr=float(angle(b+180.-hR[j]))
            total+=game.kB.fire(r,db,6,str(aspect(dr)))-game.kR.fire(r,dr,6,str(aspect(db)))
    return total

def scalar_interval_payoff(game,b,r,seqB,seqR):
    b=b.clone();r=r.clone();prior=scalar_stage(game,b,r);value=0.
    for u,v in zip(seqB,seqR):
        b.extend_plan([u]);r.extend_plan([v]);cur=scalar_stage(game,b,r);value+=(prior+cur)/2;prior=cur
    return value

def terminal_payoff_matrix(game,levels=GRIDS['3'],T=6,chunk=96):
    seq=enumerate_sequences(levels,T);b,r=initial_states(game);pb,hb=trajectory_batch(b,seq,game);pr,hr=trajectory_batch(r,seq,game)
    A=np.empty((len(seq),len(seq)))
    for i in range(0,len(seq),chunk):
        L=paired_stage(game,pb[i:i+chunk,None],hb[i:i+chunk,None],pr[None],hr[None]);A[i:i+chunk]=(L[...,:-1]+L[...,1:]).sum(-1)/2
    return A
