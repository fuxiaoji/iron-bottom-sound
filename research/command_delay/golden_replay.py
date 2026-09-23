"""CD-0 golden replay: freeze Classic and Realistic semantics before Command Delay.

Run with ``--build`` to write the baselines from the frozen commit
(``realistic-command-v1-frozen``); run with ``--check`` to assert the current
working tree still reproduces them.

What is frozen
--------------
Three independent surfaces per matrix row:

1. ``events``  — the adjudication stream (turn/phase/type/payload), so any rule
   change that alters movement, gunnery, damage or command-chain resolution
   shows up.
2. ``orders``  — the sealed order batch of every (turn, phase, side), so a
   change in the *planner* (formation expansion, follower plans, detachments)
   is caught even when it happens not to move the dice.
3. ``ships`` / ``formations`` — final per-ship position/heading/hull/sunk and
   the formation command chain, the coarse end state.

Classic is replayed with ``GameOptions()``; Realistic with
``GameOptions(realistic_command=True)``.  Both sides use the deterministic state
machine AI, so a game is a pure function of (scenario, seed, options).

Determinism by construction
---------------------------
Every row runs in a **child process with ``PYTHONHASHSEED`` pinned**, because the
frozen tree was measured to be hash-order sensitive in one row (defect CD0-F1,
see ``--probe-hash-seeds``).  Pinning the seed makes the baseline a reproducible
property of the code rather than of the caller's environment; the cross-seed
probe separately measures how much of that sensitivity is left.

Frozen-projection comparison
----------------------------
A golden tree is compared through ``project(actual, frozen)``: dict keys that
did not exist at freeze time are ignored, everything else must match exactly,
and list lengths must match.  This separates two questions a plain byte diff
would conflate:

* **frozen semantics changed?** — answered by the projection.  A changed value,
  a removed key, a resized or reordered list is drift and fails the check.
* **data model grew?** — reported separately as ``envelope_added`` key paths
  (e.g. a new ``GameOptions`` flag appears as one new key in every
  ``game_created`` payload).  Additive growth is recorded in
  ``DATA_MODEL_DIFF.md`` and never silently edits frozen semantics.

The projection is applied recursively and pairwise, so it cannot hide a change
inside a nested payload: only *new* keys are dropped, never new *values* of keys
that already existed.

Usage::

    python research/command_delay/golden_replay.py --build
    python research/command_delay/golden_replay.py --check
    python research/command_delay/golden_replay.py --probe-hash-seeds 0,1,2,8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
PINNED_HASH_SEED = "0"

# Frozen matrix.  Seeds are the ones already used by the repository's own
# realistic regression tests, so the baseline exercises the same scenarios the
# project already trusts.
MATRIX: tuple[dict, ...] = (
    {"tag": "classic_s01", "scenario": "IBS-S-01", "seed": 20270830, "realistic": False},
    {"tag": "classic_s03", "scenario": "IBS-S-03", "seed": 3, "realistic": False},
    {"tag": "classic_em01", "scenario": "IBS-S-EM-01", "seed": 20270829, "realistic": False},
    {"tag": "realistic_s01", "scenario": "IBS-S-01", "seed": 20270830, "realistic": True},
    {"tag": "realistic_s03", "scenario": "IBS-S-03", "seed": 3, "realistic": True},
    {"tag": "realistic_em01", "scenario": "IBS-S-EM-01", "seed": 20270829, "realistic": True},
    {"tag": "realistic_s03_seed9", "scenario": "IBS-S-03", "seed": 9, "realistic": True},
    # CD-13: command delay mode as its own frozen row.  The seven rows above all run
    # with the mode off, so the whole command chain - orders, deliveries, reports,
    # acknowledgements and the memory the agents carry - was outside any baseline.
    # This row freezes it, deterministically and without a model: no fleet or
    # formation policy is registered here, so every commander is doctrine.
    {"tag": "cd_s01", "scenario": "IBS-S-01", "seed": 20270830, "realistic": True,
     "command_delay": True},
)

# Scalars compared for exact equality on top of the projected trees.
SCALARS = ("passed", "final_turn", "final_phase", "rng_counter", "n_events",
           "n_order_batches")


def canonical(value) -> str:
    """Stable JSON text for hashing (sorted keys, no float noise)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project(actual, frozen):
    """Keep only structure that existed at freeze time, recursively.

    Returns ``(projected, drift)``.  ``drift`` lists human-readable paths where
    the actual tree cannot be projected onto the frozen one: a missing key, a
    type change, or a different list length.
    """
    if isinstance(frozen, dict):
        if not isinstance(actual, dict):
            return None, ["type"]
        out = {}
        drift: list[str] = []
        for key, frozen_value in frozen.items():
            if key not in actual:
                drift.append(f"missing:{key}")
                continue
            value, sub = project(actual[key], frozen_value)
            if sub:
                drift.extend(f"{key}.{item}" for item in sub)
            out[key] = value
        return out, drift
    if isinstance(frozen, list):
        if not isinstance(actual, list):
            return None, ["type"]
        if len(actual) != len(frozen):
            return None, [f"len:{len(actual)}!={len(frozen)}"]
        out = []
        drift = []
        for index, frozen_item in enumerate(frozen):
            value, sub = project(actual[index], frozen_item)
            if sub:
                drift.extend(f"[{index}].{item}" for item in sub)
            out.append(value)
        return out, drift
    if isinstance(actual, type(frozen)) or (
        isinstance(actual, (int, float)) and isinstance(frozen, (int, float))
    ):
        return actual, []
    return None, ["type"]


def envelope_added(actual, frozen, path: str = "") -> list[str]:
    """Key paths present in ``actual`` but absent from ``frozen`` (report only)."""
    found: list[str] = []
    if isinstance(frozen, dict) and isinstance(actual, dict):
        for key, value in actual.items():
            here = f"{path}.{key}" if path else key
            if key not in frozen:
                found.append(here)
            else:
                found.extend(envelope_added(value, frozen[key], here))
    elif isinstance(frozen, list) and isinstance(actual, list) and len(frozen) == len(actual):
        for index, (item_actual, item_frozen) in enumerate(zip(actual, frozen)):
            found.extend(envelope_added(item_actual, item_frozen, f"{path}[{index}]"))
    return found


def strip_indices(path: str) -> str:
    """Collapse ``events[7].payload`` to ``events[].payload`` for reporting."""
    return re.sub(r"\[\d+\]", "[]", path)


def walk_diffs(actual, frozen, path: str = "") -> list[str]:
    """Exact leaf/path diff between two trees, for diagnostics."""
    out: list[str] = []
    if isinstance(frozen, dict) and isinstance(actual, dict):
        for key in sorted(set(frozen) | set(actual)):
            here = f"{path}.{key}" if path else key
            if key not in frozen:
                out.append(f"{here}: ADDED")
            elif key not in actual:
                out.append(f"{here}: REMOVED")
            else:
                out.extend(walk_diffs(actual[key], frozen[key], here))
    elif isinstance(frozen, list) and isinstance(actual, list):
        if len(actual) != len(frozen):
            out.append(f"{path}: LEN {len(actual)} != {len(frozen)}")
        else:
            for index, (a, b) in enumerate(zip(actual, frozen)):
                out.extend(walk_diffs(a, b, f"{path}[{index}]"))
    elif actual != frozen:
        out.append(f"{path}: {json.dumps(frozen)[:160]} -> {json.dumps(actual)[:160]}")
    return out


# --------------------------------------------------------------------------- worker

ROW_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import GameOptions

spec = json.loads(sys.argv[2])
if spec.get("command_delay"):
    # The mode owns the movement and gunnery phases (formations are commanded by their
    # own agents, not by a per-ship planner), so this row drives those phases the way
    # the mode's research driver does.
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import OrderBatch, Phase, Side
    from iron_bottom_sound.realistic_command import (
        RealisticCommander, default_setup_orders,
    )

    engine = IronBottomEngine()
    state = engine.reset(spec["scenario"], spec["seed"], GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)
    sessions = {item: LLMPlayerSession(item, RealisticCommander()) for item in Side}
    substitutions: list[dict] = []
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase == Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(
                        side=side, phase=state.phase,
                        formation_movement=command_delay.formation_orders(state, side),
                    )
                elif state.phase == Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase == Phase.MOVEMENT_PLANNING:
                    # Doctrine can propose a formation plan the engine refuses (a member
                    # speed limit, a wake the followers cannot hold).  The mode's research
                    # driver answers that the same way: record the substitution and let
                    # the deterministic commander move the side this turn.  Silently
                    # pretending the plan was executed is what this record exists to
                    # prevent.
                    substitutions.append(
                        {"turn": state.turn, "side": side.value, "errors": result.errors[:3]}
                    )
                    _, fallback, _ = RealisticCommander().choose_plan(
                        engine, state.game_id, side,
                    )
                    result = engine.submit_orders(state.game_id, fallback)
                if not result.valid:
                    raise SystemExit("rejected: " + repr(result.errors[:2]))
        engine.advance(state.game_id)
    game_id = state.game_id
    report_passed = state.phase == Phase.COMPLETE
    failure_reason = None
else:
    options = GameOptions(realistic_command=bool(spec["realistic"]))
    report, engine, _sessions = run_match(
        spec["scenario"], axis="tactical", allies="tactical", seed=spec["seed"],
        options=options, request_limit=256,
    )
    state = engine.get(report.game_id)
    game_id = report.game_id
    report_passed = report.passed
    failure_reason = report.failure_reason


def mask(value):
    if isinstance(value, str):
        return "<GAME_ID>" if value == game_id else value
    if isinstance(value, dict):
        return {k: mask(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask(v) for v in value]
    return value


events = [
    {
        "turn": e.turn,
        "phase": e.phase.value,
        "type": e.type,
        "payload": mask(e.payload),
    }
    for e in state.events
]
orders = {
    key: {side: batch.model_dump(mode="json") for side, batch in sealed.items()}
    for key, sealed in state.sealed_orders.items()
}
ships = {
    ship.id: {
        "position": ship.position.label if ship.position else None,
        "heading": ship.heading,
        "hull": ship.hull,
        "sunk": ship.sunk,
        "speed": ship.current_speed,
        "command_status": ship.command_status,
        "formation_id": ship.formation_id,
    }
    for ship in state.ships.values()
}
formations = {
    f.id: {
        "side": f.side.value,
        "ship_ids": f.ship_ids,
        "leader_id": f.leader_id,
        "flagship_id": f.flagship_id,
        "status": f.status,
    }
    for f in state.formations.values()
}
trees = {"events": events, "orders": orders, "ships": ships,
         "formations": formations}
if spec.get("command_delay"):
    # Freeze the command chain itself: who was told what, when it arrived, what came
    # back up, and how much the commanders remembered.
    from iron_bottom_sound.formation_memory import MEMORY_KINDS

    mode = state.command_delay
    trees["command_delay"] = {
        "messages": [
            {
                "message_id": item.message_id,
                "kind": item.kind.value,
                "medium": item.medium.value,
                "precedence": item.precedence.value,
                "origin": item.origin,
                "destination": item.destination,
                "issued_turn": item.issued_turn,
                "issued_phase": item.issued_phase.value,
                "handling_delay": item.handling_delay,
                "delivered_turn": item.delivered_turn,
                "status": item.status.value,
                "acknowledged_turn": item.acknowledged_turn,
                "reason": item.reason,
                "reporting_formation_id": (
                    (item.payload.get("report") or {}).get("reporting_formation_id")
                ),
                "in_person": bool(item.payload.get("delivered_in_person")),
                "has_report_text": bool(item.payload.get("report_text")),
            }
            for item in mode.messages
        ],
        "decisions": [
            {
                "formation_id": row["formation_id"],
                "turn": row["turn"],
                "plan": row.get("selected_movement_plan"),
                "report_actions": sorted(row.get("report_actions") or []),
                "acknowledgement": bool(row.get("acknowledgement")),
            }
            for row in mode.decisions
        ],
        "memories": {
            formation_id: {kind: len(memory.of_kind(kind)) for kind in MEMORY_KINDS}
            for formation_id, memory in sorted(mode.memories.items())
        },
        "policy_labels": dict(sorted(mode.policy_labels.items())),
        "substitutions": substitutions,
    }

json.dump(
    {
        "tag": spec["tag"],
        "scenario": spec["scenario"],
        "seed": spec["seed"],
        "realistic_command": bool(spec["realistic"]),
        "passed": bool(report_passed),
        "failure_reason": failure_reason,
        "final_turn": state.turn,
        "final_phase": state.phase.value,
        "rng_counter": state.rng_counter,
        "n_events": len(events),
        "n_order_batches": sum(len(sealed) for sealed in state.sealed_orders.values()),
        "trees": trees,
    },
    sys.stdout,
)
"""


def replay(spec: dict, hash_seed: str = PINNED_HASH_SEED) -> dict:
    """Play one matrix row in a child process and return its record."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", ROW_SCRIPT, str(SRC), json.dumps(spec)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=1800,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{spec['tag']}: child failed\n{completed.stderr[-4000:]}")
    record = json.loads(completed.stdout)
    record["hash_seed"] = hash_seed
    record["digest_trees"] = digest(canonical(record["trees"]))
    return record


# --------------------------------------------------------------------------- modes

def build() -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    index_rows = []
    for spec in MATRIX:
        record = replay(spec)
        (GOLDEN_DIR / f"{spec['tag']}.json").write_text(
            json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
        )
        index_rows.append({key: record[key] for key in
                           ("tag", "scenario", "seed", "realistic_command", "passed",
                            "final_turn", "final_phase", "rng_counter", "n_events",
                            "n_order_batches", "digest_trees")})
        print(f"[golden] {spec['tag']:<20} events={record['n_events']:<5} "
              f"passed={record['passed']} digest={record['digest_trees'][:16]}")
    (GOLDEN_DIR / "GOLDEN_INDEX.json").write_text(
        json.dumps(
            {
                "frozen_tag": "realistic-command-v1-frozen",
                "frozen_commit": "d432a975151651fa7d6746b2f92e66b1e09d8d4a",
                "hash_seed_pinned": PINNED_HASH_SEED,
                "matrix": [spec["tag"] for spec in MATRIX],
                "scalars": list(SCALARS),
                "comparison": "frozen-projection (added dict keys ignored and reported)",
                "known_defect": "CD0-F1: engine.py:3124 iterates set[frozenset[str]] "
                                "in hash order; see --probe-hash-seeds",
                "records": index_rows,
            },
            indent=1, sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    return 0


def check() -> int:
    index_path = GOLDEN_DIR / "GOLDEN_INDEX.json"
    if not index_path.exists():
        print("FAIL: no golden baseline; run --build first")
        return 2
    index = json.loads(index_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    envelope_all: dict[str, int] = {}
    for expected_row in index["records"]:
        tag = expected_row["tag"]
        frozen = json.loads((GOLDEN_DIR / f"{tag}.json").read_text(encoding="utf-8"))
        spec = next(item for item in MATRIX if item["tag"] == tag)
        actual = replay(spec)
        scalar_drift = [name for name in SCALARS if actual[name] != frozen[name]]
        projected, drift = project(actual["trees"], frozen["trees"])
        if not drift and canonical(projected) != canonical(frozen["trees"]):
            drift = walk_diffs(projected, frozen["trees"])[:12]
        added = sorted({strip_indices(path) for path in
                        envelope_added(actual["trees"], frozen["trees"])})
        for path in added:
            envelope_all[path] = envelope_all.get(path, 0) + 1
        if drift or scalar_drift:
            failures.append(f"{tag}: scalars={scalar_drift} trees={drift[:6]}")
            print(f"[check] {tag:<20} DRIFT scalars={scalar_drift} trees={drift[:4]}")
        else:
            print(f"[check] {tag:<20} OK  (envelope keys added: {len(added)})")
    if envelope_all:
        print("\nENVELOPE_KEYS_ADDED (additive only, not drift):")
        for path in sorted(envelope_all):
            print(f"  {path}  x{envelope_all[path]}")
    if failures:
        print("\nGOLDEN_REPLAY = FAIL")
        for line in failures:
            print("  " + line)
        return 1
    print("\nGOLDEN_REPLAY = PASS")
    return 0


def probe_hash_seeds(seeds: list[str]) -> int:
    """Measure hash-order sensitivity of each row across processes."""
    rows: list[dict] = []
    unstable = 0
    for spec in MATRIX:
        digests: dict[str, str] = {}
        for seed in seeds:
            record = replay(spec, hash_seed=seed)
            digests[seed] = record["digest_trees"]
        unique = sorted(set(digests.values()))
        stable = len(unique) == 1
        unstable += 0 if stable else 1
        rows.append({"tag": spec["tag"], "stable": stable,
                     "digests": digests, "n_unique": len(unique)})
        print(f"[probe] {spec['tag']:<20} stable={stable} n_unique={len(unique)} "
              f"{ {k: v[:12] for k, v in digests.items()} }")
    out = Path(__file__).resolve().parent / "audits" / "cd0_hash_seed_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"hash_seeds": seeds, "rows": rows,
         "n_unstable_rows": unstable, "all_stable": unstable == 0},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")
    verdict = "PASS" if unstable == 0 else "FAIL"
    print(f"\nHASH_SEED_STABILITY = {verdict}  ({unstable} unstable rows) -> {out}")
    return 0 if unstable == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--probe-hash-seeds", metavar="LIST")
    args = parser.parse_args()
    if args.build:
        return build()
    if args.check:
        return check()
    seeds = [item.strip() for item in args.probe_hash_seeds.split(",") if item.strip()]
    return probe_hash_seeds(seeds)


if __name__ == "__main__":
    raise SystemExit(main())
