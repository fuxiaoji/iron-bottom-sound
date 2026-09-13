"""E05: Dynamic engagement graph vs aggregate-force predictors of battle damage.

Research question (plan E05): do local structure metrics of the dynamic
engagement graph — built from the engine's own expected-hit function at the
moment geometry freezes (after MOVEMENT_RESOLUTION, before GUNNERY orders) —
predict the hull damage a ship takes in the following GUNNERY + TORPEDO_EFFECTS
window better than aggregate force totals alone?

Match collection discipline: every match is driven exclusively through legal
order batches produced by `TacticalCommander.choose_plan` and adjudicated by
`IronBottomEngine.submit_orders` / `advance` (engine truth).  The engagement
graph is read-only research instrumentation on top of the resulting states
(`research truth`), never a substitute for adjudication.

Graph construction (per snapshot, per alive ship j):
  - directed edge i->j: for each gun kind, sum the firepower of non-destroyed
    mounts of that kind whose arcs bear on j (engine `_relative_aspect`), then
    add `engine.expected_gunnery_hits(fp_kind, dist_ij, j.current_speed)` —
    the engine's own D66-averaged hit-table lookup.  Edges additionally
    require `engine._can_see` (gunnery orders to unseen targets are rejected
    by validation, so ungated edges could never convert into fire).
  - node targets: P_attack(j) = sum of incoming enemy weight, P_reply(j) =
    sum of outgoing friendly weight, LFR = (P_attack + eps) / (P_reply + eps),
    Herfindahl concentration over attackers, attacker count.
  - formation graph per side: adjacency at distance <= 3 and heading
    difference <= 1; algebraic connectivity lambda2 (second-smallest Laplacian
    eigenvalue).

Models (OLS, numpy lstsq; statsmodels not installed):
  (a) baseline  damage ~ hull_frac + force_ratio + avg_enemy_dist   (totals only)
  (b) full      baseline + LFR + Herfindahl + lambda2 + attacker_count + P_reply
  P_attack is deliberately excluded from (b) — it is collinear with LFR.
  80/20 train/test split by match (group split, stratified per scenario).
  Paired bootstrap (1000 resamples of test rows) for delta CIs; logistic
  (ridge IRLS) for damaged/not-damaged AUC.  OOD: train S-01 -> test S-03 and
  the reverse.

Acceptance (plan E05): out-of-sample R^2 improvement >= +0.05 OR relative MAE
reduction >= 10% for (b) over (a)  =>  PASS (main contribution); otherwise the
null result is reported verbatim.

Outputs: research/results/e05/{dataset.csv, results.json,
fig_e05_scatter.png, fig_e05_feature_importance.png, report.md}
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
for p in (REPO / "backend" / "src", REPO):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameState, Phase, ShipState, Side  # noqa: E402
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from research.common import derive_seed  # noqa: E402

OUT = REPO / "research" / "results" / "e05"

BASE_SEED = 20260909
SPLIT_SEED = 20260909
BOOTSTRAP_SEED = 20260909
BOOTSTRAP_REPS = 1000
EPS = 0.05       # LFR smoothing constant (D12)
LFR_CLIP = 50.0  # LFR upper bound (D12)
GUN_KINDS = ("primary", "secondary", "tertiary")

# (axis profile, allies profile) pairings cycled across match indices.
PROFILE_PAIRS = (
    ("balanced", "balanced"),
    ("line", "brawl"),
    ("cautious", "balanced"),
)

SCENARIOS = {
    "IBS-S-03": {"tag": 3, "matches": 80},
    "IBS-S-01": {"tag": 1, "matches": 40},
}

DECISIONS = [
    "D1 graph edges are gated by engine._can_see: gunnery validation rejects "
    "orders at unseen targets (night-battle visibility), so ungated expected "
    "fire could never convert into adjudicated shots.",
    "D2 per-kind firepower aggregation mirrors research/geometry/"
    "firepower_kernel.expected_hits_exact: sum can-bear, non-destroyed mount "
    "firepower per kind, then one engine.expected_gunnery_hits lookup per "
    "(kind, distance, target_speed).",
    "D3 baseline force_ratio = enemy-side remaining total hull points / "
    "own-side remaining total hull points (aggregate 'total strength'); "
    "avg_enemy_dist = mean distance to alive enemies.",
    "D4 Herfindahl H_j = sum_i (w_ij / P_attack)^2 with H=0 when P_attack=0 "
    "and H=1 with a single attacker (degenerate maximum concentration); "
    "'at least 2 attackers' structure is carried by attacker_count.",
    "D5 lambda2 = second-smallest eigenvalue of the side's formation-graph "
    "Laplacian (adjacency: distance <= 3 AND circular heading difference <= 1 "
    "on the 6-direction compass); 0.0 for sides with fewer than 2 alive ships "
    "or a disconnected graph.",
    "D6 outcome window = hull points lost between the GUNNERY snapshot and the "
    "entry to FIRE_END (i.e. _resolve_gunnery + _resolve_torpedoes only); "
    "movement-phase damage (collision / torpedo contact) precedes the snapshot "
    "and is excluded by design.",
    "D7 P_attack is excluded from the full regression (collinear with LFR = "
    "P_attack / P_reply); it is kept in dataset.csv for reference.",
    "D8 statsmodels/sklearn are not installed: OLS uses numpy lstsq, logistic "
    "uses ridge IRLS (lambda=1e-6, 50 Newton steps), AUC uses the "
    "Mann-Whitney rank statistic.",
    "D9 train/test split is grouped by match (no samples of the same match on "
    "both sides), stratified per scenario at 80/20.",
    "D10 S-01 special rules (allies firepower halved, axis turn-1 gunnery ban) "
    "act through adjudication only; w_ij uses the raw engine hit-table "
    "function per plan, so S-01 realised damage is systematically scaled "
    "relative to its graph weights — a known, documented mismatch that also "
    "affects the OOD transfer numbers.",
    "D11 reinforcement / contact-setup phases are answered by "
    "TacticalCommander.choose_plan itself (inherits "
    "DeterministicCommander._reinforcements); no special-casing needed. "
    "S-03 has no reinforcement group; S-01 turn-4 axis reinforcements enter "
    "through the same legal path when the turn-3 roll triggers.",
    "D12 LFR smoothing constant eps = 0.05 (scale of a fraction of one "
    "expected hit) and LFR clipped to [0, 50]: ships whose side has no "
    "can-bear gun on any visible enemy give P_reply = 0 and an unclipped "
    "ratio would explode (observed max > 3e5 with eps = 1e-6 in S-01) and "
    "destabilise OLS standardisation. Clip affects 8.4% of smoke samples.",
]


# --------------------------------------------------------------------------- #
# match collection
# --------------------------------------------------------------------------- #

def formation_lambda2(ships: list[ShipState]) -> float:
    """Algebraic connectivity of the side's formation graph (D5)."""
    n = len(ships)
    if n < 2:
        return 0.0
    adj = np.zeros((n, n))
    for a in range(n):
        for b in range(a + 1, n):
            pa, pb = ships[a].position, ships[b].position
            if pa is None or pb is None:
                continue
            head_diff = abs((ships[a].heading - ships[b].heading) % 6)
            head_diff = min(head_diff, 6 - head_diff)
            if pa.distance(pb) <= 3 and head_diff <= 1:
                adj[a, b] = adj[b, a] = 1.0
    laplacian = np.diag(adj.sum(axis=1)) - adj
    eigenvalues = np.linalg.eigvalsh(laplacian)
    return float(eigenvalues[1]) if n > 1 else 0.0


def snapshot_rows(engine: IronBottomEngine, state: GameState,
                  match_id: str, scenario: str, seed: int,
                  profiles: tuple[str, str]) -> tuple[list[dict], dict[str, dict]]:
    """Extract the engagement graph and node features at gunnery-freeze time.

    Returns (rows_without_outcome, hull_before) — outcome is filled later from
    the hull difference at FIRE_END entry.
    """
    alive = [s for s in state.ships.values() if not s.sunk and s.position]
    sides = {side: [s for s in alive if s.side == side] for side in Side}

    # --- directed expected-fire edges i->j (read-only research truth) ---
    weight: dict[tuple[str, str], float] = {}
    for attacker in alive:
        enemies = [s for s in alive if s.side != attacker.side]
        for target in enemies:
            if not engine._can_see(state, attacker, target):  # D1
                continue
            distance = attacker.position.distance(target.position)
            total = 0.0
            for kind in GUN_KINDS:  # D2
                firepower = sum(
                    mount.firepower for mount in attacker.gun_mounts
                    if mount.kind == kind and not mount.destroyed
                    and IronBottomEngine._relative_aspect(
                        attacker.position, attacker.heading, target.position)
                    in mount.arcs
                )
                if firepower <= 0:
                    continue
                total += engine.expected_gunnery_hits(
                    firepower, distance, target.current_speed)
            if total > 0:
                weight[(attacker.id, target.id)] = total

    hull_before = {s.id: int(s.hull) for s in alive}
    rows: list[dict] = []
    for target in alive:
        own = sides[target.side]
        foes = sides[target.side.opponent]
        incoming = {i: w for (i, j), w in weight.items() if j == target.id}
        outgoing = {k: w for (k, j), w in weight.items() if k == target.id}
        p_attack = float(sum(incoming.values()))
        p_reply = float(sum(outgoing.values()))
        lfr = min((p_attack + EPS) / (p_reply + EPS), LFR_CLIP)  # D12
        herfindahl = (
            sum((w / p_attack) ** 2 for w in incoming.values()) if p_attack > 0 else 0.0
        )  # D4
        enemy_dists = [target.position.distance(f.position) for f in foes]
        own_hull = sum(s.hull for s in own) or 1
        foe_hull = sum(s.hull for s in foes)
        rows.append({
            "match_id": match_id,
            "scenario": scenario,
            "seed": seed,
            "turn": int(state.turn),
            "side": target.side.value,
            "ship_id": target.id,
            "ship_type": target.ship_type,
            "hull_frac": float(target.hull / target.max_hull),
            "speed": float(target.current_speed),
            "avg_enemy_dist": float(np.mean(enemy_dists)) if enemy_dists else 0.0,
            "min_enemy_dist": float(np.min(enemy_dists)) if enemy_dists else 0.0,
            "p_attack": p_attack,
            "p_reply": p_reply,
            "lfr": float(lfr),
            "herfindahl": float(herfindahl),
            "attacker_count": float(sum(1 for w in incoming.values() if w > 0)),
            "lambda2_own": formation_lambda2(own),  # D5
            "force_ratio": float(foe_hull / own_hull),  # D3
            "n_alive_own": float(len(own)),
            "n_alive_enemy": float(len(foes)),
            "axis_profile": profiles[0],
            "allies_profile": profiles[1],
            "damage_next": 0,  # filled from hull diff
            "damaged": 0,
        })
    return rows, hull_before


def event_hull_crosscheck(state: GameState, start_seq: int, hull_before: dict[str, int],
                          hull_after: dict[str, int]) -> dict[str, float]:
    """Crosscheck hull diffs against gunnery_result/torpedo_result event payloads."""
    event_loss: dict[str, int] = {}
    for event in state.events:
        if event.sequence < start_seq or event.phase not in (Phase.GUNNERY, Phase.TORPEDO_EFFECTS):
            continue
        if event.type not in ("gunnery_result", "torpedo_result"):
            continue
        target = str(event.payload.get("target"))
        lost = int(event.payload.get("damage", {}).get("hull_lost", 0))
        event_loss[target] = event_loss.get(target, 0) + lost
    diffs = {
        ship_id: hull_before[ship_id] - hull_after.get(ship_id, 0)
        for ship_id in hull_before
        if hull_before[ship_id] - hull_after.get(ship_id, 0) > 0
    }
    agreement = sum(
        1 for ship_id in diffs
        if event_loss.get(ship_id, 0) == diffs[ship_id]
    )
    return {
        "ships_with_damage": len(diffs),
        "ships_matched_by_events": agreement,
        "event_total_hull_lost": int(sum(event_loss.values())),
        "hull_diff_total": int(sum(diffs.values())),
    }


def run_one_match(task: dict) -> dict:
    """Drive one full match via legal orders only; return per-snapshot samples."""
    scenario = task["scenario"]
    seed = task["seed"]
    profiles = task["profiles"]
    match_id = task["match_id"]

    engine = IronBottomEngine()
    state = engine.reset(scenario, seed)
    commanders = {
        Side.AXIS: TacticalCommander(PROFILES[profiles[0]]),
        Side.ALLIES: TacticalCommander(PROFILES[profiles[1]]),
    }
    samples: list[dict] = []
    pending: tuple[list[dict], dict[str, int], int] | None = None
    failures: list[str] = []
    try:
        while state.phase != Phase.COMPLETE:
            if state.phase in ORDER_PHASES:
                # Snapshot exactly when geometry is frozen: GUNNERY phase with
                # no orders sealed yet (== after MOVEMENT_RESOLUTION; == the
                # scenario's initial layout for S-01 turn 1 which starts in
                # GUNNERY per special rule IBS-S-01-R1).
                if state.phase == Phase.GUNNERY and not state.submitted_orders:
                    rows, hull_before = snapshot_rows(
                        engine, state, match_id, scenario, seed, profiles)
                    pending = (rows, hull_before, state.events[-1].sequence + 1 if state.events else 0)
                for side in Side:
                    _plan, batch, _audits = commanders[side].choose_plan(
                        engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, batch)
                    if not result.valid:
                        raise RuntimeError(f"{match_id}: invalid orders {result.errors}")
            engine.advance(state.game_id)
            if pending is not None and state.phase == Phase.FIRE_END:
                rows, hull_before, start_seq = pending
                hull_after = {s.id: int(s.hull) for s in state.ships.values()}
                for row in rows:
                    damage = hull_before[row["ship_id"]] - hull_after.get(row["ship_id"], 0)
                    row["damage_next"] = int(damage)
                    row["damaged"] = int(damage > 0)
                crosscheck = event_hull_crosscheck(state, start_seq, hull_before, hull_after)
                for row in rows:
                    row["crosscheck_matched"] = crosscheck["ships_matched_by_events"]
                    row["crosscheck_total"] = crosscheck["ships_with_damage"]
                samples.append({
                    "rows": rows,
                    "turn": int(rows[0]["turn"]) if rows else -1,
                    "crosscheck": crosscheck,
                })
                pending = None
    except Exception as exc:  # per-match isolation: record and skip
        failures.append(f"{type(exc).__name__}: {exc}")
        return {"match_id": match_id, "ok": False, "failures": failures,
                "samples": [], "winner": None, "turns": -1, "elapsed_s": 0.0}

    return {
        "match_id": match_id,
        "ok": not failures,
        "failures": failures,
        "samples": samples,
        "winner": state.winner,
        "turns": int(state.turn),
        "elapsed_s": 0.0,
    }


def build_tasks(n_s03: int, n_s01: int, base_seed: int) -> list[dict]:
    tasks: list[dict] = []
    for scenario, spec in SCENARIOS.items():
        count = n_s03 if spec["tag"] == 3 else n_s01
        for i in range(count):
            tasks.append({
                "scenario": scenario,
                "seed": derive_seed(base_seed, spec["tag"], i),
                "profiles": PROFILE_PAIRS[i % len(PROFILE_PAIRS)],
                "match_id": f"{scenario}-{i:03d}",
            })
    return tasks


# --------------------------------------------------------------------------- #
# statistics (numpy-only; statsmodels not installed — D8)
# --------------------------------------------------------------------------- #

BASELINE_FEATURES = ("hull_frac", "force_ratio", "avg_enemy_dist")
GRAPH_FEATURES = ("lfr", "herfindahl", "lambda2_own", "attacker_count", "p_reply")
FULL_FEATURES = BASELINE_FEATURES + GRAPH_FEATURES


def fit_ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef


def predict_ols(coef: np.ndarray, x: np.ndarray) -> np.ndarray:
    return coef[0] + x @ coef[1:]


def r_squared(y: np.ndarray, prediction: np.ndarray) -> float:
    ss_res = float(np.sum((y - prediction) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def mae(y: np.ndarray, prediction: np.ndarray) -> float:
    return float(np.mean(np.abs(y - prediction)))


def fit_logistic(x: np.ndarray, y: np.ndarray, ridge: float = 1e-6,
                 max_iter: int = 50) -> np.ndarray:
    """Ridge-penalised IRLS logistic regression (D8)."""
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(design.shape[1])
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    for _ in range(max_iter):
        eta = np.clip(design @ beta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        weights = np.clip(mu * (1 - mu), 1e-9, None)
        gradient = design.T @ (y - mu) - penalty @ beta
        hessian = (design.T * weights) @ design + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            break
        beta = beta + step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    return beta


def predict_logistic(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    eta = np.clip(beta[0] + x @ beta[1:], -30, 30)
    return 1.0 / (1.0 + np.exp(-eta))


def auc_score(y: np.ndarray, score: np.ndarray) -> float:
    """Mann-Whitney AUC with midranks for ties."""
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=float)
    sorted_scores = score[order]
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    n_pos = float(np.sum(y == 1))
    n_neg = float(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def standardize(train_x: np.ndarray, *others: np.ndarray):
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std == 0] = 1.0
    return tuple((arr - mean) / std for arr in (train_x, *others))


def regression_block(train_rows: list[dict], test_rows: list[dict],
                     bootstrap: int = 0, boot_seed: int = BOOTSTRAP_SEED) -> dict:
    """Fit baseline + full OLS (and logistic), score out-of-sample, optional
    paired bootstrap over test rows."""
    def matrices(rows: list[dict], features: tuple[str, ...]):
        x = np.array([[row[f] for f in features] for row in rows], dtype=float)
        y = np.array([row["damage_next"] for row in rows], dtype=float)
        d = np.array([row["damaged"] for row in rows], dtype=float)
        return x, y, d

    result: dict = {}
    predictions: dict[str, np.ndarray] = {}
    probabilities: dict[str, np.ndarray] = {}
    coefficients: dict[str, dict[str, float]] = {}
    x_train_all, y_train, d_train = matrices(train_rows, FULL_FEATURES)
    x_test_all, y_test, d_test = matrices(test_rows, FULL_FEATURES)

    for name, features in (("baseline", BASELINE_FEATURES), ("full", FULL_FEATURES)):
        cols = [FULL_FEATURES.index(f) for f in features]
        x_train, x_test = x_train_all[:, cols], x_test_all[:, cols]
        x_train_z, x_test_z = standardize(x_train, x_test)
        coef = fit_ols(x_train_z, y_train)
        pred = predict_ols(coef, x_test_z)
        predictions[name] = pred
        beta = fit_logistic(x_train_z, d_train)
        prob = predict_logistic(beta, x_test_z)
        probabilities[name] = prob
        result[name] = {
            "oos_r2": r_squared(y_test, pred),
            "oos_mae": mae(y_test, pred),
            "auc_damaged": auc_score(d_test, prob),
            "n_train": len(train_rows),
            "n_test": len(test_rows),
        }
        coefficients[name] = dict(zip(("intercept",) + features, map(float, coef)))

    delta_r2 = result["full"]["oos_r2"] - result["baseline"]["oos_r2"]
    mae_base = result["baseline"]["oos_mae"]
    mae_full = result["full"]["oos_mae"]
    mae_reduction = (mae_base - mae_full) / mae_base if mae_base > 0 else float("nan")
    delta_auc = result["full"]["auc_damaged"] - result["baseline"]["auc_damaged"]
    result["delta"] = {
        "r2_full_minus_baseline": float(delta_r2),
        "mae_relative_reduction": float(mae_reduction),
        "auc_full_minus_baseline": float(delta_auc),
    }

    if bootstrap > 0:
        rng = np.random.default_rng(boot_seed)
        n = len(test_rows)
        boot_r2, boot_mae, boot_auc = [], [], []
        for _ in range(bootstrap):
            idx = rng.integers(0, n, size=n)
            yt, dt = y_test[idx], d_test[idx]
            if float(np.sum((yt - np.mean(yt)) ** 2)) <= 0:
                continue
            r2_b = (r_squared(yt, predictions["full"][idx])
                    - r_squared(yt, predictions["baseline"][idx]))
            mb = mae(yt, predictions["baseline"][idx])
            mf = mae(yt, predictions["full"][idx])
            red = (mb - mf) / mb if mb > 0 else np.nan
            # Paired bootstrap over the same fixed out-of-sample outputs:
            # OLS predictions for R2/MAE, logistic probabilities for AUC.
            auc_b = (auc_score(dt, probabilities["full"][idx])
                     - auc_score(dt, probabilities["baseline"][idx]))
            boot_r2.append(r2_b)
            boot_mae.append(red)
            boot_auc.append(auc_b)
        def ci(values):
            arr = np.array([v for v in values if np.isfinite(v)])
            if len(arr) == 0:
                return [float("nan"), float("nan")]
            return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]
        result["delta"]["r2_ci95"] = ci(boot_r2)
        result["delta"]["mae_relative_reduction_ci95"] = ci(boot_mae)
        result["delta"]["auc_ci95"] = ci(boot_auc)
        result["delta"]["bootstrap_reps"] = bootstrap
    result["coefficients_standardized"] = coefficients
    return result


def split_by_match(rows: list[dict], fraction: float = 0.8,
                   seed: int = SPLIT_SEED) -> tuple[list[dict], list[dict]]:
    """Group split by match, stratified per scenario (D9).

    Every row is assigned exactly once: only the rows of the scenario being
    split enter the train/test lists (a naive `for row in rows` inside the
    per-scenario loop would silently duplicate the other scenario into test
    and leak its train rows).
    """
    rng = np.random.default_rng(seed)
    train: list[dict] = []
    test: list[dict] = []
    for scenario in sorted({row["scenario"] for row in rows}):
        scenario_rows = [row for row in rows if row["scenario"] == scenario]
        match_ids = sorted({row["match_id"] for row in scenario_rows})
        perm = rng.permutation(len(match_ids))
        n_train = int(round(len(match_ids) * fraction))
        train_ids = {match_ids[i] for i in perm[:n_train]}
        for row in scenario_rows:
            (train if row["match_id"] in train_ids else test).append(row)
    assert len(train) + len(test) == len(rows), "split must partition rows"
    return train, test


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #

FIELDNAMES = [
    "match_id", "scenario", "seed", "turn", "side", "ship_id", "ship_type",
    "hull_frac", "speed", "avg_enemy_dist", "min_enemy_dist",
    "p_attack", "p_reply", "lfr", "herfindahl", "attacker_count", "lambda2_own",
    "force_ratio", "n_alive_own", "n_alive_enemy",
    "axis_profile", "allies_profile", "damage_next", "damaged",
    "crosscheck_matched", "crosscheck_total",
]


def write_dataset(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_figures(rows: list[dict], train_rows: list[dict], test_rows: list[dict],
                 path_scatter: Path, path_importance: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x_train_all = np.array([[r[f] for f in FULL_FEATURES] for r in train_rows])
    x_test_all = np.array([[r[f] for f in FULL_FEATURES] for r in test_rows])
    y_train = np.array([r["damage_next"] for r in train_rows], dtype=float)
    y_test = np.array([r["damage_next"] for r in test_rows], dtype=float)
    preds = {}
    for name, features in (("baseline", BASELINE_FEATURES), ("full", FULL_FEATURES)):
        cols = [FULL_FEATURES.index(f) for f in features]
        x_tr, x_te = standardize(x_train_all[:, cols], x_test_all[:, cols])
        coef = fit_ols(x_tr, y_train)
        preds[name] = predict_ols(coef, x_te)

    fig, ax = plt.subplots(figsize=(5.8, 5.8))
    rng = np.random.default_rng(7)
    for name, color, label in (("baseline", "#7f7f7f", "baseline (totals only)"),
                               ("full", "#d62728", "full (baseline + graph shape)")):
        jitter = rng.uniform(-0.08, 0.08, size=len(y_test))
        ax.scatter(y_test + jitter, preds[name] + jitter, s=9, alpha=0.35,
                   color=color, label=label)
    limit = float(max(y_test.max(), max(p.max() for p in preds.values()))) * 1.05 + 0.5
    ax.plot([0, limit], [0, limit], "k--", lw=1)
    ax.set_xlabel("actual hull damage next phase")
    ax.set_ylabel("predicted hull damage (out-of-sample)")
    ax.set_title("E05 engagement graph: predicted vs actual damage (test matches)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path_scatter, dpi=160)
    plt.close(fig)

    cols = [FULL_FEATURES.index(f) for f in FULL_FEATURES]
    x_tr, _ = standardize(x_train_all[:, cols], x_train_all[:, cols])
    coef = fit_ols(x_tr, y_train)[1:]
    order = np.argsort(np.abs(coef))
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    colors = ["#1f77b4" if f in BASELINE_FEATURES else "#d62728" for f in
              [FULL_FEATURES[i] for i in order]]
    ax.barh([FULL_FEATURES[i] for i in order], coef[order], color=colors)
    ax.axvline(0.0, color="k", lw=0.8)
    ax.set_xlabel("standardized OLS coefficient (full model, train matches)")
    ax.set_title("E05 feature importance (blue = baseline totals, red = graph shape)")
    fig.tight_layout()
    fig.savefig(path_importance, dpi=160)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--smoke", action="store_true",
                        help="tiny run: 4x S-03 + 2x S-01 matches, 100 bootstrap reps")
    parser.add_argument("--matches-s03", type=int, default=SCENARIOS["IBS-S-03"]["matches"])
    parser.add_argument("--matches-s01", type=int, default=SCENARIOS["IBS-S-01"]["matches"])
    parser.add_argument("--base-seed", type=int, default=BASE_SEED)
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel match-collection processes (1 = serial)")
    parser.add_argument("--bootstrap", type=int, default=BOOTSTRAP_REPS)
    parser.add_argument("--from-dataset", action="store_true",
                        help="skip match collection; re-run analysis on the "
                             "existing research/results/e05/dataset.csv")
    args = parser.parse_args()
    if args.smoke:
        args.matches_s03, args.matches_s01, args.bootstrap = 4, 2, 100

    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.from_dataset:
        rows = []
        with (OUT / "dataset.csv").open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                for key in ("seed", "turn", "damage_next", "damaged",
                            "crosscheck_matched", "crosscheck_total"):
                    row[key] = int(row[key])
                for key in ("hull_frac", "speed", "avg_enemy_dist", "min_enemy_dist",
                            "p_attack", "p_reply", "lfr", "herfindahl",
                            "attacker_count", "lambda2_own", "force_ratio",
                            "n_alive_own", "n_alive_enemy"):
                    row[key] = float(row[key])
                rows.append(row)
        matches = []
        failed_matches = []
        crosschecks = []
        matched = 0
    else:
        tasks = build_tasks(args.matches_s03, args.matches_s01, args.base_seed)
        print(f"E05 collecting {len(tasks)} matches "
              f"(S-03 x{args.matches_s03}, S-01 x{args.matches_s01}, workers={args.workers})")

        matches = []
        if args.workers > 1:
            with ProcessPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(run_one_match, task): task for task in tasks}
                for done, future in enumerate(as_completed(futures), start=1):
                    matches.append(future.result())
                    if done % 10 == 0 or done == len(tasks):
                        print(f"  matches done: {done}/{len(tasks)}", flush=True)
        else:
            for index, task in enumerate(tasks, start=1):
                matches.append(run_one_match(task))
                if index % 10 == 0 or index == len(tasks):
                    print(f"  matches done: {index}/{len(tasks)}", flush=True)

        ok_matches = [m for m in matches if m["ok"]]
        failed_matches = [m for m in matches if not m["ok"]]
        rows = [row for match in ok_matches for sample in match["samples"] for row in sample["rows"]]
        crosschecks = [
            {"match_id": match["match_id"], **sample["crosscheck"]}
            for match in ok_matches for sample in match["samples"]
        ]
        matched = sum(1 for c in crosschecks if c["ships_with_damage"] == c["ships_matched_by_events"])

    damage_values = np.array([r["damage_next"] for r in rows], dtype=float)
    data_summary = {
        "n_samples": len(rows),
        "n_matches_ok": len([m for m in matches if m["ok"]]) if matches else None,
        "n_matches_failed": len(failed_matches),
        "failures": [f"{m['match_id']}: {m['failures']}" for m in failed_matches][:10],
        "n_snapshots": (sum(len(m["samples"]) for m in matches if m["ok"])
                        if matches else None),
        "damage_mean": float(damage_values.mean()) if len(rows) else float("nan"),
        "damage_share_positive": float((damage_values > 0).mean()) if len(rows) else float("nan"),
        "damage_max": float(damage_values.max()) if len(rows) else float("nan"),
        "crosscheck": {
            "n_windows": len(crosschecks),
            "windows_fully_matched_by_events": matched,
            "event_total_hull_lost": int(sum(c["event_total_hull_lost"] for c in crosschecks)),
            "hull_diff_total": int(sum(c["hull_diff_total"] for c in crosschecks)),
        },
    }
    print(json.dumps(data_summary, indent=2))

    if not args.from_dataset:
        write_dataset(rows, OUT / "dataset.csv")

    # ---- main 80/20 grouped split + paired bootstrap ----
    train_rows, test_rows = split_by_match(rows)
    main_block = regression_block(train_rows, test_rows, bootstrap=args.bootstrap)
    acceptance = (
        "PASS"
        if (main_block["delta"]["r2_full_minus_baseline"] >= 0.05
            or main_block["delta"]["mae_relative_reduction"] >= 0.10)
        else "FAIL"
    )

    # ---- OOD transfer: train whole scenario -> test whole other scenario ----
    s01 = [r for r in rows if r["scenario"] == "IBS-S-01"]
    s03 = [r for r in rows if r["scenario"] == "IBS-S-03"]
    ood = {
        "train_s01_test_s03": regression_block(s01, s03),
        "train_s03_test_s01": regression_block(s03, s01),
    }

    elapsed = time.perf_counter() - started
    results = {
        "experiment": "E05 dynamic engagement graph vs aggregate-force damage prediction",
        "config": {
            "base_seed": args.base_seed,
            "matches_s03": args.matches_s03,
            "matches_s01": args.matches_s01,
            "profile_pairs": list(PROFILE_PAIRS),
            "bootstrap_reps": main_block["delta"].get("bootstrap_reps", 0),
            "workers": args.workers,
            "smoke": bool(args.smoke),
        },
        "data_summary": data_summary,
        "split": {
            "method": "grouped by match, stratified per scenario, 80/20",
            "n_train_samples": len(train_rows),
            "n_test_samples": len(test_rows),
            "train_matches": len({r["match_id"] for r in train_rows}),
            "test_matches": len({r["match_id"] for r in test_rows}),
        },
        "baseline_features": list(BASELINE_FEATURES),
        "full_features": list(FULL_FEATURES),
        "main": main_block,
        "acceptance": {
            "criteria": "delta_oos_r2 >= +0.05 OR mae_relative_reduction >= 10%",
            "verdict": acceptance,
        },
        "ood": ood,
        "decisions": DECISIONS,
        "elapsed_s": round(elapsed, 1),
    }
    (OUT / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    make_figures(rows, train_rows, test_rows,
                 OUT / "fig_e05_scatter.png", OUT / "fig_e05_feature_importance.png")

    m = main_block
    lines = [
        "# E05 — dynamic engagement graph vs aggregate-force damage prediction", "",
    ]
    if matches:
        lines += [
            f"- matches: {data_summary['n_matches_ok']} ok / {data_summary['n_matches_failed']} failed"
            f" (S-03 x{args.matches_s03}, S-01 x{args.matches_s01});"
            f" snapshots {data_summary['n_snapshots']}; samples {data_summary['n_samples']}",
            f"- event crosscheck: {matched}/{len(crosschecks)} damage windows fully matched"
            f" by event payloads ({data_summary['crosscheck']['event_total_hull_lost']} vs"
            f" {data_summary['crosscheck']['hull_diff_total']} hull points)",
        ]
    else:
        lines.append(
            f"- samples: {data_summary['n_samples']} (analysis re-run on existing dataset.csv)")
    lines += [
        f"- samples with damage>0: {data_summary['damage_share_positive']:.3f};"
        f" mean damage {data_summary['damage_mean']:.3f};"
        f" max {data_summary['damage_max']:.0f}", "",
        "## Main result (80/20 grouped-by-match split)", "",
        "| model | OOS R2 | OOS MAE | AUC(damaged) |",
        "|---|---|---|---|",
        f"| baseline (totals) | {m['baseline']['oos_r2']:.4f} | {m['baseline']['oos_mae']:.4f} | {m['baseline']['auc_damaged']:.4f} |",
        f"| full (baseline + graph) | {m['full']['oos_r2']:.4f} | {m['full']['oos_mae']:.4f} | {m['full']['auc_damaged']:.4f} |",
        "",
        f"- delta R2 (full - baseline): **{m['delta']['r2_full_minus_baseline']:+.4f}**"
        + (f"  95% CI [{m['delta']['r2_ci95'][0]:+.4f}, {m['delta']['r2_ci95'][1]:+.4f}]"
           if "r2_ci95" in m["delta"] else ""),
        f"- relative MAE reduction: **{m['delta']['mae_relative_reduction']:+.4f}**"
        + (f"  95% CI [{m['delta']['mae_relative_reduction_ci95'][0]:+.4f},"
           f" {m['delta']['mae_relative_reduction_ci95'][1]:+.4f}]"
           if "mae_relative_reduction_ci95" in m["delta"] else ""),
        f"- delta AUC (damaged): **{m['delta']['auc_full_minus_baseline']:+.4f}**"
        + (f"  95% CI [{m['delta']['auc_ci95'][0]:+.4f}, {m['delta']['auc_ci95'][1]:+.4f}]"
           if "auc_ci95" in m["delta"] else ""),
        "",
        f"- acceptance (delta R2 >= +0.05 OR MAE reduction >= 10%): **{acceptance}**",
        "" if acceptance == "PASS" else
        "- Interpretation: the graph shape metrics add no material out-of-sample "
        "explanatory power beyond aggregate totals on this data — reported "
        "verbatim as a null result (plan permits downgrading to appendix).",
        "",
        "## OOD transfer",
        "",
        "| direction | model | R2 | MAE |",
        "|---|---|---|---|",
    ]
    for direction, block in ood.items():
        for name in ("baseline", "full"):
            lines.append(
                f"| {direction} | {name} | {block[name]['oos_r2']:.4f} | {block[name]['oos_mae']:.4f} |")
    lines += [
        "",
        "## Method",
        "",
        "- Matches driven exclusively through legal TacticalCommander order"
        " batches adjudicated by the engine (profiles cycled over "
        + ", ".join("/".join(p) for p in PROFILE_PAIRS) + ").",
        "- Snapshot at gunnery-freeze time (after MOVEMENT_RESOLUTION; S-01"
        " turn 1 starts in GUNNERY per scenario rule, snapshot = setup layout).",
        "- Directed edge i->j = sum over gun kinds of expected_gunnery_hits("
        "summed can-bear firepower, distance, target speed), gated by _can_see.",
        "- Node features: P_attack, P_reply, LFR=(P_attack+eps)/(P_reply+eps),"
        " Herfindahl concentration, attacker count, formation lambda2"
        " (distance<=3, heading diff<=1), plus baseline totals"
        " (hull_frac, force_ratio, avg_enemy_dist).",
        "- Outcome: hull points lost in the following GUNNERY +"
        " TORPEDO_EFFECTS phases. OLS (numpy lstsq), logistic ridge IRLS,"
        " Mann-Whitney AUC, paired bootstrap 95% CIs.",
        "",
        "## Decisions",
        "",
    ]
    lines += [f"- {d}" for d in DECISIONS]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"acceptance: {acceptance}")
    print(f"delta R2 {m['delta']['r2_full_minus_baseline']:+.4f}, "
          f"MAE reduction {m['delta']['mae_relative_reduction']:+.4f}, "
          f"AUC delta {m['delta']['auc_full_minus_baseline']:+.4f}")
    print(f"done in {elapsed:.1f}s -> {OUT}")


if __name__ == "__main__":
    main()
