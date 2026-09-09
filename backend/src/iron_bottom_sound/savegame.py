from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any

from .models import GameEvent, GameState
from .storage import GameRepository


FORMAT = "iron-bottom-sound-save"
VERSION = 1


def _canonical(value: Any) -> bytes:
    def browser_stable(item: Any) -> Any:
        # JSON has one number type.  Browsers stringify 5.0 as 5, whereas Python
        # normally emits 5.0; normalize integral floats so a download/file-read/
        # upload round trip cannot invalidate an otherwise untouched archive.
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {key: browser_stable(child) for key, child in item.items()}
        if isinstance(item, list):
            return [browser_stable(child) for child in item]
        return item

    return json.dumps(
        browser_stable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _checksum(payload: dict) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    return "sha256:" + hashlib.sha256(_canonical(unsigned)).hexdigest()


def build_save_bundle(
    repository: GameRepository,
    state: GameState,
    custom_scenario: dict | None = None,
) -> dict:
    snapshots = repository.snapshots(state.game_id)
    if not snapshots:
        sequence = state.events[-1].sequence if state.events else 0
        snapshots = [(sequence, state)]
    bundle = {
        "format": FORMAT,
        "version": VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_game_id": state.game_id,
        "state": state.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in state.events],
        "snapshots": [
            {"sequence": sequence, "state": snapshot.model_dump(mode="json")}
            for sequence, snapshot in snapshots
        ],
        "custom_scenario": custom_scenario,
    }
    bundle["checksum"] = _checksum(bundle)
    return bundle


def _validate_sequences(events: list[GameEvent]) -> None:
    if not events or events[0].type != "game_created":
        raise ValueError("存档事件必须以 game_created 开始")
    sequences = [event.sequence for event in events]
    if sequences != list(range(1, len(events) + 1)):
        raise ValueError("存档事件序号不连续")


def validate_save_bundle(bundle: dict) -> tuple[GameState, list[tuple[int, GameState]]]:
    if bundle.get("format") != FORMAT or bundle.get("version") != VERSION:
        raise ValueError("不支持的存档格式或版本")
    checksum = bundle.get("checksum")
    if not isinstance(checksum, str) or checksum != _checksum(bundle):
        raise ValueError("存档校验和不匹配，文件可能已损坏或被修改")
    state = GameState.model_validate(bundle.get("state"))
    events = [GameEvent.model_validate(item) for item in bundle.get("events", [])]
    _validate_sequences(events)
    if state.events != events:
        raise ValueError("存档状态与事件轨迹不一致")
    if bundle.get("source_game_id") != state.game_id:
        raise ValueError("存档对局标识不一致")

    snapshots: list[tuple[int, GameState]] = []
    last_sequence = -1
    for item in bundle.get("snapshots", []):
        sequence = int(item["sequence"])
        snapshot = GameState.model_validate(item["state"])
        if sequence <= last_sequence or sequence > events[-1].sequence:
            raise ValueError("存档快照序列无效")
        if snapshot.game_id != state.game_id:
            raise ValueError("存档快照的对局标识不一致")
        if (snapshot.events[-1].sequence if snapshot.events else 0) != sequence:
            raise ValueError("存档快照与事件序列不一致")
        if snapshot.events != events[:sequence]:
            raise ValueError("存档快照的事件前缀不一致")
        snapshots.append((sequence, snapshot))
        last_sequence = sequence
    final_sequence = events[-1].sequence
    if not snapshots or snapshots[-1][0] != final_sequence:
        snapshots.append((final_sequence, state.model_copy(deep=True)))
    return state, snapshots


def clone_imported_game(
    state: GameState, snapshots: list[tuple[int, GameState]]
) -> tuple[GameState, list[tuple[int, GameState]]]:
    """Give every import a fresh id so importing can never overwrite a live game."""
    new_id = str(uuid.uuid4())

    def clone(source: GameState) -> GameState:
        copied = source.model_copy(deep=True)
        copied.game_id = new_id
        if copied.events and copied.events[0].type == "game_created":
            copied.events[0].payload = deepcopy(copied.events[0].payload)
            copied.events[0].payload["game_id"] = new_id
        return copied

    return clone(state), [(sequence, clone(snapshot)) for sequence, snapshot in snapshots]
