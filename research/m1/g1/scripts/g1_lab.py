"""G1 lab — natural commitment-induced decision aliasing in Iron Bottom Sound.

Window under test (priority 1 of the M1 plan):

    MOVEMENT_PLANNING  (both sides submit; engine seals)
      -> TORPEDO_PLANNING  (both sides decide torpedoes while the *enemy's*
         movement orders are sealed, unexecuted and invisible)
      -> advance -> movement resolution -> gunnery -> torpedo effects -> ...

Pair construction (legal pipeline only, no state surgery):

  1. run a real match (TacticalCommander balanced vs balanced) to
     MOVEMENT_PLANNING at a target turn;
  2. X_A = the axis commander's own movement batch; Y = the allies batch;
  3. X_B = X_A with ONE axis ship's plan replaced by another plan drawn from
     `engine.movement_candidates` (the engine's own legal alternatives for that
     ship at that state);
  4. branch A: validate+submit X_A, validate+submit Y, advance;
     branch B: same with X_B (fresh clone of the pre-state each time);
  5. at TORPEDO_PLANNING hash both branches' allies observation, allies legal
     actions and allies own sealed movement — a pair is valid only if all equal;
  6. Q_x(a) = mean final VP differential (allies - axis) over R dice-stream
     replicates (common random numbers: both branches reuse the same offsets;
     the strategic state is never touched - only state.rng_counter, the engine's
     dice stream position, is advanced to sample outcome variance).

Controls:
  A  same commitment twice  -> pipeline determinism check (regret must be 0)
  B  distant-ship variant   -> hidden difference predicted irrelevant
                               (post-hoc interaction audit filters)
  C  per-world oracle action -> regret 0 by construction (upper bound check)

All numbers produced here are exact continuations of scripted play - there is no
learning and no heuristic score is used as a Q value.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.tactical import TacticalCommander  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402

OUT = REPO / "research" / "m1" / "g1"
PROFILES = ("balanced", "balanced")          # axis, allies (pre-declared)
SCENARIOS = ("IBS-S-03", "IBS-S-01")         # pre-declared
TARGET_TURNS = (1, 2, 3, 4)                  # pre-declared
SEEDS = tuple(range(1, 13))                  # pre-declared
MAX_VARIANTS_PER_NODE = 3                    # pre-declared
MAX_CANDIDATES = 6                           # pre-declared
REPLICATES = 5                               # pre-declared (dice streams)
TIE_EPS = 1e-9
ADVANCE_GUARD = 400

PAIRS_JSONL = OUT / "IBS_ALIAS_PAIRS.jsonl"
STATES_DIR = OUT / "states"
LOG = OUT / "logs"


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()[:16]


def fresh_engine(state) -> IronBottomEngine:
    eng = IronBottomEngine()
    eng.games[state.game_id] = state
    return eng


def _validate(eng, state, batch: OrderBatch, tag: str, errors: list):
    res = eng.validate_orders(state.game_id, batch)
    if not res.valid:
        errors.append({tag: res.errors})
    return res.valid


def movement_alts(eng: IronBottomEngine, state, ship_id: str, own_plan: str):
    """Legal alternative plan strings for one axis ship, from the engine."""
    ship = state.ships[ship_id]
    info = eng.movement_candidates(state, ship, include_plans=True)
    plans = {}
    for entry in info.get("reachable", []):
        plan = entry.get("plan")
        if plan is not None:
            plans[plan] = entry.get("cost", entry.get("speed", 0))
    alts = []
    if own_plan in plans or True:
        # hold alternative
        if "0" in plans and own_plan != "0":
            alts.append(("0", plans["0"]))
        # aggressive alternative: max-cost plan
        if plans:
            best = max(plans.items(), key=lambda kv: kv[1])
            if best[0] != own_plan and best[0] != "0":
                alts.append(best)
    return alts[:2]


def build_variants(eng, state, x_a: OrderBatch, allies_state, max_variants: int):
    """Variant axis batches: replace ONE ship's plan with a legal alternative.

    Returns (main_variants, control_variant) where main variants pick the axis
    ships CLOSEST to the allies (decision-relevant) and the control variant
    picks the FARTHEST ship (predicted decision-irrelevant).
    """
    state2 = state  # MOVEMENT_PLANNING state (pre-advance)
    ships = [s for s in state2.ships.values()
             if s.side == Side.AXIS and not s.sunk and s.position]
    allies_pos = [s.position for s in state2.ships.values()
                  if s.side == Side.ALLIES and not s.sunk and s.position]
    if not allies_pos:
        return [], None
    def min_dist(ship):
        return min(ship.position.distance(p) for p in allies_pos)
    plan_of = {o.ship_id: o for o in x_a.movement}
    ranked = sorted(ships, key=min_dist)
    main, control = [], None
    for ship in ranked:  # closest first
        if len(main) >= max_variants:
            break
        order = plan_of.get(ship.id)
        if order is None:
            continue
        for plan, cost in movement_alts(eng, state2, ship.id, order.plan):
            xb = x_a.model_copy(deep=True)
            for o in xb.movement:
                if o.ship_id == ship.id:
                    o.plan = plan
                    if cost is not None:
                        o.speed = cost
            if xb.model_dump_json() == x_a.model_dump_json():
                continue
            main.append({"ship_id": ship.id, "ship_name": ship.name,
                         "from_plan": order.plan, "to_plan": plan,
                         "min_dist_allies": min_dist(ship), "batch": xb})
            break  # one alternative per ship
    for ship in reversed(ranked):  # farthest ship for Control B
        order = plan_of.get(ship.id)
        if order is None:
            continue
        for plan, cost in movement_alts(eng, state2, ship.id, order.plan):
            xb = x_a.model_copy(deep=True)
            for o in xb.movement:
                if o.ship_id == ship.id:
                    o.plan = plan
                    if cost is not None:
                        o.speed = cost
            if xb.model_dump_json() == x_a.model_dump_json():
                continue
            control = {"ship_id": ship.id, "ship_name": ship.name,
                       "from_plan": order.plan, "to_plan": plan,
                       "min_dist_allies": min_dist(ship), "batch": xb}
            break
        break
    return main, control


def make_branch(pre_state, x: OrderBatch, y: OrderBatch, errors: list):
    """Seal X (axis) + Y (allies) on a fresh clone; return branch data."""
    st = pre_state.model_copy(deep=True)
    eng = fresh_engine(st)
    if not _validate(eng, st, x, "axis_movement", errors):
        return None
    eng.submit_orders(st.game_id, x)
    if not _validate(eng, st, y, "allies_movement", errors):
        return None
    eng.submit_orders(st.game_id, y)
    eng.advance(st.game_id)
    if st.phase != Phase.TORPEDO_PLANNING:
        errors.append({"phase": str(st.phase)})
        return None
    obs = eng.observe(st.game_id, Side.ALLIES)
    legal = eng.legal_actions(st.game_id, Side.ALLIES)
    own_sealed = [b.model_dump(mode="json")
                  for b in eng._sealed_batches(st, Phase.MOVEMENT_PLANNING)
                  if b.side == Side.ALLIES]
    axis_view = eng.observe(st.game_id, Side.AXIS)
    return {
        "state": copy.deepcopy(st),
        "engine": eng,
        "public_obs_hash": sha(obs.model_dump(mode="json")),
        "legal_hash": sha([a.model_dump(mode="json") for a in legal]),
        "own_sealed_hash": sha(own_sealed),
        "axis_view_hash": sha(axis_view.model_dump(mode="json")),
        "c0": st.rng_counter,
    }


def torpedo_candidates(eng: IronBottomEngine, state, chosen_a, chosen_b):
    """Shared candidate torpedo batches (identical across branches)."""
    cands = []
    seen = set()

    def add(batch: OrderBatch):
        batch.phase = Phase.TORPEDO_PLANNING
        key = batch.model_dump_json()
        if key not in seen:
            seen.add(key)
            cands.append(batch)

    empty = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
    add(empty)
    for b in (chosen_a, chosen_b):
        if b is not None and b.torpedoes:
            add(b.model_copy(deep=True))
    # engine assist recommendations: top-2 combos for the top-2 own ships
    try:
        from iron_bottom_sound.models import HexCoord, TorpedoOrder
        assist = eng.torpedo_assist(state, Side.ALLIES)
        per_ship = {}
        for combo in assist.get("combos", []):
            if combo.get("blocked_reason") or combo.get("friendly_risk"):
                continue
            per_ship.setdefault(combo["ship_id"], []).append(combo)
        for ship_id, combos in list(per_ship.items())[:2]:
            for c in combos[:2]:
                batch = OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
                batch.torpedoes = [TorpedoOrder(
                    ship_id=c["ship_id"], launcher_id=c["launcher_id"],
                    count=c["salvo_size"], launch_at_mf=c["launch_at_mf"],
                    launch_hex=HexCoord.from_label(c["launch_hex"]),
                    bearing=c["launch_heading"], launch_side=c["launch_side"],
                    launch_angle=c["launch_angle"], setting_index=c["setting_index"])]
                add(batch)
    except Exception:
        pass
    return cands[:MAX_CANDIDATES]


def commander_torpedo_batch(state) -> OrderBatch:
    from iron_bottom_sound.tactical import PROFILES as TAC_PROFILES
    eng = fresh_engine(state.model_copy(deep=True))
    cmd = TacticalCommander(profile=TAC_PROFILES[PROFILES[1]])
    return cmd.choose_plan(eng, state.game_id, Side.ALLIES)[1]


# --------------------------------------------------------------------------
# continuation evaluation
# --------------------------------------------------------------------------


def _hull(state, side: Side) -> float:
    return sum(max(0.0, s.hull or 0.0) for s in state.ships.values()
               if s.side == side)


def _continuation(st, allies_batch, profile_allies: str, profile_axis: str):
    """Submit allies_batch at TORPEDO_PLANNING, then script the rest of the game.

    Value functions (pre-declared, see Q_ESTIMATION_METHOD.md):
      outcome      +1 allies win / 0 draw / -1 axis win (the true game value)
      damage_diff  (axis hull lost - allies hull lost) / total initial hull,
                   measured over the continuation only; in [-1, 1]
    """
    from iron_bottom_sound.tactical import PROFILES
    try:
        eng = fresh_engine(st)
        if not eng.validate_orders(st.game_id, allies_batch).valid:
            return {"outcome": None, "damage_diff": None, "turns": None,
                    "error": "candidate rejected"}
        eng.submit_orders(st.game_id, allies_batch)
        hull0_axis = _hull(st, Side.AXIS)
        hull0_allies = _hull(st, Side.ALLIES)
        total_hull = hull0_axis + hull0_allies
        sessions = {
            Side.AXIS: TacticalCommander(profile=PROFILES[profile_axis]),
            Side.ALLIES: TacticalCommander(profile=PROFILES[profile_allies]),
        }
        guard = 0
        while st.phase != Phase.COMPLETE:
            guard += 1
            if guard > ADVANCE_GUARD:
                return {"outcome": None, "damage_diff": None, "turns": None,
                        "error": "advance guard hit"}
            if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                            Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                            Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
                for side in Side:
                    if side.value not in st.submitted_orders:
                        batch = sessions[side].choose_plan(eng, st.game_id, side)[1]
                        eng.submit_orders(st.game_id, batch)
            eng.advance(st.game_id)
        winner = st.winner if hasattr(st, "winner") else None
        outcome = 0.0
        if winner is not None:
            outcome = 1.0 if winner == Side.ALLIES else -1.0
        damage_diff = ((hull0_axis - _hull(st, Side.AXIS))
                       - (hull0_allies - _hull(st, Side.ALLIES)))
        if total_hull > 0:
            damage_diff /= total_hull
        return {"outcome": outcome, "damage_diff": damage_diff,
                "turns": st.turn, "error": None, "score": dict(st.score)}
    except Exception as exc:  # noqa: BLE001 - record, never hide
        return {"outcome": None, "damage_diff": None, "turns": None,
                "error": f"{type(exc).__name__}: {exc}"}


def eval_branch_state(branch_state_json: str, cand_json: str, replicate: int):
    """Worker: one (branch, candidate, dice-stream) continuation."""
    from iron_bottom_sound.models import GameState
    st = GameState.model_validate_json(branch_state_json)
    st.rng_counter = st.rng_counter + replicate  # dice-stream sampling only
    batch = OrderBatch.model_validate_json(cand_json)
    return _continuation(st, batch, PROFILES[1], PROFILES[0])
