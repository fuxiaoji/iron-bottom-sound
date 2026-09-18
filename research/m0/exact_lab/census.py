"""Node-level census: the measurement layer shared by the tests and by A0/B0.

Why nodes and not histories
---------------------------
The focal's posterior is a deterministic function of the observation history, so
every history inside one information-set node shares that node's belief (and
therefore its optimal action and its optimal value).  Aliasing is a property of
nodes: two *nodes* with the same **snapshot** but different beliefs are two
situations a stateless representation cannot tell apart.

So the census compares nodes, and reports two distinct kinds of gap:

``max_v_gap``       largest difference in optimal value between two nodes in the
                    same snapshot cell.  Zero means the snapshot loses nothing.
``n_action_disagree``  how often two same-snapshot nodes have *different*
                    optimal actions.  This can be positive even when
                    ``max_v_gap`` is zero (both nodes reach the same value by
                    different actions), which is exactly what makes a
                    snapshot-only policy ill-defined.
"""

from __future__ import annotations

from collections import defaultdict

from .core import ExactLab, GameSpec
from .lab import enumerate_all_nodes, snapshot_of


def cells(spec: GameSpec, require_commitment: bool = True):
    """Group reachable information-set nodes by public snapshot.

    Returns ``{snapshot: [(node, belief), ...]}``.
    """
    lab = ExactLab(spec)
    out: dict[tuple, list] = defaultdict(list)
    for (t, af, rf, obs), belief in enumerate_all_nodes(spec):
        if require_commitment and rf <= 0:
            continue
        out[snapshot_of(t, af, rf, obs)].append(((t, af, rf, obs), belief))
    return lab, out


def alias_stats(spec: GameSpec, require_commitment: bool = True) -> dict:
    """Aliasing statistics for one game."""
    lab, grouped = cells(spec, require_commitment)
    n_nodes = sum(len(v) for v in grouped.values())
    n_mixed = 0
    max_v_gap = 0.0
    n_disagree = 0
    max_delta_gap = 0.0
    pair_count = 0
    max_snapshot_regret = 0.0
    n_cells_with_regret = 0
    for snap, members in grouped.items():
        if len(members) < 2:
            continue
        if len({b for _n, b in members}) < 2:
            continue          # identical beliefs: nothing to alias
        n_mixed += 1
        # A snapshot policy must commit to ONE option for the whole cell.  Its
        # worst-case loss is the quantity that actually matters: the V-gap above
        # can be zero (every node reaches the same optimal value by a different
        # action) while no single snapshot action achieves it everywhere.
        regret = _snapshot_regret(lab, members)
        max_snapshot_regret = max(max_snapshot_regret, regret)
        if regret > 1e-12:
            n_cells_with_regret += 1
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (na, ba), (nb, bb) = members[i], members[j]
                pair_count += 1
                va = lab.V(na[0], na[1], na[2], ba)
                vb = lab.V(nb[0], nb[1], nb[2], bb)
                max_v_gap = max(max_v_gap, abs(va - vb))
                if lab.best_action(na[0], na[1], na[2], ba) != lab.best_action(nb[0], nb[1], nb[2], bb):
                    n_disagree += 1
                da = _delta(lab, na, ba)
                db = _delta(lab, nb, bb)
                if da is not None and db is not None:
                    max_delta_gap = max(max_delta_gap, abs(da - db))
    return {
        "game_id": spec.name,
        "family": spec.family,
        "T": spec.T, "b": spec.b, "K": spec.K, "m": spec.m, "L": spec.L,
        "alpha": spec.alpha,
        "n_nodes": n_nodes,
        "n_snapshot_cells": len(grouped),
        "n_mixed_cells": n_mixed,
        "n_mixed_pairs": pair_count,
        "n_action_disagree": n_disagree,
        "action_disagree_rate": (n_disagree / pair_count) if pair_count else 0.0,
        "max_v_gap": max_v_gap,
        "max_delta_gap": max_delta_gap,
        "max_snapshot_regret": max_snapshot_regret,
        "n_cells_with_regret": n_cells_with_regret,
        "is_lossy": spec.snapshot_lossy,
    }


def _snapshot_regret(lab: ExactLab, members) -> float:
    """min over a single cell-wide option of the worst-case loss vs optimal.

    ``min_opt max_node [ V(node) - W(node, opt) ]``.  Zero means the snapshot is
    a sufficient statistic for *acting* well; positive means no stateless policy
    can do well on every situation the cell conflates.
    """
    opts = lab.options(members[0][0][2])
    best = None
    for kind, a in opts:
        worst = 0.0
        for node, belief in members:
            t, af, rf, _obs = node
            v = lab.V(t, af, rf, belief)
            w = lab.W(t, af, rf, belief, kind, a)
            worst = max(worst, v - w)
        if best is None or worst < best:
            best = worst
    return best if best is not None else 0.0


def _delta(lab: ExactLab, node, belief):
    t, af, rf, _obs = node
    if rf <= 0:
        return None
    vc = lab.W(t, af, rf, belief, "continue", -1)
    return lab.V_replan(t, af, rf, belief) - vc


def delta_rows(spec: GameSpec) -> list[dict]:
    """The A0 table: one row per reachable decision node with a commitment."""
    lab, grouped = cells(spec)
    rows = []
    for snap, members in grouped.items():
        for (t, af, rf, obs), belief in members:
            vc = lab.W(t, af, rf, belief, "continue", -1)
            vr = lab.V_replan(t, af, rf, belief)
            best = lab.best_action(t, af, rf, belief)
            top_theme = max(belief, key=lambda kv: kv[1])[0]
            rows.append({
                "game_id": spec.name,
                "family": spec.family,
                "node_id": f"n:t{t}:obs{','.join(map(str, obs))}:af{af}:rf{rf}",
                "t": t,
                "public_state": f"z:t{t}:q{obs[-1] if obs else 0}",
                "snapshot": snap,
                "hidden_commitment": f"th{top_theme[0]}:ao{','.join(map(str, top_theme[1]))}",
                "belief_n": len(belief),
                "remaining_horizon": spec.T - t,
                "commitment_len": rf,
                "V_replan": vr,
                "V_continue": vc,
                "delta": vr - vc,
                "best_kind": best[0],
                "best_action": best[1],
            })
    return rows


def find_witness(verbose: bool = False):
    """Node-level search for the Case-2 witness.

    ``best_disagreeing`` requires the gaps to be real, i.e. the two nodes must
    have different beliefs AND different optimal actions AND a strictly positive
    value or delta gap — never a mere tie between equally good actions.
    """
    from .lab import case2_candidates

    best_disagreeing = None
    best_gap = None
    for spec in case2_candidates():
        if not spec.snapshot_lossy:
            continue
        try:
            lab, grouped = cells(spec)
        except RuntimeError:
            continue
        for snap, members in grouped.items():
            if len(members) < 2 or len({b for _n, b in members}) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    (na, ba), (nb, bb) = members[i], members[j]
                    oa = lab.best_action(na[0], na[1], na[2], ba)
                    ob = lab.best_action(nb[0], nb[1], nb[2], bb)
                    va = lab.V(na[0], na[1], na[2], ba)
                    vb = lab.V(nb[0], nb[1], nb[2], bb)
                    da = _delta(lab, na, ba)
                    db = _delta(lab, nb, bb)
                    v_gap = abs(va - vb)
                    d_gap = abs(da - db) if (da is not None and db is not None) else 0.0
                    gap = max(v_gap, d_gap)
                    if gap <= 1e-12:
                        continue
                    rec = {"spec": spec, "snap": snap, "a": oa, "b": ob,
                           "V_a": va, "V_b": vb, "v_gap": v_gap, "d_gap": d_gap,
                           "gap": gap, "actions_disagree": oa != ob,
                           "node_a": na, "node_b": nb}
                    if best_gap is None or gap > best_gap["gap"]:
                        best_gap = rec
                    if oa != ob and (best_disagreeing is None or gap > best_disagreeing["gap"]):
                        best_disagreeing = rec
                    if verbose:
                        print("witness", spec.name, snap, oa, ob, va, vb, da, db)
    return {"best_disagreeing": best_disagreeing, "best_gap": best_gap}
