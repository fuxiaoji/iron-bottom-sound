"""Pilot geometry survey for E04 (same-turn protocol).

Even with same-turn co-timing, contact requires the threatened lane and the
tau0* baseline route to meet at the same (turn, impulse); whether a geometry
yields both a direct-kill population (expected hits >= threshold) and a
low-hit population (expected hits < threshold, i.e. bow/stern shots at
torpedo travel >= 5 hexes) depends on the initial positions.  This module
scans a grid of candidate CA turn-2 start positions per family and reports
the lane-population counts; the chosen geometries are then hard-coded in
scenarios.GEOMETRIES with the pilot evidence cited in the E04 report.
No doctrine scores are involved anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass

from iron_bottom_sound.models import HexCoord, Side

from research.common import derive_seed, make_sandbox
from research.torpedo_denial.lane import build_lane, build_ship_timeline, first_contact
from research.torpedo_denial.protocol import (
    DIRECT_HIT_THRESHOLD,
    HORIZON_TURNS,
    LAUNCHED_TURN,
    expected_hull_fraction_per_hit,
)
from research.torpedo_denial.routes import enumerate_plans
from research.torpedo_denial.scenarios import (
    ATTACKER_PLAN,
    CA_ID,
    DD1_T1_START,
    DD2_T1_START,
    FLEETS,
    GEOMETRIES,
    Geometry,
    build_sandbox,
    enumerate_launch_options,
    progress_to_torpedo_planning,
    resolve_turn,
    seal_turn2_plans,
)


@dataclass(frozen=True)
class GeometryCandidate:
    family: str
    ca_t2_start: tuple[int, int]   # CA position at start of turn 2 (q, r)
    ca_heading: int

    @property
    def key(self) -> str:
        return f"{self.family}:t2=({self.ca_t2_start[0]},{self.ca_t2_start[1]}):h{self.ca_heading}"

    def geometry(self) -> Geometry:
        return Geometry(f"pilot-{self.key}", self.key, self.ca_t2_start, self.ca_heading)


def survey_candidate(candidate: GeometryCandidate, seed: int, fleet: str = "1v1") -> dict:
    """One pilot measurement: lane-population counts against tau0*."""
    geometry = candidate.geometry()
    engine, state = build_sandbox(geometry, fleet, seed)
    ca = state.ships[CA_ID]

    progress_to_torpedo_planning(engine, state)
    resolve_turn(engine, state)
    seal_turn2_plans(engine, state)

    plan_strings = {ship.id: ATTACKER_PLAN for ship in state.ships.values() if ship.side == Side.AXIS}
    options = enumerate_launch_options(engine, state, plan_strings)

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
    best_index = max(range(len(plans)),
                     key=lambda i: (j_values[i], -plans[i].cost, plans[i].end_hex.label, -plans[i].end_heading))
    tau0 = plans[best_index]
    tau0_timeline, tau0_speeds = build_ship_timeline(
        engine, state, tau0.trajectory, tau0.end_hex, tau0.end_heading, tau0.cost,
        start_turn=LAUNCHED_TURN, horizon_turn=HORIZON_TURNS,
    )

    t1_contacts = 0   # (same-turn protocol: contacts at launch impulses 1..3 vs pre-launch route)
    cross_high = 0
    cross_low = 0
    cross_low_far = 0   # low-hit crossings at torpedo distance >= 16 (modifier -1)
    cross_total = 0
    aspects_low = []
    d_values_low = []
    e_values_high = []
    for option in options:
        lane = build_lane(
            engine, state, state.ships[option.ship_id],
            launch_hex=option.launch_hex, ship_heading=option.ship_heading,
            launch_side=option.launch_side, launch_angle=option.launch_angle,
            setting_index=option.setting_index, launch_at_mf=option.launch_at_mf,
            horizon_turn=HORIZON_TURNS, launched_turn=LAUNCHED_TURN,
        )
        contact = first_contact(
            engine, state, state.ships[option.ship_id], ca, lane,
            tau0_timeline, tau0_speeds, option.count, min_turn=LAUNCHED_TURN,
        )
        if contact is None:
            continue
        cross_total += 1
        if contact.expected_hits < DIRECT_HIT_THRESHOLD:
            cross_low += 1
            if contact.lane_distance >= 16:
                cross_low_far += 1
            aspects_low.append(contact.aspect)
            d_values_low.append(contact.lane_distance)
        else:
            cross_high += 1
            e_values_high.append(contact.expected_hits)

    return {
        "candidate": candidate.key,
        "family": candidate.family,
        "seed": seed,
        "n_options": len(options),
        "n_plans": len(plans),
        "tau0": f"{tau0.end_hex.label}/h{tau0.end_heading}/c{tau0.cost}",
        "tau0_j": j_values[best_index],
        "j_ref": max(j_values),
        "threat_weight": expected_hull_fraction_per_hit(engine, ca.displacement_band, ca.max_hull),
        "cross_total": cross_total,
        "cross_high": cross_high,
        "cross_low": cross_low,
        "cross_low_far": cross_low_far,
        "aspects_low": ",".join(sorted(set(aspects_low))),
        "d_low_min": min(d_values_low, default=0),
        "e_high_min": min(e_values_high, default=0.0),
    }


# ---------------------------------------------------------------------------
# candidate grids per geometry family (DD turn-2 course runs NE from (19,9);
# scan sweeps the CA's turn-2 start over a rectangle per family heading).
# ---------------------------------------------------------------------------

FAMILY_HEADINGS = {
    "opposing": (3, 4),    # CA closes S/SW toward the DD line
    "chase": (1,),         # CA flees NE (DD astern) or pursues along the axis
    "crossing": (2, 5),    # CA rail crosses the DD lane fan
}
SCAN_Q = range(14, 27, 2)
SCAN_R = range(-2, 25, 2)


def family_candidates(family: str) -> list[GeometryCandidate]:
    candidates = []
    for heading in FAMILY_HEADINGS[family]:
        for q in SCAN_Q:
            for r in SCAN_R:
                candidates.append(GeometryCandidate(family, (q, r), heading))
    return candidates


def run_pilot(seeds: list[int], families: tuple[str, ...] = ("opposing", "chase", "crossing"),
              out_path=None) -> list[dict]:
    """Scan all candidates; aggregate over seeds; print a ranked table."""
    records = []
    for family in families:
        for candidate in family_candidates(family):
            for seed in seeds:
                try:
                    records.append(survey_candidate(candidate, seed))
                except Exception as error:  # noqa: BLE001 - pilot must survive bad candidates
                    records.append({"candidate": candidate.key, "family": family,
                                    "seed": seed, "error": repr(error)})
    agg: dict[str, dict] = {}
    for record in records:
        if "error" in record:
            continue
        stats = agg.setdefault(record["candidate"], {
            "family": record["family"], "n": 0, "cross_low": 0.0, "cross_low_far": 0.0,
            "cross_high": 0.0, "cross_total": 0.0, "seeds_with_low": 0, "seeds_with_high": 0,
        })
        stats["n"] += 1
        stats["cross_low"] += record["cross_low"]
        stats["cross_low_far"] += record["cross_low_far"]
        stats["cross_high"] += record["cross_high"]
        stats["cross_total"] += record["cross_total"]
        if record["cross_low"] > 0:
            stats["seeds_with_low"] += 1
        if record["cross_high"] > 0:
            stats["seeds_with_high"] += 1
    ranked = sorted(
        agg.items(),
        key=lambda item: (min(item[1]["seeds_with_low"], item[1]["seeds_with_high"]),
                          item[1]["seeds_with_low"] + item[1]["seeds_with_high"],
                          item[1]["cross_low"]),
        reverse=True,
    )
    lines = [f"{'candidate':40s} {'fam':9s} n low lowFar high tot seeds_low seeds_high"]
    for key, stats in ranked:
        if stats["cross_low"] + stats["cross_high"] == 0:
            continue
        n = stats["n"]
        lines.append(
            f"{key:40s} {stats['family']:9s} {n} "
            f"{stats['cross_low'] / n:4.1f} {stats['cross_low_far'] / n:4.1f} "
            f"{stats['cross_high'] / n:4.1f} {stats['cross_total'] / n:4.1f} "
            f"{stats['seeds_with_low']}/{n} {stats['seeds_with_high']}/{n}"
        )
    report = "\n".join(lines)
    print(report)
    if out_path:
        out_path.write_text(report + "\n\n" + "\n".join(str(r) for r in records) + "\n", encoding="utf-8")
    return records
