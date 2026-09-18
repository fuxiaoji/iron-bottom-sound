"""A0 + B0 cheap kill tests.

A0 — is there a learnable "when to replan" signal?
    For every reachable decision node with an active commitment, compute
    Delta = V_replan - V_continue exactly.  Then ask whether a *budgeted*
    schedule can capture most of the value of always replanning.

B0 — does the hidden pending commitment create public-state aliasing?
    Group reachable nodes by snapshot and measure (a) the spread of optimal
    values inside a cell and (b) how often the optimal action differs.  Compare
    sealed-commitment games against the Markov / negative controls.

Outputs go to research/m0/results/.  Nothing here samples: every number is exact.

Run:
    PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/a0b0_census.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m0"))

from exact_lab import (BudgetedLab, ExactLab, alias_stats, case1_markov_control,
                       case3_negative_control, delta_rows, initial_belief)  # noqa: E402
from exact_lab.generator import grid  # noqa: E402

OUT = REPO / "research" / "m0" / "results"
FIG = REPO / "research" / "m0" / "figures"

# --- pre-declared thresholds (fixed BEFORE looking at results) -------------
A0_DELTA_FLOOR = 0.10          # a Delta below this counts as "no signal"
A0_NEAR_ZERO_FRACTION = 0.90   # >90% near-zero Deltas => A_WEAK
A0_SAVING_TARGET = 0.30
A0_RETENTION_TARGET = 0.95
B0_ALIAS_FLOOR = 1e-9          # any strictly positive gap counts as aliasing
B0_ALIAS_RATE_TARGET = 0.05    # >=5% of mixed pairs disagreeing on action


def _csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    cols = list(rows[0].keys())
    lines = [",".join(cols)]
    for r in rows:
        vals = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, tuple):
                v = "|".join(map(str, v))
            s = str(v)
            vals.append('"' + s.replace('"', "'") + '"' if ("," in s or '"' in s) else s)
        lines.append(",".join(vals))
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    specs = grid("discovery")
    print(f"discovery grid: {len(specs)} specs")

    all_delta: list[dict] = []
    alias_rows: list[dict] = []
    frontier_rows: list[dict] = []
    failures: list[dict] = []

    for spec in specs:
        try:
            all_delta.extend(delta_rows(spec))
            alias_rows.append(alias_stats(spec))
        except Exception as exc:  # noqa: BLE001 - record, never hide
            failures.append({"game_id": spec.name, "stage": "census",
                             "error": f"{type(exc).__name__}: {exc}"})
            continue
        # ---- compute/value frontier (A1 preview) -------------------------
        try:
            lab = ExactLab(spec)
            bl = BudgetedLab(spec)
            bel = initial_belief(spec)
            v_never = bl.oracle_k(0, bel)
            v_always = bl.oracle_k(spec.T, bel)
            span = v_always - v_never
            row = {"game_id": spec.name, "family": spec.family, "T": spec.T,
                   "b": spec.b, "K": spec.K, "L": spec.L,
                   "V_never": v_never, "V_always": v_always, "span": span}
            for k in range(1, spec.T):
                v_or = bl.oracle_k(k, bel)
                r_mean, r_std, n_subsets = bl.random_k_mean(k, bel)
                row.update({
                    f"V_oracle_k{k}": v_or,
                    f"V_random_k{k}": r_mean,
                    f"V_random_k{k}_std": r_std,
                    f"n_subsets_k{k}": n_subsets,
                    f"saving_k{k}": 1.0 - k / spec.T,
                    f"retention_oracle_k{k}": ((v_or - v_never) / span) if span > 1e-12 else None,
                    f"retention_random_k{k}": ((r_mean - v_never) / span) if span > 1e-12 else None,
                })
            for P in (2, 3, 4):
                if P > spec.T:
                    continue
                vp = bl.periodic(P, bel)
                row[f"V_periodic_P{P}"] = vp
                row[f"n_plans_periodic_P{P}"] = len(range(0, spec.T, P))
                row[f"saving_periodic_P{P}"] = 1.0 - len(range(0, spec.T, P)) / spec.T
                row[f"retention_periodic_P{P}"] = ((vp - v_never) / span) if span > 1e-12 else None
            frontier_rows.append(row)
        except Exception as exc:  # noqa: BLE001
            failures.append({"game_id": spec.name, "stage": "frontier",
                             "error": f"{type(exc).__name__}: {exc}"})

    # ------------------------------------------------------------------
    # A0 aggregation
    # ------------------------------------------------------------------
    deltas = [r["delta"] for r in all_delta if r["delta"] is not None]
    n_delta = len(deltas)
    near_zero = sum(1 for d in deltas if abs(d) < A0_DELTA_FLOOR)
    frac_near_zero = near_zero / n_delta if n_delta else 1.0

    by_family = defaultdict(list)
    by_horizon = defaultdict(list)
    by_commit = defaultdict(list)
    for r in all_delta:
        if r["delta"] is None:
            continue
        by_family[r["family"]].append(r["delta"])
        by_horizon[r["remaining_horizon"]].append(r["delta"])
        by_commit[r["commitment_len"]].append(r["delta"])

    # within-snapshot spread of Delta
    snap_groups = defaultdict(list)
    for r in all_delta:
        if r["delta"] is None:
            continue
        snap_groups[(r["game_id"], r["snapshot"])].append(r["delta"])
    spreads = [max(v) - min(v) for v in snap_groups.values() if len(v) > 1]

    a0 = {
        "n_decision_nodes": n_delta,
        "n_games": len({r["game_id"] for r in all_delta}),
        "delta_mean": statistics.mean(deltas) if deltas else None,
        "delta_median": statistics.median(deltas) if deltas else None,
        "delta_max": max(deltas) if deltas else None,
        "delta_min": min(deltas) if deltas else None,
        "delta_std": statistics.pstdev(deltas) if len(deltas) > 1 else 0.0,
        "frac_near_zero": frac_near_zero,
        "threshold_near_zero": A0_DELTA_FLOOR,
        "by_family_mean": {k: statistics.mean(v) for k, v in sorted(by_family.items())},
        "by_horizon_mean": {str(k): statistics.mean(v) for k, v in sorted(by_horizon.items())},
        "by_commitment_mean": {str(k): statistics.mean(v) for k, v in sorted(by_commit.items())},
        "within_snapshot_delta_spread_mean": statistics.mean(spreads) if spreads else 0.0,
        "within_snapshot_delta_spread_max": max(spreads) if spreads else 0.0,
        "n_snapshot_groups": len(spreads),
    }

    # frontier aggregation
    fr = []
    for row in frontier_rows:
        if row.get("span", 0.0) <= 1e-12:
            continue
        for k in range(1, row["T"]):
            ro = row.get(f"retention_oracle_k{k}")
            rr = row.get(f"retention_random_k{k}")
            if ro is None:
                continue
            fr.append({"saving": row[f"saving_k{k}"], "retention_oracle": ro,
                       "retention_random": rr or 0.0})
    # non-oracle candidates: periodic and random
    cand = []
    for row in frontier_rows:
        if row.get("span", 0.0) <= 1e-12:
            continue
        for P in (2, 3, 4):
            s = row.get(f"saving_periodic_P{P}")
            r = row.get(f"retention_periodic_P{P}")
            if s is None or r is None:
                continue
            cand.append({"method": f"periodic_P{P}", "saving": s, "retention": r,
                         "game_id": row["game_id"]})
        for k in range(1, row["T"]):
            s = row.get(f"saving_k{k}")
            r = row.get(f"retention_random_k{k}")
            if s is None or r is None:
                continue
            cand.append({"method": f"random_k{k}", "saving": s, "retention": r,
                         "game_id": row["game_id"]})
    best_cand = {}
    for c in cand:
        m = c["method"]
        if m not in best_cand or c["retention"] > best_cand[m]["retention"]:
            best_cand[m] = c
    a0["best_nonoracle_candidates"] = best_cand
    a0["oracle_frontier_points"] = len(fr)

    # ------------------------------------------------------------------
    # B0 aggregation
    # ------------------------------------------------------------------
    sealed = [r for r in alias_rows if r["family"] != "null"]
    controls = [r for r in alias_rows if r["family"] == "null"]

    def _agg(rows, key="action_disagree_rate"):
        vals = [r[key] for r in rows]
        return {
            "n_games": len(rows),
            "mean": statistics.mean(vals) if vals else 0.0,
            "max": max(vals) if vals else 0.0,
            "n_games_with_any_disagreement": sum(1 for v in vals if v > 0),
            "n_games_with_any_value_gap": (
                sum(1 for r in rows if r["max_v_gap"] > B0_ALIAS_FLOOR)
                if key == "action_disagree_rate" else None),
            "n_games_with_any_delta_gap": (
                sum(1 for r in rows if r["max_delta_gap"] > B0_ALIAS_FLOOR)
                if key == "action_disagree_rate" else None),
            "max_v_gap": max((r["max_v_gap"] for r in rows), default=0.0),
            "max_delta_gap": max((r["max_delta_gap"] for r in rows), default=0.0),
            "max_snapshot_regret": max((r["max_snapshot_regret"] for r in rows), default=0.0),
            "mean_snapshot_regret": (
                statistics.mean([r["max_snapshot_regret"] for r in rows]) if rows else 0.0),
            "n_games_with_snapshot_regret": sum(
                1 for r in rows if r["max_snapshot_regret"] > B0_ALIAS_FLOOR),
        }

    b0 = {
        "sealed_games": _agg(sealed),
        "control_games": _agg(controls),
        "sealed_vs_control_action_disagreement": (
            _agg(sealed)["mean"] - _agg(controls)["mean"]),
        "note": ("sealed = coordination/anticor/delayed/pathdep families; "
                 "control = opponent-blind 'null' family"),
    }

    # ------------------------------------------------------------------
    # Verdicts against the pre-declared gates
    # ------------------------------------------------------------------
    # trivial-schedule kill: if a FIXED schedule (periodic / random-K) already
    # reaches the pre-declared retention bar at the pre-declared saving bar, then
    # "learn when to replan" is not separated from a fixed calendar.
    n_eval = 0
    n_trivial_pass = 0
    trivial_examples = []
    for row in frontier_rows:
        if row.get("span", 0.0) <= 1e-12:
            continue
        for P in (2, 3, 4):
            sv = row.get(f"saving_periodic_P{P}")
            rt = row.get(f"retention_periodic_P{P}")
            if sv is None or rt is None:
                continue
            n_eval += 1
            if sv >= A0_SAVING_TARGET and rt >= A0_RETENTION_TARGET:
                n_trivial_pass += 1
                if len(trivial_examples) < 10:
                    trivial_examples.append({"game_id": row["game_id"],
                                             "method": f"periodic_P{P}",
                                             "saving": sv, "retention": rt})
        for k in range(1, row["T"]):
            sv = row.get(f"saving_k{k}")
            rt = row.get(f"retention_random_k{k}")
            if sv is None or rt is None:
                continue
            n_eval += 1
            if sv >= A0_SAVING_TARGET and rt >= A0_RETENTION_TARGET:
                n_trivial_pass += 1
                if len(trivial_examples) < 10:
                    trivial_examples.append({"game_id": row["game_id"],
                                             "method": f"random_k{k}",
                                             "saving": sv, "retention": rt})
    trivial_rate = (n_trivial_pass / n_eval) if n_eval else 0.0
    n_zero_span = sum(1 for r in frontier_rows if r.get("span", 0.0) <= 1e-12)

    a0_verdict = "PASS_TO_DISCOVERY"
    reasons = []
    if frac_near_zero >= A0_NEAR_ZERO_FRACTION:
        a0_verdict = "A_WEAK"
        reasons.append(f"{frac_near_zero:.1%} of Deltas below {A0_DELTA_FLOOR}")
    if a0["delta_max"] is not None and a0["delta_max"] < A0_DELTA_FLOOR:
        a0_verdict = "A_WEAK"
        reasons.append("max Delta is itself below the signal floor")
    if n_zero_span > 0.25 * len(frontier_rows):
        a0_verdict = "A_WEAK"
        reasons.append(f"{n_zero_span}/{len(frontier_rows)} games have zero "
                       f"compute-value span (never-plan == always-plan)")
    if trivial_rate >= 0.40:
        a0_verdict = "A_WEAK"
        reasons.append(f"a trivial fixed schedule already meets saving>="
                       f"{A0_SAVING_TARGET:.0%} and retention>="
                       f"{A0_RETENTION_TARGET:.0%} at {trivial_rate:.0%} of "
                       f"evaluable points, so a learned gate is not separated "
                       f"from a fixed calendar")
    a0.update({
        "n_zero_span_games": n_zero_span,
        "n_frontier_games": len(frontier_rows),
        "trivial_schedule_pass_rate": trivial_rate,
        "n_evaluable_points": n_eval,
        "n_trivial_pass_points": n_trivial_pass,
        "trivial_pass_examples": trivial_examples,
        "verdict": a0_verdict,
        "verdict_reasons": reasons,
    })

    b0_verdict = "PASS_TO_DISCOVERY"
    breasons = []
    if sealed and sealed[0]["n_mixed_cells"] is not None and \
            all(r["n_mixed_cells"] == 0 for r in sealed):
        b0_verdict = "B_WEAK"
        breasons.append("no snapshot cell contained two distinct beliefs")
    if b0["sealed_vs_control_action_disagreement"] <= 0:
        b0_verdict = "B_WEAK"
        breasons.append("sealed games are no more aliased than the controls")
    b0["verdict"] = b0_verdict
    b0["verdict_reasons"] = breasons

    # ------------------------------------------------------------------
    # write
    # ------------------------------------------------------------------
    _csv(OUT / "A0_delta_rows.csv", all_delta)
    _csv(OUT / "A0_frontier.csv", frontier_rows)
    _csv(OUT / "B0_alias_stats.csv", alias_rows)
    _csv(OUT / "A0_failures.csv", failures)
    (OUT / "A0_summary.json").write_text(json.dumps(a0, indent=2, ensure_ascii=False))
    (OUT / "B0_summary.json").write_text(json.dumps(b0, indent=2, ensure_ascii=False))

    print(json.dumps({"A0": a0, "B0": b0}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
