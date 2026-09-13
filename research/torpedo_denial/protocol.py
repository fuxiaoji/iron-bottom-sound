"""E04 A/C/D measurement protocol (paired samples per seed).

Protocol: SAME-TURN perfect-information response (decision documented in the
E04 report).  The launch opportunity is drawn from the attacker's sealed
turn-2 plan; the target's best response is its turn-2 movement plan, chosen
knowing the launch parameters.  This mirrors the engine's own torpedo-assist
intercept model (same-turn launch/target co-timing) and is the regime in which
torpedo threats are live at all; a turn-1-launch variant was implemented first
and abandoned after the pilot scan showed its lanes structurally sweep the
target's turn-2 cells one turn early (all crossings become close broadsides).

No dice are consumed anywhere in the pipeline, so A/C/D samples share
byte-identical initial conditions.

Conditions:
    A (control)   tau0*  = argmax_plan J(plan)
    C (low-hit)   tauT*  = argmax_plan J(plan)/J_ref - w * P_hit(first contact)
                    sampled from launch opportunities whose expected direct
                    hits against the tau0* route are < DIRECT_HIT_THRESHOLD.
    D (threat-only) tauT*,D = argmax_plan J(plan)/J_ref - THREAT_ONLY_HAZARD * 1[first contact]
                    (expected damage replaced by a constant: pure lane-avoidance
                    motive, mechanism identification).
    B (direct, supplementary) = same measurement for opportunities with
                    expected hits >= threshold; feeds the decomposition figure.

Value definitions (plan 5.2, doctrine-free):
    J(plan)     = engine.ship_gun_pressure(target, position, heading,
                                            target_hexes = attacker turn-2 end hexes)
    Hazard(plan)= P_hit at the FIRST spatio-temporal contact between the
                  threatened lane and the plan's own timeline (turn-2 plan plus a
                  hold-course continuation), evaluated by engine functions at
                  the contact geometry.
    w           = expected hull fraction destroyed per torpedo hit, averaged
                  over the engine's own torpedo-collision table for the target's
                  displacement band (engine-grounded exchange rate between
                  "hit taken" and "position value", not a hand-tuned weight).
    V_denial    = J(tau0*) - J(tauT*)   (both evaluated with the threat-free J)
    V_direct    = expected direct hits on the tau0* route x target VP
                  (normalized variant: expected hits x w, the expected fraction
                  of the target's value destroyed).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import Side

from research.common import derive_seed
from research.torpedo_denial.lane import (
    Lane,
    build_lane,
    build_ship_timeline,
    first_contact,
)
from research.torpedo_denial.routes import Plan, enumerate_plans
from research.torpedo_denial.scenarios import (
    ATTACKER_PLAN,
    CA_ID,
    FLEETS,
    GEOMETRIES,
    Geometry,
    build_sandbox,
    enumerate_launch_options,
    progress_to_torpedo_planning,
    resolve_turn,
    seal_turn2_plans,
    validate_launch_options,
)

DIRECT_HIT_THRESHOLD = 0.15   # plan E04 condition C: expected direct hits below this
THREAT_ONLY_HAZARD = 1.0      # condition D: any contact counts as constant hazard
HORIZON_TURNS = 6             # lane/ship timeline horizon (lanes die well before)
LAUNCHED_TURN = 2             # same-turn threat


def expected_hull_fraction_per_hit(engine: IronBottomEngine, displacement_band: str, max_hull: int) -> float:
    """Engine-table exchange rate: mean hull fraction destroyed per torpedo hit."""
    from iron_bottom_sound.engine import parse_effect

    total = 0.0
    for die_one in range(1, 7):
        for die_two in range(1, 7):
            effect = engine.rules.torpedo_effect(die_one + die_two, displacement_band)
            hull, _speed, sunk, _fire = parse_effect(effect)
            total += 1.0 if sunk else min(1.0, hull / max(1, max_hull))
    return total / 36.0


@dataclass
class SeedSample:
    """Everything measured for one (geometry, fleet, seed) paired sample."""

    cell: str
    geometry: str
    fleet: str
    seed: int
    sample_kind: str = ""          # "low" (condition C) or "direct" (supplementary B)
    n_plans: int = 0
    j_ref: float = 0.0
    j_tied_top: int = 0
    j_tiers: int = 0
    threat_weight: float = 0.0
    options_total: int = 0
    cross_total: int = 0           # lanes crossing the tau0* route (turn>=2)
    cross_low: int = 0             # ... with expected hits < threshold
    cross_high: int = 0            # ... with expected hits >= threshold
    # sampled opportunity
    attacker_id: str = ""
    launcher_id: str = ""
    launch_side: str = ""
    launch_angle: str = ""
    setting_index: int = -1
    launch_at_mf: int = -1
    salvo: int = 0
    torpedo_heading: int = 0
    launch_hex: str = ""
    e_hits_direct: float = 0.0
    direct_aspect: str = ""
    direct_distance: int = 0
    direct_contact: str = ""
    # condition A baseline
    tau0_hex: str = ""
    tau0_heading: int = 0
    tau0_cost: int = 0
    tau0_plan: str = "0"
    tau0_j: float = 0.0
    # condition C (true hazard)
    c_route_changed: bool = False
    c_plan_changed: bool = False
    c_hex: str = ""
    c_heading: int = 0
    c_cost: int = 0
    c_plan: str = "0"
    c_j: float = 0.0
    c_denial: float = 0.0
    c_heading_change: int = 0
    c_speed_loss: int = 0
    c_deviation: int = 0
    c_contact: str = ""
    c_p_hit: float = 0.0
    # condition D (threat-only)
    d_route_changed: bool = False
    d_hex: str = ""
    d_heading: int = 0
    d_cost: int = 0
    d_j: float = 0.0
    d_denial: float = 0.0
    d_heading_change: int = 0
    d_speed_loss: int = 0
    d_deviation: int = 0
    d_contact: str = ""
    # sensitivity: raw plan weighting (J/J_ref - P_hit)
    c1_route_changed: bool = False
    c1_hex: str = ""
    c1_denial: float = 0.0
    c1_denial_norm: float = 0.0
    # decomposition (normalized value units)
    v_direct_vp: float = 0.0
    v_direct_norm: float = 0.0
    v_denial_norm: float = 0.0
    v_denial_d_norm: float = 0.0
    ca_vp: int = 0

    def as_row(self) -> dict:
        return asdict(self)


def _heading_distance(head_a: int, head_b: int) -> int:
    delta = abs(head_a - head_b) % 6
    return min(delta, 6 - delta)


def measure_seed(geometry_index: int, fleet_index: int, seed_index: int,
                 base_seed: int, validate_all: bool = True) -> list[SeedSample]:
    """Paired A(/B-supplementary)/C/D measurement for one seed.

    Returns up to two samples sharing the same baseline: the condition-C sample
    (low direct-hit opportunity) and the supplementary direct sample.
    """
    import numpy as np

    geometry_keys = sorted(GEOMETRIES)
    fleet_keys = sorted(FLEETS)
    geometry: Geometry = GEOMETRIES[geometry_keys[geometry_index]]
    fleet = fleet_keys[fleet_index]
    seed = derive_seed(base_seed, geometry_index + 1, fleet_index + 1, seed_index + 1)
    cell = f"{geometry.key}:{fleet}"

    engine, state = build_sandbox(geometry, fleet, seed)
    ca = state.ships[CA_ID]

    # ---- turn 1 (kinematics) then seal turn-2 attacker plans ----------------
    progress_to_torpedo_planning(engine, state)
    resolve_turn(engine, state)
    seal_turn2_plans(engine, state)

    plan_strings = {ship.id: ATTACKER_PLAN for ship in state.ships.values() if ship.side == Side.AXIS}
    options = enumerate_launch_options(engine, state, plan_strings)
    if validate_all:
        errors = validate_launch_options(engine, state, options, CA_ID)
        if errors:
            raise ValueError(f"invalid launch options on seed {seed}: {list(errors.items())[:3]}")

    # ---- the target's turn-2 decision space ---------------------------------
    plans = enumerate_plans(engine, state, ca)
    attacker_hexes = []
    for ship in state.ships.values():
        if ship.side == Side.AXIS and ship.position:
            position = ship.position
            for _ in range(int(ATTACKER_PLAN)):
                try:
                    position = position.neighbor(ship.heading, columns=state.map_columns, rows=state.map_rows)
                except ValueError:
                    break
            attacker_hexes.append(position)

    j_values = [
        engine.ship_gun_pressure(state, ca, position=plan.end_hex, heading=plan.end_heading,
                                 target_hexes=attacker_hexes)
        for plan in plans
    ]
    j_ref = max(j_values) if j_values else 0.0
    signature_values: dict[tuple, float] = {}
    for plan, j_value in zip(plans, j_values):
        signature_values.setdefault(plan.signature, j_value)
    j_tied_top = sum(1 for value in signature_values.values() if value == j_ref)
    j_tiers = len(set(signature_values.values()))
    threat_weight = expected_hull_fraction_per_hit(engine, ca.displacement_band, ca.max_hull)

    best_index = max(
        range(len(plans)),
        key=lambda i: (j_values[i], -plans[i].cost, plans[i].end_hex.label, -plans[i].end_heading),
    )
    tau0 = plans[best_index]
    tau0_timeline, tau0_speeds = build_ship_timeline(
        engine, state, tau0.trajectory, tau0.end_hex, tau0.end_heading, tau0.cost,
        start_turn=LAUNCHED_TURN, horizon_turn=HORIZON_TURNS,
    )

    def lane_for(option) -> Lane:
        attacker = state.ships[option.ship_id]
        return build_lane(
            engine, state, attacker,
            launch_hex=option.launch_hex, ship_heading=option.ship_heading,
            launch_side=option.launch_side, launch_angle=option.launch_angle,
            setting_index=option.setting_index, launch_at_mf=option.launch_at_mf,
            horizon_turn=HORIZON_TURNS, launched_turn=LAUNCHED_TURN,
        )

    # ---- direct-hit value of each opportunity against the tau0* route -------
    cross_high_options = []
    cross_low_options = []
    direct_values: dict[tuple, float] = {}
    direct_contacts: dict[tuple, object] = {}
    for option in options:
        lane = lane_for(option)
        contact = first_contact(
            engine, state, state.ships[option.ship_id], ca, lane,
            tau0_timeline, tau0_speeds, option.count, min_turn=LAUNCHED_TURN,
        )
        e_hits = contact.expected_hits if contact else 0.0
        direct_values[option.lane_key] = e_hits
        direct_contacts[option.lane_key] = contact
        if contact is not None:
            if e_hits < DIRECT_HIT_THRESHOLD:
                cross_low_options.append(option)
            else:
                cross_high_options.append(option)

    base = SeedSample(
        cell=cell, geometry=geometry.key, fleet=fleet, seed=seed,
        n_plans=len(plans), j_ref=j_ref, j_tied_top=j_tied_top, j_tiers=j_tiers,
        threat_weight=threat_weight,
        options_total=len(options),
        cross_total=len(cross_high_options) + len(cross_low_options),
        cross_low=len(cross_low_options), cross_high=len(cross_high_options),
        tau0_hex=tau0.end_hex.label, tau0_heading=tau0.end_heading,
        tau0_cost=tau0.cost, tau0_plan=tau0.plan_string, tau0_j=j_values[best_index],
        ca_vp=ca.vp,
    )

    rng = np.random.default_rng(derive_seed(base_seed, 777, geometry_index + 1, fleet_index + 1, seed_index + 1))

    def fill(chosen, kind: str) -> SeedSample:
        sample = replace(base)
        lane = lane_for(chosen)
        attacker = state.ships[chosen.ship_id]
        contact0 = direct_contacts[chosen.lane_key]
        sample.sample_kind = kind
        sample.attacker_id = chosen.ship_id
        sample.launcher_id = chosen.launcher_id
        sample.launch_side = chosen.launch_side
        sample.launch_angle = chosen.launch_angle
        sample.setting_index = chosen.setting_index
        sample.launch_at_mf = chosen.launch_at_mf
        sample.salvo = chosen.count
        sample.torpedo_heading = lane.torpedo_heading
        sample.launch_hex = chosen.launch_hex.label
        sample.e_hits_direct = direct_values[chosen.lane_key]
        if contact0 is not None:
            sample.direct_aspect = contact0.aspect
            sample.direct_distance = contact0.lane_distance
            sample.direct_contact = f"t{contact0.turn}.i{contact0.impulse}@{contact0.hex.label}"
        sample.v_direct_vp = sample.e_hits_direct * ca.vp
        sample.v_direct_norm = sample.e_hits_direct * threat_weight

        # ---- responses under C and D ----------------------------------------
        def response(variant: str) -> None:
            prefix = "c" if variant == "C" else "d"

            def contact_for(plan: Plan):
                timeline, speeds = build_ship_timeline(
                    engine, state, plan.trajectory, plan.end_hex, plan.end_heading,
                    plan.cost, start_turn=LAUNCHED_TURN, horizon_turn=HORIZON_TURNS,
                )
                return first_contact(
                    engine, state, attacker, ca, lane, timeline, speeds,
                    chosen.count, min_turn=LAUNCHED_TURN,
                )

            # Objective ties resolve toward minimal deviation from the baseline
            # tau0* (route inertia): a response counts as changed only when the
            # threat makes the baseline strictly suboptimal.
            def deviation(plan: Plan) -> tuple:
                return (
                    0 if plan.signature == tau0.signature else 1,
                    tau0.end_hex.distance(plan.end_hex),
                    abs(plan.cost - tau0.cost),
                    _heading_distance(plan.end_heading, tau0.end_heading),
                )

            best = None
            for plan, j_value in zip(plans, j_values):
                contact = contact_for(plan)
                normalized = j_value / j_ref if j_ref > 0 else 0.0
                if contact is None:
                    value = normalized
                elif variant == "C":
                    value = normalized - threat_weight * contact.hit_probability
                else:
                    value = normalized - THREAT_ONLY_HAZARD
                key = (-value, deviation(plan), plan.end_hex.label, plan.end_heading, plan.plan_string)
                if best is None or key < best[0]:
                    best = (key, plan, j_value, contact)
            _, tau, j_tau, contact = best
            setattr(sample, f"{prefix}_hex", tau.end_hex.label)
            setattr(sample, f"{prefix}_heading", tau.end_heading)
            setattr(sample, f"{prefix}_cost", tau.cost)
            setattr(sample, f"{prefix}_plan", tau.plan_string)
            setattr(sample, f"{prefix}_j", j_tau)
            denial = sample.tau0_j - j_tau
            setattr(sample, f"{prefix}_denial", denial)
            setattr(sample, f"{prefix}_route_changed", tau.signature != tau0.signature)
            setattr(sample, f"{prefix}_heading_change", _heading_distance(tau0.end_heading, tau.end_heading))
            setattr(sample, f"{prefix}_speed_loss", tau0.cost - tau.cost)
            setattr(sample, f"{prefix}_deviation", tau0.end_hex.distance(tau.end_hex))
            if variant == "C":
                sample.c_plan_changed = tau.plan_string != tau0.plan_string
                sample.c_contact = (
                    f"t{contact.turn}.i{contact.impulse}@{contact.hex.label}"
                    f"({contact.aspect},d{contact.lane_distance},m{contact.modifier:+d})" if contact else ""
                )
                sample.c_p_hit = contact.hit_probability if contact else 0.0
            else:
                sample.d_contact = f"t{contact.turn}.i{contact.impulse}@{contact.hex.label}" if contact else ""

        response("C")
        response("D")
        sample.v_denial_norm = sample.c_denial / j_ref if j_ref > 0 else 0.0
        sample.v_denial_d_norm = sample.d_denial / j_ref if j_ref > 0 else 0.0

        # Sensitivity: the plan's raw reading J' = J/J_ref - Hazard (weight 1.0
        # on the hit probability, no hull-damage exchange rate).  Reported as
        # c1_* fields; the low-hit conclusion is invariant to this choice.
        def response_raw() -> None:
            def contact_for(plan: Plan):
                timeline, speeds = build_ship_timeline(
                    engine, state, plan.trajectory, plan.end_hex, plan.end_heading,
                    plan.cost, start_turn=LAUNCHED_TURN, horizon_turn=HORIZON_TURNS,
                )
                return first_contact(
                    engine, state, attacker, ca, lane, timeline, speeds,
                    chosen.count, min_turn=LAUNCHED_TURN,
                )

            def deviation(plan: Plan) -> tuple:
                return (
                    0 if plan.signature == tau0.signature else 1,
                    tau0.end_hex.distance(plan.end_hex),
                    abs(plan.cost - tau0.cost),
                    _heading_distance(plan.end_heading, tau0.end_heading),
                )

            best = None
            for plan, j_value in zip(plans, j_values):
                contact = contact_for(plan)
                normalized = j_value / j_ref if j_ref > 0 else 0.0
                value = normalized - (contact.hit_probability if contact is not None else 0.0)
                key = (-value, deviation(plan), plan.end_hex.label, plan.end_heading, plan.plan_string)
                if best is None or key < best[0]:
                    best = (key, plan, j_value)
            _, tau, j_tau = best
            sample.c1_route_changed = tau.signature != tau0.signature
            sample.c1_hex = tau.end_hex.label
            sample.c1_denial = sample.tau0_j - j_tau
            sample.c1_denial_norm = sample.c1_denial / j_ref if j_ref > 0 else 0.0

        response_raw()
        return sample

    samples: list[SeedSample] = []
    if cross_low_options:
        samples.append(fill(cross_low_options[int(rng.integers(0, len(cross_low_options)))], "low"))
    if cross_high_options:
        samples.append(fill(cross_high_options[int(rng.integers(0, len(cross_high_options)))], "direct"))
    return samples
