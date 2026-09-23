"""Fight one command-delay battle with a real provider, and record everything.

This is the parametrised sibling of ``llm_vs_llm.py``.  That one drives the ZCode
sub-agent bridge by rewriting files and re-reading them; this one calls an
OpenAI-compatible provider directly from the process, which is what a
"the models play this scenario" run needs - and it keeps a record detailed enough
to audit the battle and to cut a documentary out of it afterwards.

What is recorded, and why each piece exists:

``calls.jsonl``     one line per model round trip: the prompt, the reply, the model's
                    **chain of thought**, token usage, latency, HTTP mishaps.  A
                    commander's reasoning is the interesting part of its turn.
``orders.jsonl``    every order batch the engine accepted, verbatim.  Without this a
                    battle cannot be re-simulated bit-for-bit - the previous battle
                    shipped without it and could only be audited as a record.
``reports.jsonl``   every report that went up: who wrote it, its own words, when it was
                    sent, when it arrived, and how late that was.
``views/``          per phase, both sides' filtered observations plus the compact full
                    state - the material for the god's-eye / axis / allies renderings.
``substitutions``   every time the engine refused an agent's batch and doctrine took
                    over.  Reported, never hidden: it is the difference between "the
                    agents commanded" and "the engine did".

Usage::

    ZHIPU_API_KEY=... .venv/bin/python research/command_delay/llm_battle.py \
        --scenario IBS-S-EM-01 --seed 19440619 --out battle_em01 \
        --model glm-4.5-flash --thinking --turn-cap 12
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import battle_report, command_delay  # noqa: E402
from iron_bottom_sound.command_observation import (  # noqa: E402
    fleet_observation, formation_observation,
)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.formation_llm import make_policy  # noqa: E402
from iron_bottom_sound.fleet_llm import make_fleet_policy  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)


class CallRecorder:
    """Wraps a provider policy: retries transport failures, records every attempt.

    The provider's own policy raises on a transport error, and the formation agent
    counts that as a rejected attempt - but a rejected attempt with no pause is a
    hammer.  The retry with backoff lives here, at the edge, so the engine's
    decision logic stays exactly as audited, and every try is on the record.
    """

    def __init__(self, inner, sink: Path, *, role: str, side: str, label: str,
                 attempts: int = 5, backoff: float = 6.0, pause: float = 1.5) -> None:
        self.inner = inner
        self.sink = sink
        self.role = role
        self.side = side
        self.label = label
        self.attempts = attempts
        self.backoff = backoff
        self.pause = pause
        self.last_meta: dict = {}
        self.calls = 0

    def __call__(self, prompt: dict) -> str:
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                content = self.inner(prompt)
                meta = dict(getattr(self.inner, "last_meta", {}) or {})
                self.last_meta = meta
                self.calls += 1
                self._write(prompt, content, meta, attempt, started, None)
                if self.pause:
                    time.sleep(self.pause)
                return content
            except Exception as error:  # noqa: BLE001 - recorded, then retried
                last_error = error
                self._write(prompt, "", {"error": f"{type(error).__name__}: {error}"},
                            attempt, started, error)
                if attempt < self.attempts:
                    time.sleep(self.backoff * attempt)
        raise last_error if last_error is not None else RuntimeError("no attempt ran")

    def _write(self, prompt: dict, content: str, meta: dict, attempt: int,
               started: float, error: Exception | None) -> None:
        record = {
            "ts": round(time.time(), 3),
            "role": self.role,
            "side": self.side,
            "label": self.label,
            "attempt": attempt,
            "latency_s": round(time.monotonic() - started, 2),
            "model": meta.get("model"),
            "request_id": meta.get("request_id"),
            "usage": meta.get("usage") or {},
            "finish_reason": meta.get("finish_reason"),
            "thinking": meta.get("reasoning_content") or "",
            "response": content,
            "prompt": prompt,
            "transport_error": f"{type(error).__name__}: {error}" if error else None,
        }
        with self.sink.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def compact_state(state) -> dict:
    """The god's-eye material: every ship, exactly where it is.

    Kept separate from the two side views on purpose - the documentary's whole device
    is showing what each side knew next to what was actually there.
    """
    return {
        "turn": state.turn,
        "phase": state.phase.value,
        "ships": {
            ship.id: {
                "name": ship.name,
                "side": ship.side.value,
                "type": ship.ship_type,
                "position": ship.position.label if ship.position else None,
                "q": ship.position.q if ship.position else None,
                "r": ship.position.r if ship.position else None,
                "heading": ship.heading,
                "speed": ship.current_speed,
                "hull": ship.hull,
                "max_hull": ship.max_hull,
                "sunk": ship.sunk,
                "formation_id": ship.formation_id,
                "command_status": ship.command_status,
            }
            for ship in state.ships.values()
        },
        "formations": {
            formation.id: {
                "name": formation.name,
                "side": formation.side.value,
                "ship_ids": list(formation.ship_ids),
                "leader_id": formation.leader_id,
                "flagship_id": formation.flagship_id,
                "geometry_kind": formation.geometry_kind.value,
                "heading": formation.heading,
                "status": formation.status,
                "movement_style": formation.movement_style.value,
            }
            for formation in state.formations.values()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="IBS-S-EM-01")
    parser.add_argument("--seed", type=int, default=19440619)
    parser.add_argument("--out", default="battle_em01")
    parser.add_argument("--provider", default="zhipu")
    parser.add_argument("--model", default="glm-4.5-flash")
    parser.add_argument("--thinking", action="store_true",
                        help="leave the model's reasoning on and record it")
    parser.add_argument("--max-tokens", type=int, default=0,
                        help="output budget per call; default 4000 with thinking "
                             "(reasoning + JSON must both fit) and 2000 without")
    parser.add_argument("--turn-cap", type=int, default=12)
    parser.add_argument("--max-calls", type=int, default=0,
                        help="stop after N model calls (smoke test)")
    parser.add_argument("--no-model", action="store_true",
                        help="run the battle with doctrine only (no provider calls): the "
                             "pipeline's dress rehearsal, and a fallback record")
    parser.add_argument("--capture-images", action="store_true",
                        help="also render the board per turn (off: frames are cut later)")
    args = parser.parse_args()

    out_dir = Path(__file__).resolve().parent / args.out
    for sub in ("requests", "responses", "views", "images"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    orders_path = out_dir / "orders.jsonl"
    calls_path.write_text("", encoding="utf-8")
    orders_path.write_text("", encoding="utf-8")

    engine = IronBottomEngine()
    state = engine.reset(args.scenario, args.seed, GameOptions(
        realistic_command=True, command_delay_mode=True, battle_report=True,
    ))

    # A thinking model spends the same budget on its reasoning and on the JSON that
    # follows it; at 2000 the reply is regularly "reasoning only" with
    # finish_reason=length, which is a rejected attempt and a retry.  The budget is
    # therefore sized for both parts when thinking is on.
    max_tokens = args.max_tokens or (4000 if args.thinking else 2000)
    recorders: list[CallRecorder] = []
    if args.no_model:
        # Doctrine on both levels.  Every commander is still a commander - the
        # deterministic agent - so the *pipeline* (orders, reports, ledger, views) runs
        # in full and produces a real record; only the model calls are absent.
        formation_label = "deterministic-formation-v1"
        fleet_label = "no-fleet-agent"
        print("running without a model: doctrine on both levels", flush=True)
    else:
        formation_policy, formation_label = make_policy(
            provider=args.provider, model=args.model, thinking=args.thinking,
            max_tokens=max_tokens,
        )
        fleet_policy, fleet_label = make_fleet_policy(
            provider=args.provider, model=args.model, thinking=args.thinking,
            max_tokens=max_tokens,
        )
        if formation_policy is None or fleet_policy is None:
            print(f"cannot run: formation={formation_label} fleet={fleet_label}",
                  file=sys.stderr)
            return 2
        for side in Side:
            recorder = CallRecorder(formation_policy, calls_path, role="formation",
                                    side=side.value, label=formation_label)
            command_delay.set_side_policy(side, recorder, formation_label)
            recorders.append(recorder)
            fleet_recorder = CallRecorder(fleet_policy, calls_path, role="fleet",
                                          side=side.value, label=fleet_label)
            command_delay.set_fleet_policy(side, fleet_recorder, fleet_label)
            recorders.append(fleet_recorder)

    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    battle: dict = {
        "scenario": args.scenario,
        "seed": args.seed,
        "sides": {side.value: formation_label for side in Side},
        "fleet_policy": fleet_label,
        "formation_policy": formation_label,
        "thinking_enabled": bool(args.thinking),
        "max_tokens": max_tokens,
        "turns": [],
        "fleet_orders": [],
        "substitutions": [],
        "three_views": [],
    }
    total_calls = {"formation": 0, "fleet": 0}

    def budget_spent() -> bool:
        return bool(args.max_calls) and (
            total_calls["formation"] + total_calls["fleet"] >= args.max_calls
        )

    def record_view() -> None:
        entry = {
            "turn": state.turn,
            "phase": state.phase.value,
            "god": compact_state(state),
            "sides": {},
        }
        for side in Side:
            formations = command_delay.active_formations(state, side)
            entry["sides"][side.value] = {
                "fleet": fleet_observation(engine, state, side).model_dump(mode="json"),
                "formations": {
                    formation.id: formation_observation(
                        engine, state, side, formation.id
                    ).model_dump(mode="json")
                    for formation in formations
                },
            }
        battle["three_views"].append(entry)
        (out_dir / "views" / f"t{state.turn:02d}-{state.phase.value}.json").write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8",
        )

    def submit(batch: OrderBatch, side: Side) -> tuple[bool, list[str]]:
        result = engine.submit_orders(state.game_id, batch)
        if result.valid:
            with orders_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "turn": state.turn,
                    "phase": state.phase.value,
                    "side": side.value,
                    "batch": batch.model_dump(mode="json"),
                }, ensure_ascii=False, default=str) + "\n")
        return result.valid, list(result.errors)

    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)

    turn_records: dict[int, dict] = {}
    harvested = 0
    steps = 0
    while state.phase != Phase.COMPLETE and state.turn <= args.turn_cap and steps < 600:
        steps += 1
        if budget_spent():
            print(f"call budget reached ({args.max_calls}); stopping early", flush=True)
            break
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(
                        side=side, phase=state.phase,
                        formation_movement=command_delay.formation_orders(state, side),
                    )
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                valid, errors = submit(batch, side)
                if not valid and state.phase is Phase.MOVEMENT_PLANNING:
                    battle["substitutions"].append({
                        "turn": state.turn, "side": side.value, "errors": errors[:3],
                    })
                    print(f"SUBSTITUTION t{state.turn} {side.value}: {errors[:2]}", flush=True)
                    _, fallback, _ = RealisticCommander().choose_plan(
                        engine, state.game_id, side,
                    )
                    valid, errors = submit(fallback, side)
                assert valid, (state.turn, state.phase, side, errors[:3])
        prev_phase = state.phase
        engine.advance(state.game_id)
        if args.capture_images:
            try:
                battle_report.capture_after_advance(
                    None, out_dir / "images", state, engine, prev_phase,
                )
            except Exception as error:  # noqa: BLE001 - a report image is not the battle
                print(f"capture failed: {error}", flush=True)
        record = turn_records.setdefault(state.turn, {"turn": state.turn, "events": [], "images": []})
        for event in state.events[harvested:]:
            if event.turn == state.turn:
                record["events"].append(event)
        harvested = len(state.events)
        record_view()
        total_calls["formation"] = sum(item.calls for item in recorders if item.role == "formation")
        total_calls["fleet"] = sum(item.calls for item in recorders if item.role == "fleet")
        print(
            f"t{state.turn} {prev_phase.value:>18} -> {state.phase.value:<18} "
            f"calls={total_calls['formation']}+{total_calls['fleet']} "
            f"subs={len(battle['substitutions'])}",
            flush=True,
        )

    # ---- the record
    mode = state.command_delay
    battle["turns"] = [
        {
            "turn": record["turn"],
            "events": [
                {"turn": e.turn, "phase": e.phase.value, "type": e.type,
                 "message": e.message, "payload": e.payload}
                for e in record["events"]
            ],
            "images": record["images"],
        }
        for _, record in sorted(turn_records.items())
    ]
    battle["messages"] = [item.model_dump(mode="json") for item in mode.messages]
    battle["decisions"] = list(mode.decisions)
    battle["memories"] = {
        formation_id: memory.model_dump(mode="json")
        for formation_id, memory in mode.memories.items()
    }
    battle["agent_log"] = list(mode.agent_log)
    battle["policy_labels"] = dict(mode.policy_labels)
    battle["fleet_decisions"] = [
        entry for entry in mode.agent_log if entry.get("role") == "fleet_agent"
    ]
    battle["final"] = {
        "complete": state.phase == Phase.COMPLETE,
        "turns": state.turn,
        "winner": state.winner.value if state.winner else None,
        "victory_reason": state.victory_reason,
        "score": state.score,
        "friendly_collisions": sum(
            1 for event in state.events
            if event.type == "collision" and event.payload.get("friendly")
        ),
    }
    battle["images_files"] = sorted(
        str(path.relative_to(out_dir)) for path in (out_dir / "images").rglob("*.png")
    )
    battle["call_totals"] = {
        **total_calls,
        "transport_failures": sum(
            1 for line in calls_path.read_text(encoding="utf-8").splitlines()
            if line and json.loads(line).get("transport_error")
        ),
    }
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for line in calls_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        for key in usage:
            usage[key] += int((record.get("usage") or {}).get(key) or 0)
    battle["call_totals"]["usage"] = usage

    reports = []
    for item in mode.messages:
        report = (item.payload or {}).get("report") or {}
        if not report:
            continue
        reports.append({
            "message_id": item.message_id,
            "kind": item.kind.value,
            "reporting_formation_id": report.get("reporting_formation_id"),
            "origin": item.origin,
            "destination": item.destination,
            "medium": item.medium.value,
            "issued_turn": item.issued_turn,
            "issued_phase": item.issued_phase.value,
            "handling_delay": item.handling_delay,
            "delivered_turn": item.delivered_turn,
            "status": item.status.value,
            "report_text": (item.payload or {}).get("report_text") or "",
        })
    (out_dir / "reports.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in reports) + "\n",
        encoding="utf-8",
    )
    (out_dir / "battle_data.json").write_text(
        json.dumps(battle, ensure_ascii=False, default=str), encoding="utf-8",
    )
    print(
        f"\nDONE turns={state.turn} phase={state.phase.value} "
        f"calls={battle['call_totals']} substitutions={len(battle['substitutions'])} "
        f"messages={len(mode.messages)} reports={len(reports)}",
        flush=True,
    )
    print(f"record -> {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
