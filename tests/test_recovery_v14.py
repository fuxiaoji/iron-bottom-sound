import numpy as np
from research.formation.recovery_v14 import matrix_policies,full_update_policies,calendar_against_f
from research.formation.schedule_v14 import solve,schedules
from research.formation.commitment_v12 import matrix_lp


def test_recovered_matrix_strategies_against_all_actions():
    rng=np.random.default_rng(1481)
    for base in [2,3,5,7]:
        mats=rng.normal(size=(11,base,base))
        mats[0]=0.;mats[1,:,0]=mats[1,:,1]
        vals,p,q,gaps,_=matrix_policies(mats)
        for k,a in enumerate(mats):
            ref=matrix_lp(a)
            assert abs(vals[k]-ref['V'])<1e-7
            assert abs(p[k].sum()-1)<1e-10 and abs(q[k].sum()-1)<1e-10
            assert (a@q[k]).max()-(p[k]@a).min()<1e-7


def test_full_history_recovery_with_independent_sequence_form():
    for base,T in [(2,3),(3,3)]:
        A=np.random.default_rng(1482+base).normal(size=(base**T,base**T))
        got,policy=full_update_policies(A,base,T)
        ref=solve(A,base,T,tuple(range(1,T)),'F')
        assert got['LB']<=ref['UB'] and got['UB']>=ref['LB']
        assert got['gap']<1e-6 and got['flow_residual']<1e-9


def test_coarse_calendar_recovery_against_flexible_opponent():
    A=np.random.default_rng(1485).normal(size=(27,27))
    for s in schedules(3):
        ref=solve(A,3,3,s,'F')
        got,_=calendar_against_f(A,3,3,s,ref['UB'])
        assert abs(got['LB']-ref['LB'])<1e-6 and got['status']=='certified_numeric'
