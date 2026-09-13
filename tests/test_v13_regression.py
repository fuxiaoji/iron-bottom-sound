"""New factorial and mirror wiring regressions; no full Monte Carlo audit."""
import inspect
import numpy as np
from research.experiments.v13_exact import game,differences,cell
from research.formation.exact_v12 import terminal_payoff_matrix,backward_induction
from research.formation.sequence_v12 import solve_sequence_form

def test_v13_fixed_opponent_and_true_mirror():
    for geo in ('head_on','parallel','crossing'):
        a=game(geo,.7,T=2);b=game(geo,1.3,T=2);m=game(geo,.7,True,T=2)
        assert a.vR==b.vR==m.vB==6.
        assert a.kR.eta_r==b.kR.eta_r==a.kB.eta_r==1.
        A=terminal_payoff_matrix(a,T=2);M=terminal_payoff_matrix(m,T=2)
        expected=-A.T if geo!='parallel' else -A.T[::-1,::-1]
        assert np.max(abs(M-expected))<1e-8
        va={s:solve_sequence_form(A,3,2,s) for s in ('FF','FC','CF','CC')}
        vm={s:solve_sequence_form(M,3,2,s) for s in ('FF','FC','CF','CC')}
        fb=differences(va);fm=differences(vm,True)
        for k in ('F','C'):assert abs(fb[k]['F']-fm[k]['F'])<1e-7
        assert abs(va['FF']['V']-backward_induction(A,3,2,1)['V'])<1e-7

def test_v13_scientific_route_has_no_pose_cache_or_receding_do():
    source=inspect.getsource(cell)
    assert 'old_pose_key' not in source
    assert 'RemainingHorizonGame' not in source
    assert 'complete_configuration_terminal_matrix' in source

def test_v13_cf_metadata_tracks_swapped_players():
    A=terminal_payoff_matrix(game('crossing',1.3,T=2),T=2)
    s=solve_sequence_form(A,3,2,'CF')
    assert s['infosets_B']==1<s['infosets_R']
    assert s['sequences_B']<s['sequences_R']
