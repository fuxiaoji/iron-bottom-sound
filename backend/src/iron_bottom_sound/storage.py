from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from .models import BattleReportEntry, GameEvent, GameState


class GameRepository:
    """SQLite persistence for snapshots and the append-only event audit trail."""

    def __init__(self, path: str | Path = "iron-bottom-sound.sqlite3") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS games (
              game_id TEXT PRIMARY KEY,
              state_json TEXT NOT NULL,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
              game_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              event_json TEXT NOT NULL,
              PRIMARY KEY (game_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS snapshots (
              game_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              state_json TEXT NOT NULL,
              PRIMARY KEY (game_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS battle_report (
              game_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              turn INTEGER NOT NULL,
              phase TEXT NOT NULL,
              side TEXT NOT NULL,       -- 'axis'|'allies'（capture）| 'both'（narrative）
              kind TEXT NOT NULL,       -- 'capture'|'narrative'
              image_path TEXT,
              content TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (game_id, sequence, side)
            );
            CREATE TABLE IF NOT EXISTS research_consent (
              game_id TEXT PRIMARY KEY,
              allow INTEGER NOT NULL DEFAULT 0,
              handle TEXT,
              scenario TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS custom_scenarios (
              scenario_id TEXT PRIMARY KEY,
              definition_json TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    def save(self, state: GameState) -> None:
        state_json = state.model_dump_json()
        with self.connection:
            self.connection.execute(
                """INSERT INTO games(game_id, state_json) VALUES (?, ?)
                   ON CONFLICT(game_id) DO UPDATE SET
                     state_json=excluded.state_json, updated_at=CURRENT_TIMESTAMP""",
                (state.game_id, state_json),
            )
            self.connection.executemany(
                "INSERT OR IGNORE INTO events(game_id, sequence, event_json) VALUES (?, ?, ?)",
                [(state.game_id, event.sequence, event.model_dump_json()) for event in state.events],
            )
            sequence = state.events[-1].sequence if state.events else 0
            self.connection.execute(
                "INSERT OR REPLACE INTO snapshots(game_id, sequence, state_json) VALUES (?, ?, ?)",
                (state.game_id, sequence, state_json),
            )

    def load(self, game_id: str) -> GameState:
        row = self.connection.execute("SELECT state_json FROM games WHERE game_id = ?", (game_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown game {game_id}")
        return GameState.model_validate_json(row["state_json"])

    def game_ids(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT game_id FROM games ORDER BY updated_at DESC"
        ).fetchall()
        return [str(row["game_id"]) for row in rows]

    def game_summaries(self) -> list[dict]:
        """Return lightweight resume cards without exposing orders or hidden units."""
        rows = self.connection.execute(
            "SELECT game_id, state_json, updated_at FROM games ORDER BY updated_at DESC"
        ).fetchall()
        summaries: list[dict] = []
        for row in rows:
            state = GameState.model_validate_json(row["state_json"])
            summaries.append(
                {
                    "game_id": state.game_id,
                    "scenario_id": state.scenario_id,
                    "scenario_title": state.scenario_title,
                    "turn": state.turn,
                    "max_turns": state.max_turns,
                    "phase": state.phase.value,
                    "mode": state.options.mode,
                    "ai_profile": state.options.ai_profile,
                    "battle_report": state.options.battle_report,
                    "realistic_command": state.options.realistic_command,
                    "winner": state.winner.value if state.winner else None,
                    "updated_at": row["updated_at"],
                }
            )
        return summaries

    def events(self, game_id: str, after: int = 0) -> list[GameEvent]:
        rows = self.connection.execute(
            "SELECT event_json FROM events WHERE game_id = ? AND sequence > ? ORDER BY sequence",
            (game_id, after),
        ).fetchall()
        return [GameEvent.model_validate_json(row["event_json"]) for row in rows]

    def snapshots(self, game_id: str) -> list[tuple[int, GameState]]:
        rows = self.connection.execute(
            "SELECT sequence, state_json FROM snapshots WHERE game_id = ? ORDER BY sequence",
            (game_id,),
        ).fetchall()
        return [
            (int(row["sequence"]), GameState.model_validate_json(row["state_json"]))
            for row in rows
        ]

    def snapshot(self, game_id: str, sequence: int | None = None) -> tuple[int, GameState]:
        if sequence is None:
            row = self.connection.execute(
                "SELECT sequence, state_json FROM snapshots WHERE game_id = ? ORDER BY sequence DESC LIMIT 1",
                (game_id,),
            ).fetchone()
        else:
            row = self.connection.execute(
                """SELECT sequence, state_json FROM snapshots
                   WHERE game_id = ? AND sequence <= ? ORDER BY sequence DESC LIMIT 1""",
                (game_id, sequence),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown snapshot for game {game_id}")
        return int(row["sequence"]), GameState.model_validate_json(row["state_json"])

    def import_game(self, state: GameState, snapshots: list[tuple[int, GameState]]) -> None:
        """Atomically insert a validated portable save under a fresh game id."""
        if self.connection.execute(
            "SELECT 1 FROM games WHERE game_id = ?", (state.game_id,)
        ).fetchone():
            raise ValueError(f"Game {state.game_id} already exists")
        with self.connection:
            self.connection.execute(
                "INSERT INTO games(game_id, state_json) VALUES (?, ?)",
                (state.game_id, state.model_dump_json()),
            )
            self.connection.executemany(
                "INSERT INTO events(game_id, sequence, event_json) VALUES (?, ?, ?)",
                [(state.game_id, event.sequence, event.model_dump_json()) for event in state.events],
            )
            self.connection.executemany(
                "INSERT INTO snapshots(game_id, sequence, state_json) VALUES (?, ?, ?)",
                [
                    (state.game_id, sequence, snapshot.model_dump_json())
                    for sequence, snapshot in snapshots
                ],
            )

    def save_battle_entry(
        self,
        game_id: str,
        sequence: int,
        turn: int,
        phase: str,
        side: str,
        kind: str,
        image_path: str | None = None,
        content: str | None = None,
    ) -> None:
        """INSERT OR REPLACE：重复捕获/叙事对同 (game_id, sequence, side) 幂等。"""
        with self.connection:
            self.connection.execute(
                """INSERT OR REPLACE INTO battle_report
                   (game_id, sequence, turn, phase, side, kind, image_path, content)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (game_id, sequence, turn, phase, side, kind, image_path, content),
            )

    def battle_entries(self, game_id: str) -> list[BattleReportEntry]:
        rows = self.connection.execute(
            "SELECT * FROM battle_report WHERE game_id = ? ORDER BY sequence, side",
            (game_id,),
        ).fetchall()
        return [BattleReportEntry(**dict(row)) for row in rows]

    def battle_narrative_exists(self, game_id: str, turn: int, phase: str = "summary") -> bool:
        """该 (回合, 阶段) 叙事是否已落库（幂等门控：重放/重启不重复生成）。

        phase 默认 'summary'（回合总结）；每阶段叙述用各自阶段名（如 'gunnery'）。
        """
        row = self.connection.execute(
            "SELECT 1 FROM battle_report WHERE game_id = ? AND turn = ? AND kind = 'narrative' AND phase = ? LIMIT 1",
            (game_id, turn, phase),
        ).fetchone()
        return row is not None

    def save_research_consent(
        self, game_id: str, allow: bool, handle: str | None, scenario: str
    ) -> None:
        """科研用途同意记录（用户主动声明；对同一 game_id 幂等覆盖）。"""
        with self.connection:
            self.connection.execute(
                """INSERT OR REPLACE INTO research_consent(game_id, allow, handle, scenario)
                   VALUES (?, ?, ?, ?)""",
                (game_id, int(allow), handle, scenario),
            )

    def save_custom_scenario(self, scenario_id: str, definition: dict) -> None:
        payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":"))
        with self.connection:
            self.connection.execute(
                """INSERT INTO custom_scenarios(scenario_id, definition_json)
                   VALUES (?, ?)
                   ON CONFLICT(scenario_id) DO UPDATE SET
                     definition_json=excluded.definition_json,
                     updated_at=CURRENT_TIMESTAMP""",
                (scenario_id, payload),
            )

    def custom_scenario(self, scenario_id: str) -> dict:
        row = self.connection.execute(
            "SELECT definition_json FROM custom_scenarios WHERE scenario_id = ?",
            (scenario_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown custom scenario {scenario_id}")
        return json.loads(row["definition_json"])

    def custom_scenarios(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT scenario_id, definition_json, created_at, updated_at FROM custom_scenarios ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {"id": row["scenario_id"], "created_at": row["created_at"], "updated_at": row["updated_at"], **json.loads(row["definition_json"])}
            for row in rows
        ]

    def delete_custom_scenario(self, scenario_id: str) -> None:
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM custom_scenarios WHERE scenario_id = ?", (scenario_id,)
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Unknown custom scenario {scenario_id}")

    def research_consents(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM research_consent ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()
