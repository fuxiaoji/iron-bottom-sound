"""Perfect-recall sealed-block games with publicly fixed update calendars.

At an update t the player observes BOTH executed prefixes through t, selects
the whole action block up to its next update, and remembers that choice.
The opponent observes neither the current action nor the unexecuted suffix.
No fictitious choices/observations occur inside a committed block.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import time
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from research.formation.exact_v12 import values_3x3


def calendar(S, T):
    S = tuple(S)
    if T < 1 or any(type(t) not in (int, np.int64, np.int32) for t in S):
        raise ValueError('integer horizon and update epochs required')
    if tuple(sorted(set(S))) != S or any(t <= 0 or t >= T for t in S):
        raise ValueError('calendar must be strictly increasing inside (0,T)')
    return (0,) + S + (T,)


def schedules(T):
    return [tuple(t for t in range(1, T) if mask & (1 << (t-1)))
            for mask in range(2**(T-1))]


@dataclass
class Flow:
    E: sparse.csr_matrix
    e: np.ndarray
    # (update time, next time, first sequence, first information-set row)
    blocks: tuple
    own: int
    opp: int
    T: int
    S: tuple

    def terminal_ids(self, own_leaf, opp_leaf):
        t, end, offset, _ = self.blocks[-1]
        own_prefix = own_leaf // self.own**(self.T-t)
        opp_prefix = opp_leaf // self.opp**(self.T-t)
        action = own_leaf % self.own**(self.T-t)
        return offset + (own_prefix*self.opp**t+opp_prefix)*self.own**(end-t)+action


def build_flow(own, opp, T, S):
    boundaries = calendar(S, T)
    if own < 1 or opp < 1:
        raise ValueError('positive action bases required')
    rr, cc, dd = [0], [0], [1.]
    seq, row = 1, 1
    blocks = []
    for t, end in zip(boundaries[:-1], boundaries[1:]):
        ninfo, na = (own*opp)**t, own**(end-t)
        ids = np.arange(ninfo, dtype=np.int64)
        if not blocks:
            parents = np.zeros(ninfo, dtype=np.int64)
        else:
            p, _, poff, _ = blocks[-1]
            ip, jp = ids // opp**t, ids % opp**t
            old_i, old_j = ip // own**(t-p), jp // opp**(t-p)
            old_a = ip % own**(t-p)
            parents = poff+(old_i*opp**p+old_j)*own**(t-p)+old_a
        rr.extend((row+ids).tolist()); cc.extend(parents.tolist()); dd.extend([-1.]*ninfo)
        rr.extend(np.repeat(row+ids, na).tolist())
        cc.extend(range(seq, seq+ninfo*na)); dd.extend([1.]*(ninfo*na))
        blocks.append((t, end, seq, row)); seq += ninfo*na; row += ninfo
    E = sparse.csr_matrix((dd, (rr, cc)), shape=(row, seq))
    e = np.zeros(row); e[0] = 1.
    return Flow(E, e, tuple(blocks), own, opp, T, tuple(S))


def payoff_matrix(A, B, R):
    n, m = A.shape
    if (n, m) != (B.own**B.T, R.own**R.T):
        raise ValueError('payoff matrix does not match action bases and horizon')
    i = np.repeat(np.arange(n, dtype=np.int64), m)
    j = np.tile(np.arange(m, dtype=np.int64), n)
    b, r = B.terminal_ids(i, j), R.terminal_ids(j, i)
    return sparse.coo_matrix((A.ravel(), (b, r)),
                            shape=(B.E.shape[1], R.E.shape[1])).tocsr()


def options(time_limit=1200.):
    return {'dual_feasibility_tolerance': 1e-8,
            'primal_feasibility_tolerance': 1e-8, 'time_limit': time_limit}


def best_response(c, flow, maximize=False, time_limit=1200.):
    r = linprog(-c if maximize else c, A_eq=flow.E, b_eq=flow.e,
                bounds=(0, None), method='highs', options=options(time_limit))
    if not r.success:
        raise RuntimeError('FULL_REALIZATION_BR_FAILED: '+r.message)
    return float(c @ r.x), r.x


def repair_flow(x, flow):
    """Convert solver output into a nonnegative realization plan top-down.

    Changes are measured and reported; positive incoming reach is distributed
    uniformly only if all proposed child mass vanishes. This is a feasible
    strategy construction, not a way to repair an incorrectly defined game.
    """
    out = np.zeros_like(x); out[0] = 1.
    for t, end, offset, row in flow.blocks:
        ninfo, na = (flow.own*flow.opp)**t, flow.own**(end-t)
        values = np.maximum(x[offset:offset+ninfo*na].reshape(ninfo, na), 0.)
        mass = values.sum(1)
        behavior = np.divide(values, mass[:, None], out=np.full_like(values, 1./na),
                             where=mass[:, None] > 0)
        # Each constraint has exactly one negative parent coefficient.
        part = flow.E[row:row+ninfo]
        rows, cols = part.nonzero()
        parentcols = cols[part.data < 0]
        out[offset:offset+ninfo*na] = (behavior*out[parentcols, None]).ravel()
    return out


def solve(A, base=3, T=6, S=(), opponent='F', S_R=None,
          time_limit=1200., return_strategies=False, structures=None):
    start = time.perf_counter()
    if S_R is None:
        if opponent not in ('F', 'C'):
            raise ValueError('opponent must be F or C')
        S_R = tuple(range(1, T)) if opponent == 'F' else ()
    B, R = structures or (build_flow(base, base, T, S), build_flow(base, base, T, S_R))
    P = payoff_matrix(np.asarray(A, float), B, R)
    nb, nr = P.shape
    ub = sparse.hstack((-P.T, R.E.T), format='csr')
    eq = sparse.hstack((B.E, sparse.csr_matrix((B.E.shape[0], R.E.shape[0]))), format='csr')
    lp = linprog(np.r_[np.zeros(nb), -R.e], A_ub=ub, b_ub=np.zeros(nr),
                 A_eq=eq, b_eq=B.e, bounds=[(0, None)]*nb+[(None, None)]*len(R.e),
                 method='highs', options=options(time_limit))
    if not lp.success:
        raise RuntimeError('SCHEDULE_LP_FAILED: '+lp.message)
    x0, y0 = lp.x[:nb], -lp.ineqlin.marginals
    x, y = repair_flow(x0, B), repair_flow(y0, R)
    lo, brR = best_response(P.T @ x, R, time_limit=time_limit)
    hi, brB = best_response(P @ y, B, maximize=True, time_limit=time_limit)
    scale = max(1., float(np.max(np.abs(A))))
    pad = 1e-8*scale
    flowB, flowR = float(np.max(abs(B.E@x-B.e))), float(np.max(abs(R.E@y-R.e)))
    if max(flowB, flowR) > 1e-7 or hi < lo-1e-7*scale:
        raise RuntimeError('SCHEDULE_CERTIFICATE_INVALID')
    result = {'S': list(S), 'S_R': list(S_R), 'opponent': opponent, 'T': T, 'base': base,
              'V': float(x@(P@y)), 'LB': lo-pad, 'UB': hi+pad, 'gap': hi-lo+2*pad,
              'raw_LB': lo, 'raw_UB': hi, 'numerical_padding': pad,
              'flow_residual_B': flowB, 'flow_residual_R': flowR,
              'strategy_repair_linf_B': float(np.max(abs(x-x0))),
              'strategy_repair_linf_R': float(np.max(abs(y-y0))),
              'sequences_B': nb, 'sequences_R': nr, 'infosets_B': len(B.e)-1,
              'infosets_R': len(R.e)-1, 'payoff_nonzeros': P.nnz,
              'seconds': time.perf_counter()-start, 'lp_iterations': lp.nit,
              'status': 'certified_numeric' if hi-lo+2*pad <= 1e-6*scale else 'unresolved',
              'certification_scope': 'finite game; floating-point LP/BR interval with declared padding; not rigorous interval arithmetic',
              'algorithm': 'sealed-block perfect-recall sequence form with repaired strategies and two full best responses'}
    if return_strategies:
        return result, {'x': x, 'y': y, 'brB': brB, 'brR': brR}, (B, R, P)
    return result


def pure_plans(flow, max_plans=100000):
    """Independent reduced pure-policy enumeration for MICRO tests only.

    Enumerates each reachable own sequence choice; unreachable own branches
    are omitted. No flow-matrix or terminal-id construction is used here.
    A plan is a map (time, own prefix, opponent prefix) -> action block.
    """
    boundaries = (0,)+flow.S+(flow.T,)
    plans = [{}]
    for t, end in zip(boundaries[:-1], boundaries[1:]):
        expanded = []
        for policy in plans:
            reachable = []
            for op in range(flow.opp**t):
                own = 0
                for p, q in zip(boundaries[:-1], boundaries[1:]):
                    if p >= t: break
                    old_op = op // flow.opp**(t-p)
                    own = own*flow.own**(q-p)+policy[p, own, old_op]
                reachable.append((t, own, op))
            reachable = sorted(set(reachable))
            count = flow.own**((end-t)*len(reachable))
            if len(expanded)+count > max_plans:
                raise ValueError('pure policy enumeration cap exceeded')
            for choices in itertools.product(range(flow.own**(end-t)), repeat=len(reachable)):
                expanded.append({**policy, **dict(zip(reachable, choices))})
        plans = expanded
    return plans


def pure_policy_payoffs(A, B, R, max_plans=100000):
    bp, rp = pure_plans(B, max_plans), pure_plans(R, max_plans)
    out = np.zeros((len(bp), len(rp)))
    for i, b in enumerate(bp):
        for j, r in enumerate(rp):
            bi = ri = 0; bq = rq = []
            for t in range(B.T):
                if t == 0 or t in B.S:
                    end = next(v for v in (*B.S, B.T) if v > t)
                    a = b[t, bi, ri]
                    bq = [(a//B.own**k)%B.own for k in reversed(range(end-t))]
                if t == 0 or t in R.S:
                    end = next(v for v in (*R.S, R.T) if v > t)
                    a = r[t, ri, bi]
                    rq = [(a//R.own**k)%R.own for k in reversed(range(end-t))]
                bi = bi*B.own+bq.pop(0); ri = ri*R.own+rq.pop(0)
            out[i, j] = A[bi, ri]
    return out


def decompose(A, base, T, S, S_R, time_limit=1200., pricing=False):
    """Exact common-update decomposition; no physical-history state merging.

    At a common update both preceding sealed blocks have ended. The executed
    prefixes are public and no private outstanding commands remain. Each
    prefix is consequently a proper subgame; reduction preserves its entire
    history in its matrix address. Noncommon boundaries are NOT cut.
    """
    start = time.perf_counter()
    boundaries = [0]+sorted(set(S) & set(S_R))+[T]
    current = np.asarray(A).copy(); error = 0.; trace = []
    for t, end in reversed(list(zip(boundaries[:-1], boundaries[1:]))):
        n, m = base**t, base**(end-t)
        mats = current.reshape(n, m, n, m).transpose(0, 2, 1, 3).reshape(n*n, m, m)
        sb = tuple(v-t for v in S if t < v < end)
        sr = tuple(v-t for v in S_R if t < v < end)
        tick = time.perf_counter()
        if m == 3:
            vals, gaps, fallback = values_3x3(mats)
            padding = 1e-8*max(1., float(np.max(abs(mats))))
            local_error = float(np.max(gaps))+padding
        else:
            structures = (build_flow(base, base, end-t, sb), build_flow(base, base, end-t, sr))
            vals = np.empty(n*n); local_error = 0.; fallback = n*n
            for i, sub in enumerate(mats):
                if pricing and (not sb or not sr):
                    from research.formation.pricing_v14 import column_generation
                    if not sr:
                        ans = column_generation(sub,base,end-t,sb,time_limit=time_limit,
                                                tolerance=max(5e-8,1e-7/max(1,len(boundaries)-1)))
                    else:
                        a = column_generation(-sub.T,base,end-t,sr,time_limit=time_limit,
                                              tolerance=max(5e-8,1e-7/max(1,len(boundaries)-1)))
                        ans = {**a,'V':-a['V'],'LB':-a['UB'],'UB':-a['LB']}
                else:
                    ans = solve(sub, base, end-t, sb, S_R=sr, structures=structures, time_limit=time_limit)
                vals[i] = ans['V']
                local_error = max(local_error, vals[i]-ans['LB'], ans['UB']-vals[i])
        error += local_error
        current = vals.reshape(n, n)
        trace.append({'t':t,'end':end,'subgames':n*n,'block_leaves':m*m,
                      'max_local_error':local_error,'LP_subgames':fallback,
                      'seconds':time.perf_counter()-tick})
    v = float(current[0, 0]); scale = max(1., float(np.max(abs(A))))
    return {'V':v,'LB':v-error,'UB':v+error,'gap':2*error,'S':list(S),'S_R':list(S_R),
            'T':T,'base':base,'seconds':time.perf_counter()-start,'trace':trace,
            'status':'certified_numeric' if 2*error <= 1e-6*scale else 'unresolved',
            'algorithm':'common-update decomposition with full-history subgames',
            'certification_scope':'finite game; accumulated floating-point subgame intervals'}
