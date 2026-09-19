"""E1-T2: predict high-rho (decision-critical) states from agent-visible features only.

Data: the 120 evaluable M1 G1 main pairs; features from the allies' OWN
observation of the branch-A state (fog-of-war filtered, no hidden commitment,
no rollout values, no rho). Labels: high-meaningful rho per PRE_REGISTRATION
(norm >= 0.10 AND abs >= floor on either value function) from
e1_t1_rho_pairs.csv. Label noise on the 90 non-CI-passing pairs is
acknowledged (their rho is measured but ranking-uncertain).

Pre-declared gate (plan §5): best simple model CV AUROC >= 0.75 AND
recall(high-rho) >= 70% at a 20-30% reasoning budget.

    PYTHONPATH=backend/src:research/m1_5/scripts .venv/bin/python \
        research/m1_5/scripts/e1_t2_predict.py
"""

from __future__ import annotations

import csv
import gzip
import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import Side  # noqa: E402
from iron_bottom_sound.state_export import export_frame  # noqa: E402

G1 = REPO / "research" / "m1" / "g1"
OUT = REPO / "research" / "m1_5"

FLOOR_OUTCOME = 0.10
FLOOR_DAMAGE = 0.02
HIGH_NORM = 0.10
SEED = 7


def visible_features(state, engine) -> dict:
    """Agent-visible features only: computed from observe(ALLIES), never from
    sealed orders, never from rollouts, never from rho."""
    obs = engine.observe(state.game_id, Side.ALLIES)
    own = [s for s in obs.ships if s.side == Side.ALLIES.value and not s.sunk and s.position]
    enemies = [s for s in obs.ships if s.side != Side.ALLIES.value and not s.sunk and s.position]
    f = {}
    f["n_own"] = len(own)
    f["n_enemy_visible"] = len(enemies)
    if own and enemies:
        dists = [min(o.position.distance(e.position) for o in own) for e in enemies]
        f["nearest_enemy_dist"] = min(dists)
        f["mean_enemy_dist"] = statistics.mean(dists)
        # relative bearing of the nearest enemy to the nearest own ship
        nearest_own = min(own, key=lambda o: min(
            o.position.distance(e.position) for e in enemies))
        nearest_enemy = min(enemies, key=lambda e: nearest_own.position.distance(e.position))
        f["bearing_delta"] = abs(
            (nearest_enemy.position.direction_to(nearest_own.position)
             if hasattr(nearest_enemy.position, "direction_to") else 0) or 0)
        # spread of visible enemies (formation geometry proxy)
        if len(enemies) >= 2:
            f["enemy_spread"] = statistics.mean(
                e.position.distance(e2.position) for i, e in enumerate(enemies)
                for e2 in list(enemies)[i + 1:])
        else:
            f["enemy_spread"] = 0.0
        # own spread
        if len(own) >= 2:
            f["own_spread"] = statistics.mean(
                o.position.distance(o2.position) for i, o in enumerate(own)
                for o2 in list(own)[i + 1:])
        else:
            f["own_spread"] = 0.0
    else:
        f["nearest_enemy_dist"] = 99.0
        f["mean_enemy_dist"] = 99.0
        f["bearing_delta"] = 0.0
        f["enemy_spread"] = 0.0
        f["own_spread"] = 0.0
    # torpedo readiness among own ships (visible)
    f["own_torpedo_ready"] = sum(
        1 for s in state.ships.values()
        if s.side == Side.ALLIES and not s.sunk and s.torpedo and not s.torpedo.destroyed
        and s.torpedo_launchers and any(l.loaded > 0 and not l.destroyed
                                        for l in s.torpedo_launchers))
    f["own_damage_frac"] = statistics.mean(
        [1.0 - (s.hull / s.max_hull) for s in own
         if s.hull is not None and s.max_hull] or [0.0])
    f["score_margin"] = (state.score[Side.ALLIES.value]
                         - state.score[Side.AXIS.value])
    f["turn"] = state.turn
    f["own_hp_total"] = sum(s.hull or 0 for s in own)
    f["visible_enemy_vp"] = sum(s.vp for s in enemies)
    return f


def main() -> int:
    labels = {r["pair_id"]: r for r in
              csv.DictReader((OUT / "metrics" / "e1_t1_rho_pairs.csv").open())}
    rows = []
    skipped = []
    for pid, lab in labels.items():
        path = G1 / "states" / f"{pid}_A.json.gz"
        if not path.exists():
            skipped.append(pid)
            continue
        from iron_bottom_sound.models import GameState
        state = GameState.model_validate_json(gzip.decompress(path.read_bytes()))
        eng = IronBottomEngine()
        eng.games[state.game_id] = state
        f = visible_features(state, eng)
        high_outcome = (float(lab["rho_norm_outcome"]) >= HIGH_NORM
                        and float(lab["rho_abs_outcome"]) >= FLOOR_OUTCOME)
        high_damage = (float(lab["rho_norm_damage"]) >= HIGH_NORM
                       and float(lab["rho_abs_damage"]) >= FLOOR_DAMAGE)
        f["label_high"] = 1 if (high_outcome or high_damage) else 0
        f["rho_abs_outcome"] = float(lab["rho_abs_outcome"])
        f["rho_abs_damage"] = float(lab["rho_abs_damage"])
        f["pair_id"] = pid
        f["scenario"] = lab["scenario"]
        rows.append(f)
    print(f"features for {len(rows)} pairs (skipped {len(skipped)}); "
          f"positives {sum(r['label_high'] for r in rows)}")

    import sklearn.metrics as M
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold

    feature_names = [k for k in rows[0] if k not in
                     ("label_high", "pair_id", "scenario",
                      "rho_abs_outcome", "rho_abs_damage")]
    X = np.array([[r[k] for k in feature_names] for r in rows], dtype=float)
    y = np.array([r["label_high"] for r in rows], dtype=int)
    rho_out = np.array([r["rho_abs_outcome"] for r in rows], dtype=float)
    rho_dmg = np.array([r["rho_abs_damage"] for r in rows], dtype=float)
    rho_mass = rho_out + rho_dmg * 5.0  # combined regret mass (outcome + 5x damage scale)

    models = {
        "logreg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
        "gbdt": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=SEED),
        "mlp_small": make_pipeline(StandardScaler(), MLPClassifier(
            hidden_layer_sizes=(16,), max_iter=1500, random_state=SEED)),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = {}
    for name, model in models.items():
        aurocs, auprcs = [], []
        recalls_20, recalls_30 = [], []
        fn_mass_20, fn_mass_30 = [], []
        oof_score = np.zeros(len(y))
        for tr, te in cv.split(X, y):
            m = model
            from sklearn.base import clone
            m = clone(model)
            m.fit(X[tr], y[tr])
            if hasattr(m, "predict_proba"):
                s = m.predict_proba(X[te])[:, 1]
            else:
                s = m.decision_function(X[te])
            oof_score[te] = s
            yte = y[te]
            if yte.sum() > 0:
                aurocs.append(M.roc_auc_score(yte, s))
                auprcs.append(M.average_precision_score(yte, s))
        # budget recalls on out-of-fold scores
        for budget, r20, r30 in ((None, recalls_20, recalls_30),):
            pass
        order = np.argsort(-oof_score)
        for frac, rec_list, fn_list in ((0.20, recalls_20, fn_mass_20),
                                        (0.30, recalls_30, fn_mass_30)):
            k = max(1, int(frac * len(y)))
            top = order[:k]
            recalled = y[top].sum()
            rec_list.append(recalled / max(1, y.sum()))
            # false negatives: high-rho states NOT in the top-k, weighted by regret mass
            fn = [i for i in range(len(y)) if y[i] == 1 and i not in set(top)]
            total_mass = rho_mass[y == 1].sum()
            fn_list.append(rho_mass[fn].sum() / total_mass if total_mass > 0 else 0.0)
        results[name] = {
            "auroc_mean": statistics.mean(aurocs), "auroc_std": statistics.pstdev(aurocs),
            "auprc_mean": statistics.mean(auprcs),
            "recall_at_20pct": statistics.mean(recalls_20),
            "recall_at_30pct": statistics.mean(recalls_30),
            "fn_regret_mass_frac_at_20pct": statistics.mean(fn_mass_20),
            "fn_regret_mass_frac_at_30pct": statistics.mean(fn_mass_30),
        }
    # always-reject baseline for FN mass: 1.0 by definition
    gate = {
        "auroc_ge_075": bool(max(r["auroc_mean"] for r in results.values()) >= 0.75),
        "recall_20_30_ge_070": bool(max(max(r["recall_at_20pct"], r["recall_at_30pct"])
                                        for r in results.values()) >= 0.70),
    }
    verdict = "PASS" if all(gate.values()) else "FAIL"
    payload = {
        "n": len(rows), "positives": int(y.sum()),
        "feature_names": feature_names,
        "models": results, "gate": gate, "verdict": verdict,
        "note": "labels carry noise on non-CI-passing pairs (rho measured, ranking uncertain)",
    }
    (OUT / "metrics" / "e1_t2_predict.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
