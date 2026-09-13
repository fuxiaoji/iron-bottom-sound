import numpy as np
import pytest
from research.formation.schedule_v14 import build_flow, solve, schedules, pure_policy_payoffs, calendar
from research.formation.commitment_v12 import matrix_lp
from research.formation.sequence_v12 import solve_sequence_form
from research.formation.exact_v12 import backward_induction


@pytest.mark.parametrize('T', [1, 2])
def test_micro_normal_form(T):
    rng = np.random.default_rng(1400+T)
    A = rng.normal(size=(2**T, 2**T))
    for sb in schedules(T):
        for sr in schedules(T):
            B, R = build_flow(2, 2, T, sb), build_flow(2, 2, T, sr)
            normal = pure_policy_payoffs(A, B, R)
            ref = matrix_lp(normal)['V']
            ans = solve(A, 2, T, sb, S_R=sr)
            assert ans['LB'] <= ref+1e-7 <= ans['UB']+2e-7
            assert abs(ref-ans['V']) < 1e-7


def test_T3_independent_reduced_normal_form():
    A = np.random.default_rng(1403).normal(size=(8, 8))
    for sb in schedules(3):
      for sr in schedules(3):
        B, R = build_flow(2, 2, 3, sb), build_flow(2, 2, 3, sr)
        ref = matrix_lp(pure_policy_payoffs(A, B, R))['V']
        assert abs(solve(A, 2, 3, sb, S_R=sr)['V']-ref) < 1e-7


def test_common_boundary_decomposition():
    from research.formation.schedule_v14 import decompose
    A = np.random.default_rng(1616).normal(size=(27,27))
    for sb in schedules(3):
        for sr in schedules(3):
            d = decompose(A,3,3,sb,sr)
            v = solve(A,3,3,sb,S_R=sr)['V']
            assert d['LB']-1e-7 <= v <= d['UB']+1e-7


@pytest.mark.parametrize('geo',['head_on','parallel','crossing'])
def test_physical_mirror_and_legacy_match(geo):
    from research.formation.physical_v14 import matrix
    from research.formation.payoff_v13 import terminal_payoff_matrix
    from research.experiments.v13_exact import game
    c={'geometry':geo,'speed':.85,'distance':16.,'T':2,'grid':3,'ablation':'none'}
    a=matrix(c); ref=terminal_payoff_matrix(game(geo,.85,T=2),T=2)
    assert np.max(abs(a-ref))<1e-10
    for ablation in ['none','terminal','isotropic','rigid']:
        c['distance']=13.5;c['ablation']=ablation
        a=matrix(c);m=matrix(c,True)
        expected=-a.T if geo!='parallel' else -a.T[::-1,::-1]
        assert np.max(abs(m-expected))<1e-8


@pytest.mark.parametrize('T', [1, 2, 3])
def test_old_endpoints_and_swap(T):
    A = np.random.default_rng(1500+T).normal(size=(3**T, 3**T))
    for kind in ('FF', 'FC', 'CF', 'CC'):
        sb = tuple(range(1, T)) if kind[0] == 'F' else ()
        sr = tuple(range(1, T)) if kind[1] == 'F' else ()
        v = solve(A, 3, T, sb, S_R=sr)['V']
        assert abs(v-solve_sequence_form(A, 3, T, kind)['V']) < 1e-7
        assert abs(v+solve(-A.T, 3, T, sr, S_R=sb)['V']) < 1e-7
        if kind == 'FF': assert abs(v-backward_induction(A, 3, T, 1)['V']) < 1e-7


def test_all_calendar_inclusion():
    T = 3; A = np.random.default_rng(1414).normal(size=(27, 27))
    for opponent in ('F', 'C'):
        vals = {s: solve(A, 3, T, s, opponent)['V'] for s in schedules(T)}
        for s, v in vals.items():
            for t, w in vals.items():
                if set(s) <= set(t): assert v <= w+1e-7


def test_hidden_suffix_and_prefix_information():
    B = build_flow(3, 3, 4, (2,))
    # At t=2 the opponent's final two actions are absent from the info ID.
    a = B.terminal_ids(np.array([10, 10]), np.array([0, 8]))
    assert a[0] == a[1]
    b = B.terminal_ids(np.array([10, 10]), np.array([0, 9]))
    assert b[0] != b[1]
    assert [x[0] for x in B.blocks] == [0, 2]
    assert B.E.shape[0] == 1+1+9**2


@pytest.mark.parametrize('S,T', [((0,), 3), ((3,), 3), ((2, 1), 3), ((1, 1), 3), ((1.5,), 3)])
def test_invalid_calendar(S, T):
    with pytest.raises(ValueError): calendar(S, T)
