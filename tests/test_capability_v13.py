import numpy as np
from research.formation.capability_v13 import terminal_matrix,sequences,sequence_value,flexible_value,negate_plan_permutation,variable_trajectories,action_menu
from research.formation.exact_v12 import terminal_payoff_matrix
from research.formation.commitment_v12 import matrix_lp,initial_states
from research.experiments.v13_exact import game

def test_variable_arc_sampler_matches_constant_speed_core():
    for geo in ('head_on','parallel','crossing'):
        for speed in (.75,1.,1.3):
            A=terminal_matrix(game(geo,1.,T=3),[speed],[1.],3)
            old=terminal_payoff_matrix(game(geo,speed,T=3),T=3)
            assert np.max(abs(A-old))<1e-8

def test_rectangular_information_sets_against_dp_and_matrix():
    rng=np.random.default_rng(13001)
    for b,r,T in [(3,2,1),(2,3,2),(3,2,3)]:
        A=rng.normal(size=(b**T,r**T));values={s:sequence_value(A,b,r,T,s) for s in ('FF','FC','CF','CC')}
        assert abs(values['FF']['V']-flexible_value(A,b,r,T)['V'])<1e-7
        assert abs(values['CC']['V']-matrix_lp(A)['V'])<1e-7
        assert values['FC']['V']>=max(values['FF']['V'],values['CC']['V'])-1e-7
        assert values['CF']['V']<=min(values['FF']['V'],values['CC']['V'])+1e-7
        if T==1:assert max(v['V'] for v in values.values())-min(v['V'] for v in values.values())<1e-7

def test_absolute_speed_menus_are_nested_and_mirrored():
    T=2;g=game('parallel',1.,T=T)
    low=terminal_matrix(g,[.75,1.],[1.],T);high=terminal_matrix(g,[.75,1.,1.3],[1.],T)
    indices=sequences(6,T)@(9**np.arange(T-1,-1,-1))
    assert np.max(abs(low-high[indices]))<1e-10
    swapped=terminal_matrix(g,[1.],[.75,1.,1.3],T)
    expected=-high.T[np.ix_(negate_plan_permutation(1,T),negate_plan_permutation(3,T))]
    assert np.max(abs(swapped-expected))<1e-8
    for s in ('FF','FC','CF','CC'):
        vl=sequence_value(low,6,3,T,s);vh=sequence_value(high,9,3,T,s)
        assert vh['V']>=vl['V']-1e-7

def test_variable_speed_future_suffix_cannot_change_prefix():
    rng=np.random.default_rng(13401);g=game('crossing',1.,T=4);b,_=initial_states(g)
    acts=action_menu([.75,1.,1.3])[rng.integers(0,9,size=(12,4))]
    p,h=variable_trajectories(b,acts,g);pp,hh=variable_trajectories(b,acts[:,:2],g)
    assert np.max(abs(p[:,:3]-pp))<1e-10
    assert np.max(abs(h[:,:3]-hh))<1e-10
