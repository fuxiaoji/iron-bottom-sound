"""Shared bootstrap for the B10-B12 batches (E04 protocol reuse).

- rules-data snapshot discipline (borrowed from e04_torpedo_denial, which
  introduced it against a concurrently-regenerating derived-rules tree),
- provenance fingerprints (engine source + rules tree) written into every
  results.json so mid-run external mutations are detectable,
- one setup_cell() implementing the shared E04 same-turn protocol pipeline:
  sandbox -> turn 1 -> sealed turn-2 attacker plans -> TORPEDO_PLANNING,
  target plan space, J landscape, launch options.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.models import Side  # noqa: E402
from research.torpedo_denial.lane import (  # noqa: E402
    Lane,
    build_lane,
    build_ship_timeline,
    first_contact,
)
from research.torpedo_denial.protocol import (  # noqa: E402
    HORIZON_TURNS,
    LAUNCHED_TURN,
    expected_hull_fraction_per_hit,
)
from research.torpedo_denial.routes import Plan, enumerate_plans  # noqa: E402
from research.torpedo_denial.scenarios import (  # noqa: E402
    ATTACKER_PLAN,
    CA_ID,
    GEOMETRIES,
    Geometry,
    build_sandbox,
    enumerate_launch_options,
    progress_to_torpedo_planning,
    resolve_turn,
    seal_turn2_plans,
)

BASE_SEED = 20260910  # batch base seed (paired seeds derived from it)


def snapshot_rules_or_none(verbose: bool = True) -> str | None:
    """Reuse E04's snapshot machinery (waits for a consistent rules tree)."""
    from e04_torpedo_denial import _snapshot_rules

    try:
        snapshot = _snapshot_rules()
        if verbose:
            print(f"[rules] snapshot at {snapshot}")
        return snapshot
    except Exception as error:  # noqa: BLE001 - record, do not crash the batch
        print(f"[rules] snapshot unavailable ({error!r}); running on live tree")
        return None


def apply_rules_snapshot(snapshot: str | None) -> None:
    if not snapshot:
        return
    from e04_torpedo_denial import _apply_snapshot

    _apply_snapshot(snapshot)


def provenance() -> dict:
    """Fingerprints of everything the measurement depends on."""
    engine_path = REPO / "backend" / "src" / "iron_bottom_sound" / "engine.py"
    entries: dict[str, str] = {}
    tree = REPO / "resources" / "derived" / "structured"
    for path in sorted(tree.rglob("*")):
        if path.is_file():
            entries[str(path.relative_to(tree))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()[:16]
    tree_hash = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(entries.items())).encode()
    ).hexdigest()[:16]
    return {
        "engine_py_sha256_16": hashlib.sha256(engine_path.read_bytes()).hexdigest()[:16]
        if engine_path.exists()
        else None,
        "structured_tree_n_files": len(entries),
        "structured_tree_hash_16": tree_hash,
        "lane_eval_compat": "evaluate_contact accepts both current "
        "_torpedo_modifier(state, attacker, target, distance) and legacy API",
    }


@dataclass
class CellContext:
    """Everything the E04 same-turn protocol provides for one cell."""

    geometry: Geometry
    fleet: str
    seed: int
    engine: object
    state: object
    ca: object
    plans: list[Plan]
    j_values: list[float]
    j_ref: float
    tau0: Plan
    tau0_timeline: dict
    tau0_speeds: dict
    signature_j: dict[tuple, float]
    tied_top: list[tuple]
    tiers: list[float]
    attacker_hexes: list
    options: list
    threat_weight: float
    _lane_cache: dict = field(default_factory=dict, repr=False)

    def lane_for(self, option) -> Lane:
        key = option.lane_key
        if key not in self._lane_cache:
            self._lane_cache[key] = build_lane(
                self.engine, self.state, self.state.ships[option.ship_id],
                launch_hex=option.launch_hex, ship_heading=option.ship_heading,
                launch_side=option.launch_side, launch_angle=option.launch_angle,
                setting_index=option.setting_index, launch_at_mf=option.launch_at_mf,
                horizon_turn=HORIZON_TURNS, launched_turn=LAUNCHED_TURN,
            )
        return self._lane_cache[key]

    def timeline_for(self, plan: Plan) -> tuple[dict, dict]:
        return build_ship_timeline(
            self.engine, self.state, plan.trajectory, plan.end_hex,
            plan.end_heading, plan.cost, start_turn=LAUNCHED_TURN,
            horizon_turn=HORIZON_TURNS,
        )

    def contact_vs_tau0(self, option):
        return first_contact(
            self.engine, self.state, self.state.ships[option.ship_id], self.ca,
            self.lane_for(option), self.tau0_timeline, self.tau0_speeds,
            option.count, min_turn=LAUNCHED_TURN,
        )

    def crossing_pool(self) -> list[dict]:
        """E04 opportunity pool: options whose lane contacts the tau0* route."""
        pool = []
        for option in self.options:
            contact = self.contact_vs_tau0(option)
            if contact is not None:
                pool.append({
                    "option": option,
                    "lane": self.lane_for(option),
                    "e_hits_tau0": contact.expected_hits,
                    "p_hit_tau0": contact.hit_probability,
                    "contact_tau0": contact,
                })
        return pool


def setup_cell(geometry: Geometry, fleet: str, seed: int) -> CellContext:
    engine, state = build_sandbox(geometry, fleet, seed)
    ca = state.ships[CA_ID]
    progress_to_torpedo_planning(engine, state)
    resolve_turn(engine, state)
    seal_turn2_plans(engine, state)

    plan_strings = {
        ship.id: ATTACKER_PLAN for ship in state.ships.values()
        if ship.side == Side.AXIS
    }
    options = enumerate_launch_options(engine, state, plan_strings)

    plans = enumerate_plans(engine, state, ca)
    attacker_hexes = []
    for ship in state.ships.values():
        if ship.side == Side.AXIS and ship.position:
            position = ship.position
            for _ in range(int(ATTACKER_PLAN)):
                try:
                    position = position.neighbor(
                        ship.heading, columns=state.map_columns, rows=state.map_rows
                    )
                except ValueError:
                    break
            attacker_hexes.append(position)

    j_values = [
        engine.ship_gun_pressure(state, ca, position=plan.end_hex,
                                 heading=plan.end_heading,
                                 target_hexes=attacker_hexes)
        for plan in plans
    ]
    j_ref = max(j_values) if j_values else 0.0
    signature_j: dict[tuple, float] = {}
    for plan, value in zip(plans, j_values):
        signature_j.setdefault(plan.signature, value)
    tiers = sorted(set(signature_j.values()), reverse=True)
    tied_top = [sig for sig, value in signature_j.items() if value == j_ref]

    best_index = max(
        range(len(plans)),
        key=lambda i: (j_values[i], -plans[i].cost, plans[i].end_hex.label,
                       -plans[i].end_heading),
    )
    tau0 = plans[best_index]
    tau0_timeline, tau0_speeds = build_ship_timeline(
        engine, state, tau0.trajectory, tau0.end_hex, tau0.end_heading,
        tau0.cost, start_turn=LAUNCHED_TURN, horizon_turn=HORIZON_TURNS,
    )
    return CellContext(
        geometry=geometry, fleet=fleet, seed=seed, engine=engine, state=state,
        ca=ca, plans=plans, j_values=j_values, j_ref=j_ref, tau0=tau0,
        tau0_timeline=tau0_timeline, tau0_speeds=tau0_speeds,
        signature_j=signature_j, tied_top=tied_top, tiers=tiers,
        attacker_hexes=attacker_hexes, options=options,
        threat_weight=expected_hull_fraction_per_hit(
            engine, ca.displacement_band, ca.max_hull
        ),
    )
