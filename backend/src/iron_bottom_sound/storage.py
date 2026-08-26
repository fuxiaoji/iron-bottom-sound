from __future__ import annotations

import sqlite3
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

    def events(self, game_id: str, after: int = 0) -> list[GameEvent]:
        rows = self.connection.execute(
            "SELECT event_json FROM events WHERE game_id = ? AND sequence > ? ORDER BY sequence",
            (game_id, after),
        ).fetchall()
        return [GameEvent.model_validate_json(row["event_json"]) for row in rows]

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

    def battle_narrative_exists(self, game_id: str, turn: int) -> bool:
        """该回合叙事是否已落库（幂等门控：重放/重启不重复生成）。"""
        row = self.connection.execute(
            "SELECT 1 FROM battle_report WHERE game_id = ? AND turn = ? AND kind = 'narrative' LIMIT 1",
            (game_id, turn),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self.connection.close()
