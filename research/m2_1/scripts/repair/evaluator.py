"""M2.1-R repaired evaluator: derived-seed replicates, explicit checkpoints,
identical pipeline for every arm (baseline included), gunnery branch fixed.

Replicate scheme (PI fix #2): replicate j of snapshot S uses
    derived_seed = int(sha256(f"{S}|{j}").hexdigest()[:8], 16)
    state.seed   = derived_seed          (RNG streams fully re-keyed)
    state.rng_counter = <branch-point counter>   (unchanged: same decision point)
All action arms of replicate j share derived_seed -> matched-seed at the seed
level; different replicates are disjoint streams.  Called matched-seed, never
CRN.

Checkpoints (PI fix #4), all evaluated from the focal side's perspective:
    P0       candidate phase legally resolved (movement -> post
             MOVEMENT_RESOLUTION; gunnery -> post GUNNERY resolution;
             torpedo -> post TORPEDO_EFFECTS)
    T0       end of the current full turn (after FIRE_END of turn0)
    T1       end of the next full turn
    T2       end of the one after
    Terminal game complete
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys_paths = [REPO / "backend" / "src", REPO / "research" / "m2_1" / "scripts"]
for p in sys_paths:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import sys  # noqa: E402

from repair.value_panel import u1_material  # noqa: E402


def derived_seed(snapshot_id: str, replicate: int) -> int:
    h = hashlib.sha256(f"{snapshot_id}|{replicate}".encode()).hexdigest()
    return int(h[:8], 16)


def _post_candidate_phase(layer: str) -> str:
    return {"movement": "movement_resolution",
            "gunnery": "torpedo_effects",
            "torpedo": "fire_end"}[layer]


def _phase_of_layer(layer: str):
    from iron_bottom_sound.models import Phase
    return {"movement": Phase.MOVEMENT_PLANNING,
            "gunnery": Phase.GUNNERY,
            "torpedo": Phase.TORPEDO_PLANNING}[layer]


def run_arm(state0, cand_json, layer, side_value, profile_pair, replicate: int,
            checkpoints=("P0", "T0", "T1", "T2"), max_turns_after=4):
    """One arm of one replicate.  ``cand_json`` is REQUIRED (the baseline is an
    explicit candidate upstream — PI fix #5); returns {checkpoint: {U0, U1}} or
    None on rejection/failure."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameState, OrderBatch, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander

    side = Side(side_value)
    seed = derived_seed(f"{state0.game_id}|{state0.turn}|{layer}|{side_value}",
                        replicate)
    st = state0.model_copy(deep=True)
    st.seed = seed                      # streams re-keyed; counter untouched
    eng = IronBottomEngine()
    eng.games[st.game_id] = st

    if cand_json is None:
        raise ValueError("baseline must be an explicit candidate (PI fix #5)")
    batch = OrderBatch.model_validate_json(cand_json)
    batch.side = side
    batch.phase = _phase_of_layer(layer)
    if not eng.validate_orders(st.game_id, batch).valid:
        return None
    eng.submit_orders(st.game_id, batch)

    sessions = {
        Side.AXIS: TacticalCommander(profile=PROFILES[profile_pair[0]]),
        Side.ALLIES: TacticalCommander(profile=PROFILES[profile_pair[1]]),
    }
    roster_vp = {s.id: s.vp for s in st.ships.values()}
    turn0 = st.turn
    panels = {}
    resolved_p0 = False
    guard = 0
    while guard < 400:
        guard += 1
        # ---- checkpoint detection BEFORE advancing this tick ----
        phase_name = st.phase.value
        if not resolved_p0 and phase_name == _post_candidate_phase(layer):
            resolved_p0 = True
            panels["P0"] = _panel(st, side, roster_vp)
        if resolved_p0 and phase_name == "reinforcement" and st.turn == turn0 + 1:
            panels.setdefault("T0", _panel(st, side, roster_vp))
        if resolved_p0 and phase_name == "reinforcement" and st.turn == turn0 + 2:
            panels.setdefault("T1", _panel(st, side, roster_vp))
        if resolved_p0 and phase_name == "reinforcement" and st.turn == turn0 + 3:
            panels.setdefault("T2", _panel(st, side, roster_vp))
        if st.phase == Phase.COMPLETE:
            panels["Terminal"] = _panel(st, side, roster_vp)
            for c in checkpoints:
                panels.setdefault(c, panels["Terminal"])
            return panels
        if all(c in panels for c in checkpoints):
            return panels
        # ---- scripted continuation ----
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = sessions[s].choose_plan(eng, st.game_id, s)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return None
        eng.advance(st.game_id)
    return panels if resolved_p0 else None


def _panel(st, side, roster_vp):
    from iron_bottom_sound.models import Phase, Side
    u0 = 0.0
    if st.phase == Phase.COMPLETE:
        if st.winner is not None:
            u0 = 1.0 if st.winner == side else -1.0
    u1 = u1_material(st, side.value, roster_vp)
    return {"U0": u0, "U1": u1}


def native_panel(state0, cand_json, layer, side_value, profile_pair, replicate,
                 scenario_id):
    """Scenario-native values alongside U1: native score margin for EM-01;
    for S-03 the distance/progress to the sunk-or-2-2-2 threshold."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameState, OrderBatch, Phase, Side
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    side = Side(side_value)
    seed = derived_seed(f"{state0.game_id}|{state0.turn}|{layer}|{side_value}",
                        replicate)
    st = state0.model_copy(deep=True)
    st.seed = seed
    eng = IronBottomEngine()
    eng.games[st.game_id] = st
    if cand_json is None:
        raise ValueError("baseline must be explicit")
    batch = OrderBatch.model_validate_json(cand_json)
    batch.side = side
    batch.phase = _phase_of_layer(layer)
    if not eng.validate_orders(st.game_id, batch).valid:
        return None
    eng.submit_orders(st.game_id, batch)
    sessions = {
        Side.AXIS: TacticalCommander(profile=PROFILES[profile_pair[0]]),
        Side.ALLIES: TacticalCommander(profile=PROFILES[profile_pair[1]]),
    }
    out = {}
    turn0 = st.turn
    guard = 0
    resolved = False
    while guard < 400:
        guard += 1
        if not resolved and st.phase.value == _post_candidate_phase(layer):
            resolved = True
            out["P0"] = _native(st, scenario_id, side)
        if resolved and st.phase == Phase.COMPLETE:
            out["Terminal"] = _native(st, scenario_id, side)
            out.setdefault("T0", out["Terminal"])
            out.setdefault("T1", out["Terminal"])
            out.setdefault("T2", out["Terminal"])
            return out
        if resolved and st.phase.value == "reinforcement":
            if st.turn == turn0 + 1:
                out.setdefault("T0", _native(st, scenario_id, side))
            if st.turn == turn0 + 2:
                out.setdefault("T1", _native(st, scenario_id, side))
            if st.turn == turn0 + 3:
                out.setdefault("T2", _native(st, scenario_id, side))
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for s in Side:
                if s.value not in st.submitted_orders:
                    b = sessions[s].choose_plan(eng, st.game_id, s)[1]
                    res = eng.submit_orders(st.game_id, b)
                    if not res.valid:
                        return None
        eng.advance(st.game_id)
        if st.turn > turn0 + 3 + 1:
            break
    return out


def _native(st, scenario_id, side):
    other = Side.ALLIES if side == Side.AXIS else Side.AXIS
    d = {"native_margin": st.score[side.value] - st.score[other.value]}
    if scenario_id == "IBS-S-03":
        axis_ships = [s for s in st.ships.values() if s.side == Side.AXIS]
        qual = sum(1 for s in axis_ships
                   if s.sunk or (s.speed_track and all(sp <= 2 for sp in s.speed_track)))
        d["s03_qualifying_dd"] = qual
        d["s03_progress"] = qual / 2.0   # 2 DDs to sink/cripple for ally win
    return d
