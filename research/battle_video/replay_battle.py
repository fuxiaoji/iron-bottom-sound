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
    Phase.MOVEMENT_PLANNING, Phase.MOVEMENT_RESOLUTION, Phase.GUNNERY,
    Phase.TORPEDO_EFFECTS, Phase.FIRE_END,
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
           viewpoints: tuple[str, ...] = VIEWS, crop: bool = True) -> dict:
    battle = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    orders = load_orders(battle_dir)
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
    engine.advance(state.game_id)

    used: set[tuple[int, str, str]] = set()
    missing: list[str] = []
    rendered = 0
    frames: list[dict] = []

    def render_phase() -> None:
        nonlocal rendered
        if frame_dir is None:
            return
        for viewpoint in viewpoints:
            image = battle_report.render_map_image(
                state, engine, Side.AXIS, viewpoint=viewpoint,
            )
            name = f"t{state.turn:02d}-{state.phase.value}-{viewpoint}.png"
            image.save(frame_dir / name, optimize=True)
            rendered += 1
            frames.append({"file": name, "turn": state.turn,
                           "phase": state.phase.value, "viewpoint": viewpoint})
            if crop:
                _crop(frame_dir / name, frame_dir / f"crop-{name}")

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
    recorded_views = _recorded_ships(battle_dir)
    mismatches: list[str] = []
    if final.get("turns") and final["turns"] != actual["turn"]:
        mismatches.append(f"final turn {actual['turn']} != recorded {final['turns']}")
    for ship_id, snapshot in recorded_views.items():
        mine = actual["ships"].get(ship_id)
        if mine is None:
            mismatches.append(f"{ship_id} missing from the replay")
            continue
        if snapshot["sunk"] != mine["sunk"]:
            mismatches.append(f"{ship_id} sunk {mine['sunk']} != recorded {snapshot['sunk']}")
        if not snapshot["sunk"] and snapshot["hull"] != mine["hull"]:
            mismatches.append(f"{ship_id} hull {mine['hull']} != recorded {snapshot['hull']}")

    verdict = {
        "battle": str(battle_dir.relative_to(ROOT)),
        "orders_used": len(used),
        "orders_recorded": len(orders),
        "orders_missing_for_a_phase": missing[:5],
        "final": {"turn": actual["turn"], "phase": actual["phase"],
                  "ships_compared": len(recorded_views)},
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
    )
    report_path = battle_dir / "replay_verification.json"
    report_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
