from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .battle_report import (
    build_report_data,
    build_report_markdown,
    capture_after_advance,
)
from .engine import ORDER_PHASES, IronBottomEngine
from .llm import DeterministicCommander, LLMPlayerSession, OpenAICompatibleCommander
from .models import GameOptions, MatchReport, OptionalRules, Phase, Side
from .randomai import RandomCommander
from .state_export import export_frame, render_board
from .tactical import PROFILES, TacticalCommander


def make_session(
    side: Side, player: str, profile: str | None = None, model: str | None = None
) -> LLMPlayerSession:
    if player == "deterministic":
        return LLMPlayerSession(side, DeterministicCommander())
    if player == "tactical":
        return LLMPlayerSession(side, TacticalCommander(profile=PROFILES.get(profile or "balanced", PROFILES["balanced"])))
    if player == "random":
        return LLMPlayerSession(side, RandomCommander())
    if player == "deepseek":
        return LLMPlayerSession(side, OpenAICompatibleCommander(model=model or "deepseek-v4-flash"))
    raise ValueError(f"Unknown player {player}")


def _reports_root(artifact_dir: str | Path | None) -> Path:
    if artifact_dir is not None:
        return Path(artifact_dir)
    return Path("artifacts") / "battle-reports"


def run_match(
    scenario_id: str,
    *,
    axis: str = "deterministic",
    allies: str = "deterministic",
    axis_profile: str | None = None,
    allies_profile: str | None = None,
    deepseek_model: str | None = None,
    seed: int = 1,
    options: GameOptions | None = None,
    request_limit: int = 128,
    artifact_dir: str | Path | None = None,
    battle_report: bool = False,
) -> tuple[MatchReport, IronBottomEngine, dict[Side, LLMPlayerSession]]:
    started = time.perf_counter()
    engine = IronBottomEngine()
    state = engine.reset(scenario_id, seed, options or GameOptions(mode="llm"))
    sessions = {
        Side.AXIS: make_session(Side.AXIS, axis, axis_profile, deepseek_model),
        Side.ALLIES: make_session(Side.ALLIES, allies, allies_profile, deepseek_model),
    }
    frames: list[dict] = []
    boards: dict[Side, list[tuple[int, Phase, str]]] = {Side.AXIS: [], Side.ALLIES: []}
    report_entries: list[dict] = []
    report_root = _reports_root(artifact_dir) if battle_report else None
    narrative_commander = OpenAICompatibleCommander(timeout=30, max_tokens=800) if battle_report else None
    failure: str | None = None
    try:
        while state.phase != Phase.COMPLETE:
            # 投影一：每个阶段对双方各累积一帧世界态 + 一份棋盘（含自动阶段）。
            for side in Side:
                frames.append({**export_frame(state, engine, side, recent_limit=20), "side": side.value})
                boards[side].append((state.turn, state.phase, render_board(state, engine, side)))
            if state.phase in ORDER_PHASES:
                for side in Side:
                    if sum(len(session.audits) for session in sessions.values()) >= request_limit:
                        raise RuntimeError(f"LLM request limit {request_limit} reached")
                    batch = sessions[side].choose_orders(engine, state.game_id)
                    result = engine.submit_orders(state.game_id, batch)
                    if not result.valid:
                        raise RuntimeError(f"Validated session batch was rejected: {result.errors}")
            prev_phase = state.phase
            engine.advance(state.game_id)
            if battle_report:
                try:
                    entries, narrative_entry = capture_after_advance(
                        None, report_root, state, engine, prev_phase,
                        commander=narrative_commander,
                    )
                    report_entries.extend(entries)
                    if narrative_entry is not None:
                        report_entries.append(narrative_entry)
                except Exception:
                    pass  # 战报失败绝不影响对局
    except (RuntimeError, ValueError) as error:
        failure = str(error)

    request_count = sum(len(session.audits) for session in sessions.values())
    report = MatchReport(
        game_id=state.game_id,
        scenario_id=state.scenario_id,
        seed=seed,
        winner=state.winner,
        victory_reason=state.victory_reason,
        completed=state.phase == Phase.COMPLETE,
        request_count=request_count,
        fallback_count=0,
        manual_state_changes=0,
        axis_plan_count=len(sessions[Side.AXIS].plan_sheets),
        allies_plan_count=len(sessions[Side.ALLIES].plan_sheets),
        total_input_tokens=sum(audit.input_tokens for session in sessions.values() for audit in session.audits),
        total_output_tokens=sum(audit.output_tokens for session in sessions.values() for audit in session.audits),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        passed=(state.phase == Phase.COMPLETE and failure is None and request_count <= request_limit),
        failure_reason=failure,
    )
    if artifact_dir is not None:
        write_match_artifacts(Path(artifact_dir), report, state, sessions, frames=frames, boards=boards)
    if battle_report and report_root is not None:
        write_battle_report_artifacts(report_root, state, engine, report_entries)
    return report, engine, sessions


def write_match_artifacts(
    directory: Path, report, state, sessions,
    frames: list[dict] | None = None,
    boards: dict[Side, list[tuple[int, Phase, str]]] | None = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "match-report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (directory / "event-replay.json").write_text(
        json.dumps([event.model_dump(mode="json") for event in state.events], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if frames:
        (directory / f"{state.game_id}-frames.jsonl").write_text(
            "\n".join(json.dumps(frame, ensure_ascii=False) for frame in frames),
            encoding="utf-8",
        )
    if boards:
        for side, entries in boards.items():
            parts = [
                f"# turn {turn} · {phase.value} · {side.value}\n{board}"
                for turn, phase, board in entries
            ]
            (directory / f"{state.game_id}-board-{side.value}.txt").write_text(
                "\n\n".join(parts), encoding="utf-8"
            )
    for side, session in sessions.items():
        private = {
            "side": side.value,
            "plans": [plan.model_dump(mode="json") for plan in session.plan_sheets],
            "audits": [audit.model_dump(mode="json") for audit in session.audits],
        }
        (directory / f"{side.value}-private.json").write_text(
            json.dumps(private, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def write_battle_report_artifacts(
    directory: Path, state, engine, report_entries: list[dict],
) -> None:
    """AI-vs-AI 战报产物：自包含 MD + 条目索引 JSON（供测试断言）。"""
    directory.mkdir(parents=True, exist_ok=True)
    data = build_report_data(state, engine, report_entries)
    (directory / f"{state.game_id}-battle-report.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # utf-8-sig：带 BOM，中文 Windows 编辑器/VS Code 才不会误判成 GBK 显示乱码。
    (directory / f"{state.game_id}-battle-report.md").write_text(
        build_report_markdown(directory, data, state.game_id), encoding="utf-8-sig"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an isolated dual-player Iron Bottom Sound IV match")
    parser.add_argument("--scenario", default="IBS-S-03", choices=("IBS-S-01", "IBS-S-03"))
    parser.add_argument("--axis", default="deterministic", choices=("deterministic", "tactical", "random", "deepseek"))
    parser.add_argument("--allies", default="deterministic", choices=("deterministic", "tactical", "random", "deepseek"))
    parser.add_argument("--axis-profile", default=None, choices=tuple(PROFILES))
    parser.add_argument("--allies-profile", default=None, choices=tuple(PROFILES))
    parser.add_argument("--model", default=None,
                        help="deepseek 玩家使用的模型（默认 OpenAICompatibleCommander 默认值）")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--request-limit", type=int, default=128)
    parser.add_argument("--all-optional", action="store_true")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--battle-report", action="store_true",
                        help="每阶段双视角 PNG + 每回合叙事 + 自包含 MD 战报（写进 artifact 目录）")
    args = parser.parse_args()
    options = GameOptions(
        mode="llm",
        optional_rules=OptionalRules(**{
            name: args.all_optional for name in OptionalRules.model_fields
        }),
    )
    artifacts = args.artifacts or Path("artifacts") / "matches" / f"{args.scenario}-{args.seed}"
    report, _, _ = run_match(
        args.scenario,
        axis=args.axis,
        allies=args.allies,
        axis_profile=args.axis_profile,
        allies_profile=args.allies_profile,
        deepseek_model=args.model,
        seed=args.seed,
        options=options,
        request_limit=args.request_limit,
        artifact_dir=artifacts,
        battle_report=args.battle_report,
    )
    print(report.model_dump_json(indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
