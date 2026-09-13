import numpy as np
from research.formation.tracking_v13 import bounded_tracking,embedding,domain,epoch_metrics
from research.formation.commitment_v12 import initial_states
from research.experiments.v13_exact import game

def test_bounded_proxy_preserves_negative_raw_semantics():
    # A forced step away from a target can have negative correction.
    assert bounded_tracking(-1.,.5)==0.
    assert bounded_tracking(0.,0.)==0.
    for r in [-10.,-.1,0.,.1,10.]:
        for d in [0.,.1,10.]:assert 0<=bounded_tracking(r,d)<=1

def test_periodic_metric_and_fixed_domain():
    assert np.max(abs(embedding([[1,2,0]])-embedding([[1,2,360]])))<1e-12
    d=domain();assert np.linalg.norm(d[:,:2],axis=1).max()<=24.
    assert len(np.unique(d[:,2]))==12

def test_stationary_opponent_shape_has_zero_set_drift():
    g=game('parallel',1.);b,r=initial_states(g)
    rows,_=epoch_metrics(g,b,r,r.clone())
    for row in rows:
        assert row['defined']
        assert row['directed_drift']==row['hausdorff']==row['centroid_drift']==0.

def test_reduced_theorem_and_nested_counterexample():
    D=np.array([[-3.,1.],[2.,4.],[.1,-.7],[1.,1.]])
    x=np.linalg.norm(D,axis=1);mu=D.mean(0);r=np.linalg.norm(mu)
    vals=[]
    for v in np.linspace(0,8,101):
        lc=np.mean(x*x)-r*r+max(r-v,0)**2;lf=np.mean(np.maximum(x-v,0)**2)
        vals.append(lc-lf)
    assert min(vals)>-1e-12 and min(np.diff(vals))>-1e-12
    # Extra robust action removes the need to observe the hidden state.
    low=np.array([[1.,0.],[0.,1.]]);high=np.r_[low,[[1.,1.]]]
    f_low=low.max(0).mean()-low.mean(1).max()
    f_high=high.max(0).mean()-high.mean(1).max()
    assert f_high-f_low==-.5
