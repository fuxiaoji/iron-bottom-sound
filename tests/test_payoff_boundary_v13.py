import numpy as np
from research.experiments.v13_exact import game
from research.formation.commitment_v12 import initial_states,trajectory_batch,paired_stage as old_stage
from research.formation.payoff_v13 import paired_stage,scalar_interval_payoff,angle

def test_observed_confirmatory_boundary_failure_is_fixed_without_projection():
    g=game('parallel',.75);m=game('parallel',.75,True)
    b,r=initial_states(g);mb,mr=initial_states(m)
    u=np.array([[-60.,0,60,60,-60,60]]);v=np.array([[-60.,0,60,-60,-60,60]])
    pb,hb=trajectory_batch(b,u,g);pr,hr=trajectory_batch(r,v,g)
    qb,qhb=trajectory_batch(mb,-v,m);qr,qhr=trajectory_batch(mr,-u,m)
    old=old_stage(g,pb,hb,pr,hr)+old_stage(m,qb,qhb,qr,qhr)
    assert abs(old).max()>2.
    L=paired_stage(g,pb,hb,pr,hr);M=paired_stage(m,qb,qhb,qr,qhr)
    assert abs(L+M).max()<1e-8
    val=(L[0,:-1]+L[0,1:]).sum()/2
    assert abs(val-scalar_interval_payoff(g,b,r,u[0],v[0]))<1e-10

def test_sector_boundary_snap_is_bounded_and_exchange_compatible():
    for edge in [-150.,-30.,30.,150.]:
        for eps in [-1e-10,0,1e-10]:assert float(angle(edge+eps))==edge
        assert float(angle(edge+1e-5))!=edge
    x=np.linspace(-179,179,101)
    assert np.max(abs(angle(-x)+angle(x)))<1e-8
