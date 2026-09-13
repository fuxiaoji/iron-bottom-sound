"""Frozen favorable-set diagnostic on a declared reduced relative-state domain."""
import numpy as np
from scipy.spatial import cKDTree
from research.formation.commitment_v12 import formation_snapshot,paired_stage,angle

EPS=1e-9;ANGULAR_LENGTH=4.

def embedding(z):
    z=np.atleast_2d(z);a=np.radians(z[:,2])
    return np.column_stack((z[:,:2],ANGULAR_LENGTH*np.cos(a),ANGULAR_LENGTH*np.sin(a)))

def domain():
    x,y=np.meshgrid(np.arange(-24.,25.,2),np.arange(-24.,25.,2),indexing='ij')
    xy=np.column_stack((x.ravel(),y.ravel()));r=np.linalg.norm(xy,axis=1);xy=xy[(r>=1)&(r<=24)]
    return np.column_stack((np.repeat(xy,12,axis=0),np.tile(np.arange(0.,360.,30),len(xy))))

def field(game,b,opponent,Z):
    pb,hb=formation_snapshot(b,game);pr,hr=formation_snapshot(opponent,game)
    offsets=pb-b.stations[-1];phi=np.radians(Z[:,2]-hb[0]);c=np.cos(phi);s=np.sin(phi)
    P=np.empty((len(Z),game.n_ships,2))
    P[:,:,0]=c[:,None]*offsets[None,:,0]-s[:,None]*offsets[None,:,1]+Z[:,0,None]
    P[:,:,1]=s[:,None]*offsets[None,:,0]+c[:,None]*offsets[None,:,1]+Z[:,1,None]
    H=Z[:,2,None]+(hb-hb[0])[None,:]
    return paired_stage(game,P,H,pr-opponent.stations[-1],hr)

def bounded_tracking(raw_correction,drift):
    if drift < -1e-12:raise ValueError('negative set distance')
    rp=max(0.,float(raw_correction));return rp/(rp+max(0.,float(drift))+EPS)

def epoch_metrics(game,b,r,rnext,Z=None,alphas=(.9,.8)):
    Z=domain() if Z is None else Z;E=embedding(Z)
    L0=field(game,b,r,Z);L1=field(game,b,rnext,Z)
    _,hb=formation_snapshot(b,game);_,hr=formation_snapshot(r,game);_,hr1=formation_snapshot(rnext,game)
    before=np.r_[b.stations[-1]-rnext.stations[-1],hb[0]];after=[]
    for a in (-60.,0.,60.):
        nxt=b.clone();nxt.extend_plan([a]);_,h=formation_snapshot(nxt,game)
        after.append(np.r_[nxt.stations[-1]-rnext.stations[-1],h[0]])
    eb=embedding(before);ea=embedding(np.array(after));out=[]
    for alpha in alphas:
        row={'alpha':alpha,'Lstar_before':float(L0.max()),'Lstar_after':float(L1.max()),
             'opponent_heading_change':abs(float(angle(hr1[0]-hr[0]))),
             'outside_domain_before':bool(np.linalg.norm(before[:2])>24 or np.linalg.norm(before[:2])<1)}
        mask0=L0>=alpha*L0.max();mask1=L1>=alpha*L1.max();G0=E[mask0];G1=E[mask1]
        row['n_G_before']=len(G0);row['n_G_after']=len(G1)
        if min(L0.max(),L1.max())<=0 or not len(G0) or not len(G1):
            row.update(defined=False,reason='nonpositive maximum or empty favorable set');out.append(row);continue
        tree0=cKDTree(G0);tree1=cKDTree(G1);d01=tree1.query(G0)[0];d10=tree0.query(G1)[0]
        drift=float(np.median(d01));centroid=float(np.linalg.norm(G0.mean(0)-G1.mean(0)));haus=float(max(d01.max(),d10.max()))
        db=float(tree1.query(eb)[0][0]);da=float(tree1.query(ea)[0].min());raw=db-da
        row.update(defined=True,directed_drift=drift,centroid_drift=centroid,hausdorff=haus,
          d_before=db,d_after_min=da,R_raw=raw,R_plus=max(0.,raw),Theta=bounded_tracking(raw,drift),
          Theta_centroid=bounded_tracking(raw,centroid),Theta_hausdorff=bounded_tracking(raw,haus),
          raw_ratio=raw/(drift+EPS),nonnegative_ratio=max(0.,raw)/(drift+EPS),
          negative_correction=bool(raw<0),zero_drift=bool(drift<EPS))
        if not 0<=row['Theta']<=1:raise RuntimeError('tracking bound failed')
        out.append(row)
    return out,{'Z':Z,'L_before':L0,'L_after':L1,'before':before,'reachable':np.array(after)}
