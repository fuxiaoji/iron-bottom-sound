"""Extract strong, manually auditable G1 cases: board renders + Q tables.

Strong case = valid primary pair with the largest normalized regret, rendered
as a human-readable file: both branches' boards at the decision point, the two
hidden commitments (diff highlighted), the shared candidate set, the Q tables
under both value functions, and the regret decomposition.

    PYTHONPATH=backend/src:research/m1/g1/scripts .venv/bin/python \
        research/m1/g1/scripts/strong_cases.py [--top 6]
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import g1_lab as L  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameState, Side  # noqa: E402
from iron_bottom_sound.state_export import render_board  # noqa: E402

OUT = L.OUT


def load_state(tag_state: bytes) -> GameState:
    return GameState.model_validate_json(gzip.decompress(tag_state).decode())


def fmt_commitment(plan_map: dict, focus_ship: str) -> str:
    lines = []
    for ship_id, plan in plan_map.items():
        mark = "  <-- CHANGED" if ship_id == focus_ship else ""
        lines.append(f"  {ship_id:28s} plan='{plan}'{mark}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    # 15-replicate primary analysis (g1_analysis15.json), not the 5-rep pilot
    lines = json.loads((OUT / "g1_analysis15.json").read_text())
    valid = []
    for r in lines:
        if r["is_control_b"] or not r.get("regret"):
            continue
        cad = r.get("control_a_max_diff")
        if not (r["public_obs_equal"] and r["legal_actions_equal"]
                and r["own_sealed_equal"] and r["n_candidates_shared"] >= 2
                and cad is not None and cad < 1e-9):
            continue
        valid.append(r)
    # rank by normalized regret on the value function that has signal, prefer
    # primary; keep the union of top primary and top secondary
    # rank among CONFIDENT pairs only (the task's strong cases must be
    # statistically defensible), by regret on the value function where the
    # pair is confident
    def conf_regret(r):
        cands = []
        if r["regret"] and r["regret"]["q_ranking_confident"]:
            cands.append(r["regret"]["normalized_regret"])
        rd = r.get("regret_damage_diff")
        if rd and rd["q_ranking_confident"]:
            cands.append(rd["normalized_regret"])
        return max(cands) if cands else -1.0
    by_primary = sorted(valid, key=lambda r: -conf_regret(r))
    by_secondary = by_primary
    chosen, seen = [], set()
    for r in by_primary[:args.top] + by_secondary[:args.top]:
        if r["pair_id"] not in seen:
            seen.add(r["pair_id"])
            chosen.append(r)

    cases_dir = OUT / "strong_cases"
    cases_dir.mkdir(exist_ok=True)
    index = []
    for rank, r in enumerate(chosen, 1):
        st_a = load_state((OUT / "states" / f"{r['pair_id']}_A.json.gz").read_bytes())
        st_b = load_state((OUT / "states" / f"{r['pair_id']}_B.json.gz").read_bytes())
        eng_a = L.fresh_engine(st_a)
        eng_b = L.fresh_engine(st_b)
        board_a = render_board(st_a, eng_a, Side.ALLIES)
        board_b = render_board(st_b, eng_b, Side.ALLIES)
        reg, regd = r["regret"], r.get("regret_damage_diff")
        q_rows = []
        labels = [f"c{i}" + (f" ({n} torpedo)"
                             f"{' (chosen A)' if False else ''}")
                  for i, n in enumerate(r["candidate_labels"])]
        for i, lab in enumerate(labels):
            qa = r["Q"]["A"][i]
            qb = r["Q"]["B"][i]
            q_rows.append(
                f"| {lab} | {qa['outcome_mean']:+.2f} ± {qa['outcome_se']:.2f} "
                f"| {qb['outcome_mean']:+.2f} ± {qb['outcome_se']:.2f} "
                f"| {qa['damage_diff_mean']:+.3f} ± {qa['damage_diff_se']:.3f} "
                f"| {qb['damage_diff_mean']:+.3f} ± {qb['damage_diff_se']:.3f} |")
        v = r["variant"]
        body = f"""# Strong case {rank}: `{r['pair_id']}`

- scenario `{r['scenario']}`, seed {r['seed']}, turn {r['turn']}, phase torpedo_planning
- public observation identical: YES (sha {r['public_observation_hash']})
- legal action set identical: YES (sha {r['legal_action_hash']})
- own sealed movement identical: YES (sha {r['own_state_hash']})
- axis (hidden) view differs: {r['axis_view_differs']}

## Hidden axis movement commitment

**Branch A** (what the axis commander actually ordered):
```
{fmt_commitment(r['hidden_commitment_A'], v['ship_id'])}
```

**Branch B** (the alternative legal commitment):
```
{fmt_commitment(r['hidden_commitment_B'], v['ship_id'])}
```

Differing ship: `{v['ship_id']}` ({v['ship_name']}), plan '{v['from_plan']}' ->
'{v['to_plan']}', distance to nearest allies ship at decision time:
{v['min_dist_allies']} hexes.

## Public board at the decision point (identical in both branches; allies view)

Branch A board (byte-render; branch B renders identically because the public
observation hash is equal):
```
{board_a}
```

## Q tables (shared candidate set, {r['n_candidates_shared']} candidates, 5 dice-stream replicates)

| candidate | Q_outcome A | Q_outcome B | Q_damage A | Q_damage B |
|---|---|---|---|---|
{chr(10).join(q_rows)}

## Regret

- primary (outcome): V_A = {reg['V_A']:+.2f}, V_B = {reg['V_B']:+.2f},
  shared-action regret R = {reg['R']:.3f}, stake = {reg['stake']:.3f},
  **normalized = {reg['normalized_regret']:.3f}**,
  argmax differs = {reg['argmax_differs']},
  ranking confident = {reg['q_ranking_confident']}
- secondary (damage): normalized = {(regd or {}).get('normalized_regret', float('nan')):.3f}

## Why the public state cannot distinguish these situations

The allies' observation is hashed identical, so no snapshot-, history- or
belief-free representation that reads only the public state can tell world A
from world B. Yet the two worlds value the shared torpedo candidates
differently, because the enemy ships will be somewhere else when the torpedoes
arrive: the difference lives entirely in the axis sealed movement orders, which
the engine holds in `state.sealed_orders` and never exposes through
`observe()`.
"""
        path = cases_dir / f"{rank:02d}_{r['pair_id']}.md"
        path.write_text(body)
        index.append((rank, r["pair_id"], reg["normalized_regret"],
                      (regd or {}).get("normalized_regret"), path.name))
    (cases_dir / "INDEX.md").write_text(
        "# Strong cases (ranked)\n\n"
        "| # | pair | norm regret (outcome) | norm regret (damage) | file |\n|---|---|---|---|---|\n"
        + "\n".join(f"| {rk} | `{pid}` | {a:.3f} | {b:.3f} | [{f}]({f}) |"
                    for rk, pid, a, b, f in index) + "\n")
    print(f"wrote {len(index)} strong cases -> {cases_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
