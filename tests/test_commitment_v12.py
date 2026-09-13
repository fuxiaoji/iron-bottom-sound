"""Regression tests for causal history, hidden suffix, caching and solver bounds."""
import json
import numpy as np
import pytest
from research.formation.path_following import make_lf_game
from research.formation.commitment_v12 import *
KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']

@pytest.mark.parametrize('geometry,mirror',[('head_on',1),('parallel',-1),('crossing',1)])
def test_exchange_geometry(geometry,mirror):
    g=make_lf_game(KD,geometry,1.,1.,3);b,r=initial_states(g)
    assert exchange_mirror(g,b,r)==mirror
    ps=enumerate_sequences(GRIDS['3'],2)
    A=np.column_stack([batch_interval_payoff(g,b,r,ps,mirror*q,True,2) for q in ps])
    assert np.max(abs(A+A.T))<1e-8
    assert abs(matrix_lp(A,coupled=True)['V'])<1e-8


def test_reachable_histories_scalar_vector_swap_prefix():
    rng=np.random.default_rng(833)
    for j in range(15):
        g=make_lf_game(KD,('head_on','parallel','crossing')[j%3],.8,1.2,6)
        b,r=initial_states(g);b.extend_plan(rng.choice([-60.,0.,60.],3));r.extend_plan(rng.choice([-60.,0.,60.],3))
        p=rng.choice([-60.,0.,60.],3);q=rng.choice([-60.,0.,60.],3)
        z=scalar_interval_payoff(g,b,r,p,q)
        assert abs(z-batch_interval_payoff(g,b,r,p[None,:],q,True,3)[0])<1e-8
        assert abs(z+scalar_interval_payoff(swap_game(g),r,b,q,p))<1e-8
        a=trajectory_batch(b,p[None,:],g);c=trajectory_batch(b,np.r_[p,60.][None,:],g)
        for i in range(2):np.testing.assert_array_equal(a[i],c[i][:,:4])


def test_old_cache_collision_rejected_by_history_key():
    g=make_lf_game(KD,'head_on',1.2,1.,6);b,r=initial_states(g);b2=b.clone()
    b.extend_plan([60.]);b2.extend_plan([-60.]);r.extend_plan([0.])
    assert state_key(b,r)==state_key(b2,r)
    assert full_lf_state_fingerprint(g,b,r,5,GRIDS['3'])!=full_lf_state_fingerprint(g,b2,r,5,GRIDS['3'])


def test_off_exact_and_do_bounds_against_full_lp():
    g=make_lf_game(KD,'crossing',1.2,.9,3);b,r=initial_states(g);cache={}
    b.extend_plan([60.]);r.extend_plan([-60.])
    ps=enumerate_sequences(GRIDS['3'],2)
    A=np.column_stack([batch_interval_payoff(g,b,r,ps,q,True,2) for q in ps]);truth=matrix_lp(A)['V']
    answers=[]
    for mode in ('off','exact_history'):
        sol=RemainingHorizonGame(g,b,r,2,GRIDS['3'],cache,SolverConfig(cache_mode=mode)).solve()
        assert sol['converged'];assert sol['LB']-1e-8<=truth<=sol['UB']+1e-8
        answers.append(sol)
    for k in ('x','y'):np.testing.assert_array_equal(answers[0][k],answers[1][k])
    assert answers[0]['V']==answers[1]['V']


def test_nonconvergence_never_used_as_episode():
    g=make_lf_game(KD,'head_on',1.2,.9,3);b,r=initial_states(g)
    cfg=SolverConfig(max_iters=1,abs_tol=1e-12,rel_tol=1e-12)
    sol=RemainingHorizonGame(g,b,r,3,GRIDS['3'],config=cfg).solve()
    assert not sol['converged']
    out=run_cadence(g,b,r,1,3,GRIDS['3'],{},np.random.default_rng(1),cfg)
    assert out['J'] is None and out['status']=='SOLVER_NOT_CONVERGED'


def test_canonical_solver_exchange():
    g=make_lf_game(KD,'crossing',.8,1.2,3);b,r=initial_states(g)
    b.extend_plan([60.]);r.extend_plan([0.])
    a=RemainingHorizonGame(g,b,r,2,GRIDS['3']).solve()
    c=RemainingHorizonGame(swap_game(g),r,b,2,GRIDS['3']).solve()
    np.testing.assert_array_equal(a['x'],c['y']);np.testing.assert_array_equal(a['y'],c['x'])
    assert a['V']==-c['V']


def test_rigid_is_distinct_after_a_turn():
    lf=make_lf_game(KD,'crossing',1.2,1.,3)
    rg=make_lf_game(KD,'crossing',1.2,1.,3,formation_mode='rigid_line_ahead')
    b,r=initial_states(lf);p=np.array([60.,60.,0.]);q=np.zeros(3)
    assert abs(scalar_interval_payoff(lf,b,r,p,q)-scalar_interval_payoff(rg,b,r,p,q))>1e-3
    bv=batch_interval_payoff(rg,b,r,p[None,:],q,True,3)[0]
    assert abs(bv-scalar_interval_payoff(rg,b,r,p,q))<1e-8


def test_spatial_isometry_policy_not_just_value():
    from research.experiments.v12_isometry_audit import transform
    rng=np.random.default_rng(1707)
    for i in range(12):
        g=make_lf_game(KD,('head_on','parallel','crossing')[i%3],1.,1.,6);b,r=initial_states(g)
        b.extend_plan(rng.choice([-60.,0.,60.],3));r.extend_plan(rng.choice([-60.,0.,60.],3))
        Q=-np.eye(2) if i%2==0 else np.diag([1.,-1.]);c=np.array([7.,-12.])
        s=RemainingHorizonGame(g,b,r,3,GRIDS['3']).solve()
        u=RemainingHorizonGame(g,transform(b,Q,c),transform(r,Q,c),3,GRIDS['3']).solve()
        perm=np.arange(len(s['x'])) if i%2==0 else np.arange(len(s['x'])-1,-1,-1)
        np.testing.assert_allclose(s['x'],u['x'][perm],atol=1e-7,rtol=0)
        np.testing.assert_allclose(s['y'],u['y'][perm],atol=1e-7,rtol=0)


def test_off_never_uses_or_writes_shared_payoff_cache():
    g=make_lf_game(KD,'parallel',1.2,1.,2);b,r=initial_states(g)
    shared={'sentinel':'must remain unchanged'}
    sol=RemainingHorizonGame(g,b,r,2,GRIDS['3'],shared,SolverConfig(cache_mode='off')).solve()
    assert sol['converged'];assert shared=={'sentinel':'must remain unchanged'}
