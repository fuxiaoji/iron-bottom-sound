"""Replay a recorded battle from its order log, verify it, and render frames.

Two jobs, one code path, because they must agree: the frames a documentary shows have
to come from the *same* states the battle actually passed through.

**Verify.**  The battle record keeps every order batch the engine accepted
(``orders.jsonl``).  Feeding those batches back into a fresh engine must reproduce the
battle: same final turn and phase, same ship positions, same hull values.  This is the
check the previous battle could not pass, because its driver never persisted the
batches - it could only be audited as a record.

**Render.**  With the state reproduced exactly, any phase can be drawn from any of the
three viewpoints the documentary uses: ``axis`` (what the Japanese commander's own
ships can see), ``allies``, and ``god`` (the union, which is the truth).  Stills rather
than invented in-between states: the video pans and dissolves between real frames
instead of tweening ships to places the engine never put them.

Usage::

    .venv/bin/python research/battle_video/replay_battle.py --battle battle_em01 --verify
    .venv/bin/python research/battle_video/replay_battle.py --battle battle_em01 --render
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import battle_report  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import default_setup_orders  # noqa: E402

BATTLE_ROOT = ROOT / "research" / "command_delay"
VIEWS = ("god", "axis", "allies")

# The phases worth a still: the ones where the map changed or a decision landed.
RENDER_PHASES = (
    # FORMATION_SETUP is the opening board - the film's first map, and the only frame in
    # which the battle line is intact.
    Phase.FORMATION_SETUP, Phase.MOVEMENT_PLANNING, Phase.MOVEMENT_RESOLUTION,
    Phase.GUNNERY, Phase.TORPEDO_EFFECTS, Phase.FIRE_END,
)


def load_orders(battle_dir: Path) -> dict[tuple[int, str, str], OrderBatch]:
    orders: dict[tuple[int, str, str], OrderBatch] = {}
    path = battle_dir / "orders.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (int(row["turn"]), row["phase"], row["side"])
        orders[key] = OrderBatch(**row["batch"])
    return orders


def replay(battle_dir: Path, frame_dir: Path | None = None, *,
           viewpoints: tuple[str, ...] = VIEWS, crop: bool = True,
           model_traffic: bool = True) -> dict:
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    orders = load_orders(battle_dir)
    policy_counts = {"formation": 0, "fleet": 0}
    if model_traffic:
        # Re-serve the models' own replies: the message traffic they authored is part of
        # the battle, and without it the replay fights a different one.
        from recorded_policies import provider_policies_from_record

        policy_counts, _ = provider_policies_from_record(battle)
    scenario = battle.get("scenario", "IBS-S-EM-01")
    seed = int(battle["seed"])

    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    used: set[tuple[int, str, str]] = set()
    missing: list[str] = []
    rendered = 0
    frames: list[dict] = []
    phase_mismatches: list[str] = []
    phases_compared = 0
    views = {}
    for path in sorted((battle_dir / "views").glob("*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        views[(snapshot["turn"], snapshot["phase"])] = snapshot

    def compare_phase() -> None:
        """The replay must reproduce every recorded snapshot, not just the last one.

        Comparing only the end state hides a divergence that later events paper over,
        and comparing against a mid-turn snapshot while the replay has run on past it
        reports a difference that is only the extra final phase.
        """
        nonlocal phases_compared
        snapshot = views.get((state.turn, state.phase.value))
        if snapshot is None:
            return
        phases_compared += 1
        recorded = snapshot["god"]["ships"]
        for ship in state.ships.values():
            row = recorded.get(ship.id)
            if row is None:
                continue
            mine = {
                "position": ship.position.label if ship.position else None,
                "heading": ship.heading, "speed": ship.current_speed,
                "hull": ship.hull, "sunk": bool(ship.sunk),
                "command_status": ship.command_status,
            }
            for field_name, value in mine.items():
                if field_name == "sunk":
                    expected = bool(row["sunk"])
                else:
                    expected = row[field_name]
                if value != expected:
                    phase_mismatches.append(
                        f"T{state.turn} {state.phase.value} {ship.id}: "
                        f"{field_name} {value!r} != recorded {expected!r}"
                    )

    def render_phase(out_opening: tuple[int, str] | None = None) -> None:
        nonlocal rendered
        if frame_dir is None:
            return
        turn, phase_name = (out_opening or (state.turn, state.phase.value))
        for viewpoint in viewpoints:
            image = battle_report.render_map_image(
                state, engine, Side.AXIS, viewpoint=viewpoint,
            )
            name = f"t{turn:02d}-{phase_name}-{viewpoint}.png"
            image.save(frame_dir / name, optimize=True)
            rendered += 1
            frames.append({"file": name, "turn": turn,
                           "phase": phase_name, "viewpoint": viewpoint})
            if crop:
                _crop(frame_dir / name, frame_dir / f"crop-{name}")

    # The opening board is a real state - formation_setup - and it is the only frame that
    # shows the battle line before anything has moved.  It has to be drawn here, after the
    # render helper exists and before the first advance leaves the phase: the loop can only
    # observe phases it has advanced into, so "render it in the loop" is impossible.
    render_phase(out_opening=(state.turn, state.phase.value))
    engine.advance(state.game_id)
    compare_phase()
    # The opening advance lands on a real phase (EM-01 opens straight into gunnery); the
    # loop only renders after *its own* advances, so without this the first phase after
    # setup would be skipped and a beat referencing it would have no frame.
    if state.phase in RENDER_PHASES:
        render_phase()

    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 2000:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                key = (state.turn, state.phase.value, side.value)
                batch = orders.get(key)
                if batch is None:
                    missing.append(str(key))
                    continue
                used.add(key)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid:
                    raise SystemExit(f"recorded batch refused at {key}: {result.errors[:3]}")
        engine.advance(state.game_id)
        compare_phase()
        if state.phase in RENDER_PHASES:
            render_phase()

    final = battle.get("final", {})
    actual = {
        "turn": state.turn,
        "phase": state.phase.value,
        "ships": {
            ship.id: {"position": ship.position.label if ship.position else None,
                      "hull": ship.hull, "sunk": ship.sunk}
            for ship in state.ships.values()
        },
    }
    mismatches = phase_mismatches[:12]
    if final.get("turns") and final["turns"] != actual["turn"]:
        mismatches.append(f"final turn {actual['turn']} != recorded {final['turns']}")

    verdict = {
        "battle": str(battle_dir.relative_to(ROOT)),
        "model_traffic_replayed": bool(model_traffic),
        "recorded_policies_registered": policy_counts,
        "orders_used": len(used),
        "orders_recorded": len(orders),
        "orders_missing_for_a_phase": missing[:5],
        "final": {"turn": actual["turn"], "phase": actual["phase"]},
        "phases_compared": phases_compared,
        "phase_mismatches": len(phase_mismatches),
        "mismatches": mismatches[:10],
        "verdict": "PASS" if not mismatches and not missing else "FAIL",
        "frames_rendered": rendered,
    }
    return verdict


def _recorded_ships(battle_dir: Path) -> dict[str, dict]:
    """The last god's-eye snapshot the battle recorded, for comparison."""
    views = sorted((battle_dir / "views").glob("*.json"))
    if not views:
        return {}
    last = json.loads(views[-1].read_text(encoding="utf-8"))
    return {
        ship_id: {"hull": ship.get("hull"), "sunk": bool(ship.get("sunk"))}
        for ship_id, ship in last["god"]["ships"].items()
    }


def _crop(src: Path, dst: Path) -> None:
    """Reuse the report's crop helper so a still is readable at video size."""
    sys.path.insert(0, str(ROOT / "research" / "command_delay"))
    try:
        from crop_battle_images import crop as crop_image  # type: ignore

        crop_image(src, dst, margin=170)
    except Exception:  # noqa: BLE001 - cropping is cosmetic; the full frame still exists
        dst.write_bytes(src.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_em01")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent / "frames")
    parser.add_argument("--views", default="god,axis,allies")
    parser.add_argument("--without-model-traffic", action="store_true",
                        help="replay order batches only; reproduces movement and fire but "
                             "NOT the battle (see recorded_policies.py for why)")
    parser.add_argument("--no-crop", action="store_true")
    args = parser.parse_args()

    battle_dir = args.battle if Path(args.battle).is_absolute() else BATTLE_ROOT / args.battle
    if not (battle_dir / "battle_data.json").exists():
        print(f"no battle record at {battle_dir}", file=sys.stderr)
        return 2
    do_render = args.render or not args.verify
    args.out.mkdir(parents=True, exist_ok=True)
    verdict = replay(
        battle_dir, args.out if do_render else None,
        viewpoints=tuple(item.strip() for item in args.views.split(",") if item.strip()),
        crop=not args.no_crop,
        model_traffic=not args.without_model_traffic,
    )
    report_path = battle_dir / "replay_verification.json"
    report_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
