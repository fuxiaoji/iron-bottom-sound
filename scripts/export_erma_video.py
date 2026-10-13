"""Read-only director export and side-filtered commentary inputs for EM-01."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameState, Side


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value: object) -> str:
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha(data)


def export(db: Path, game_id: str, out: Path) -> None:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    raw = conn.execute("SELECT state_json FROM games WHERE game_id=?", (game_id,)).fetchone()[0]
    state = json.loads(raw)
    if state["phase"] != "complete" or state["scenario_id"] != "IBS-S-EM-01":
        raise ValueError("A completed EM-01 game is required")
    snapshots = [(seq, text, json.loads(text)) for seq, text in conn.execute(
        "SELECT sequence,state_json FROM snapshots WHERE game_id=? ORDER BY sequence", (game_id,))]
    frames = {}
    engine = IronBottomEngine()
    events = state["events"]
    for seq, text, snap in snapshots:
        fid = f"s{seq:05d}"
        attacks = [e for e in events if e["turn"] == snap["turn"] and e["type"] == "gun_mount_attack"]
        pairs = {}
        names = {s["id"]: s["name"] for s in snap["ships"].values()}
        for e in attacks:
            p = e["payload"]
            key = (p["attacker"], p["target"])
            row = pairs.setdefault(key, {"attackerId": key[0], "targetId": key[1],
                "attackerName": names[key[0]], "targetName": names[key[1]], "mountCount": 0})
            row["mountCount"] += len(p.get("mount_ids", [p["mount_id"]]))
        source_hash = sha(text.encode("utf-8"))
        engine.games[game_id] = GameState.model_validate_json(text)
        records = [ship.model_dump(mode="json") for side in (Side.AXIS, Side.ALLIES)
                   for ship in engine.observe(game_id, side).ships if ship.side == side]
        frame = {
            "provenance": {"episodeId": "em01-20261011", "sourceFrameId": fid,
                "sourceSha256": source_hash, "fixtureLabel": "二马 · 已完成战局回放"},
            "recording": {"actor_id": "spectator", "view": "spectator", "source_step": seq,
                "source_state_sha256": source_hash, "source_game_id": game_id},
            "observation": {k: snap[k] for k in ["turn", "phase", "map_columns", "map_rows",
                "printed_columns", "printed_rows", "land_hexes", "coast_hexes"]},
            "shipRecords": records, "gunneryTargetLines": [],
            "gunneryEvents": [e for e in events if e["turn"] == snap["turn"] and e["phase"] == "gunnery"],
            "actualTargetLines": list(pairs.values()), "score": snap["score"],
        }
        frame["observation"].update(ships=list(snap["ships"].values()),
            formations=list(snap["formations"].values()), torpedo_tracks=snap["torpedo_tracks"],
            markers=snap["markers"], visibility=0)
        pin = write(out / "project/apps/battle-video/public/generated/em01/frames" / (fid + ".json"), frame)
        frames[fid] = {"url": f"generated/em01/frames/{fid}.json", "sha256": pin,
            "turn": snap["turn"], "phase": snap["phase"], "sequence": seq, "sourceSha256": source_hash}
    facts = {"game_id": game_id, "source_state_sha256": sha(raw.encode("utf-8")),
        "scenario_title": state["scenario_title"], "options": state["options"],
        "turns": state["turn"], "score": state["score"], "winner": state["winner"],
        "victory_reason": state["victory_reason"], "events": events,
        "sunk": [{"id": s["id"], "name": s["name"], "side": s["side"]} for s in state["ships"].values() if s["sunk"]],
        "event_counts": dict(collections.Counter(e["type"] for e in events)), "frames": frames}
    write(out / "evidence/battle-facts.json", facts)
    prompts = []
    for turn, phase in [(2, "gunnery"), (3, "torpedo_planning"), (4, "torpedo_planning"),
                        (5, "gunnery"), (6, "gunnery"), (8, "gunnery"), (12, "complete")]:
        seq, text, snap = next((x for x in snapshots if x[2]["turn"] == turn and x[2]["phase"] == phase))
        engine.games[game_id] = GameState.model_validate_json(text)
        for side in ["axis", "allies"]:
            observation = engine.observe(game_id, Side(side)).model_dump(mode="json")
            own_order = next((e for e in events if e["turn"] == turn and e["phase"] == phase
                and e["type"] == "orders_submitted" and e["payload"]["secret_side"] == side), None)
            command = own_order["payload"]["order_batch"] if own_order else None
            prompts.append({"id": f"{side}-t{turn:02d}", "side": side, "turn": turn, "phase": phase,
                "source_frame_id": f"s{seq:05d}", "source_state_sha256": sha(text.encode("utf-8")),
                "observation": observation, "already_sealed_own_order": command,
                "disclosure": "已完成战局的命令解说，非自主下令；只生成公开理由摘要，不输出私有推理"})
    write(out / "evidence/commentary-inputs.json", prompts)
    conn.close()
    print(json.dumps({"frames": len(frames), "events": len(events), "sunk": len(facts["sunk"]),
        "score": state["score"], "winner": state["winner"], "commentary_inputs": len(prompts)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "backend/iron-bottom-sound.sqlite3")
    parser.add_argument("--game", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.db, args.game, args.out.resolve())
