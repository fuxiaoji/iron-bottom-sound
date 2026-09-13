import numpy as np
from research.formation.exact_v12 import values_3x3,backward_induction
from research.formation.commitment_v12 import matrix_lp


def test_batched_support_enumeration_against_lp():
    rng=np.random.default_rng(2718)
    mats=rng.normal(size=(100,3,3));mats[:20]=np.round(mats[:20]);mats[20:25]=0
    v,g,f=values_3x3(mats)
    ref=np.array([matrix_lp(A)['V'] for A in mats])
    assert np.max(abs(v-ref))<1e-7
    assert max(g)<1e-7


def test_constant_past_reward_is_not_double_counted():
    A=np.full((27,27),5.)
    for h in (1,2,3):assert abs(backward_induction(A,3,3,h)['V']-5.)<1e-9


def test_one_step_and_committed_equivalence():
    rng=np.random.default_rng(244)
    A=rng.normal(size=(27,27));ref=matrix_lp(A)['V']
    assert abs(backward_induction(A,3,3,3)['V']-ref)<1e-9
    B=A[:3,:3]
    assert abs(backward_induction(B,3,1,1)['V']-matrix_lp(B)['V'])<1e-9


def test_exchange_oddness_does_not_imply_value_equals_stage():
    # Two absorbing exchange-related states s=+1,-1; singleton actions;
    # ell(s)=s and F(s)=s satisfy both v11 A1/A2. Two-stage value=2s.
    for s in (-1,1):
        total=s+s
        assert total!=s
        assert total==-((-s)+(-s))


def test_sequence_form_equivalences_and_monotonicity():
    from research.formation.sequence_v12 import solve_sequence_form
    rng=np.random.default_rng(555)
    for T in (1,2,3):
        A=rng.normal(size=(3**T,3**T))
        values={s:solve_sequence_form(A,3,T,s)['V'] for s in ('FF','FC','CF','CC')}
        assert abs(values['CC']-matrix_lp(A)['V'])<1e-7
        assert abs(values['FF']-backward_induction(A,3,T,1)['V'])<1e-7
        assert values['FC']>=values['CC']-1e-7
        assert values['FC']>=values['FF']-1e-7
        assert values['CC']>=values['CF']-1e-7
        assert values['FF']>=values['CF']-1e-7


def test_sequence_form_symmetry():
    from research.formation.sequence_v12 import solve_sequence_form
    rng=np.random.default_rng(999);A=rng.normal(size=(9,9));A-=A.T
    v={s:solve_sequence_form(A,3,2,s)['V'] for s in ('FF','FC','CF','CC')}
    assert abs(v['FF'])<1e-7 and abs(v['CC'])<1e-7
    assert abs(v['FC']+v['CF'])<1e-7
