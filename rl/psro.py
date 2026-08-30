"""Crash-resumable PSRO-lite league for the adaptive torpedo state-machine AI.

The engine remains the sole adjudicator.  Long runs persist every completed game to an
atomic checkpoint and expose ``status.json`` plus ``dashboard.html`` for live monitoring.

Production run (three rounds, realistic Erma is the primary slot)::

    python -m rl.psro --out rl/results/psro-torpedo-v1 --serve-dashboard

Resume after interruption or power loss::

    python -m rl.psro --out rl/results/psro-torpedo-v1 --resume --serve-dashboard

Use ``--smoke`` before a long run.  The checked-in dashboard polls status once per second;
the checkpoint, not games.jsonl, is authoritative after an abrupt shutdown.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import signal
import sqlite3
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from iron_bottom_sound.champions import CHAMPIONS
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import GameOptions
from iron_bottom_sound.tactical import PROFILES, TacticalProfile


GENES: list[tuple[str, float, float]] = [
    ("w_enemy_heat", 0.0, 4.0), ("w_fire_pressure", 0.0, 4.0),
    ("w_approach", -2.0, 3.0), ("w_formation", -2.0, 4.0),
    ("line_ahead", -2.0, 4.0), ("w_predict_opponent", 0.0, 2.0),
    ("w_retreat", 0.0, 3.0), ("w_protect_own", 0.0, 3.0),
    ("w_vp", 0.0, 3.0), ("w_finish", 0.0, 3.0),
    ("w_self_status", 0.0, 3.0), ("torpedo_min_expected", 0.0, 0.8),
    ("retreat_hull_threshold", 0.1, 0.7), ("temperature", 0.0, 1.5),
    ("approach_range", 6.0, 24.0), ("torpedo_max_range", 6.0, 20.0),
    ("w_torpedo_avoid", 0.5, 6.0), ("torpedo_min_tactical_score", 0.0, 1.0),
]
INTEGER_GENES = {"approach_range", "torpedo_max_range"}
FITNESS_REVISION = 2
INVALID_FITNESS = -2.0


class TrainingInterrupted(RuntimeError):
    """A graceful stop that leaves the league resumable, not failed."""


@dataclass
class Config:
    scenarios: list[str] = field(default_factory=lambda: ["IBS-S-03", "IBS-S-01", "IBS-S-EM-01"])
    primary_scenario: str = "IBS-S-EM-01"
    rounds: int = 3
    population: int = 32
    generations: int = 6
    seeds_per_slot: int = 4
    workers: int = 20
    seed: int = 20260829
    out: str = "rl/results/psro-realistic-v1"
    ruleset: str = "realistic-v1"
    dashboard_port: int = 8765
    smoke: bool = False
    fitness_revision: int = FITNESS_REVISION


def _profile_dict(profile: TacticalProfile) -> dict[str, Any]:
    return profile.model_dump(mode="json")


def _profile_from(data: dict[str, Any]) -> TacticalProfile:
    return TacticalProfile.model_validate(data)


def _atomic_json(path: Path, data: Any, *, replace_attempts: int = 20) -> None:
    """Durably replace a JSON projection, tolerating transient Windows readers.

    Browsers, indexers and antivirus scanners may briefly open the destination
    without delete sharing, which makes os.replace raise WinError 5 even though
    both files belong to this process.  Retrying the replace preserves atomicity;
    rewriting the destination in place would expose partial JSON to the dashboard.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(replace_attempts):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt + 1 >= replace_attempts:
                raise
            time.sleep(min(0.01 * (2 ** min(attempt, 4)), 0.25))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _game_key(kind: str, *parts: Any) -> str:
    return "|".join([kind, *(str(part) for part in parts)])


def _friendly_incidents(state) -> tuple[int, int]:
    collisions = 0
    torpedo_hits = 0
    for event in state.events:
        if event.type in {"collision", "collision_check"} and event.payload.get("friendly"):
            collisions += 1
        if (
            event.type == "torpedo_hit"
            and event.payload.get("attacker_side") == event.payload.get("target_side")
        ):
            torpedo_hits += 1
    return collisions, torpedo_hits


def _run_game(job: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        realistic = bool(job.get("realistic_command", True))
        report, engine, sessions = run_match(
            job["scenario"], axis="tactical", allies="tactical",
            axis_profile=_profile_from(job["axis_profile"]),
            allies_profile=_profile_from(job["allies_profile"]),
            seed=job["seed"], options=GameOptions(realistic_command=realistic),
            request_limit=180,
        )
        state = engine.get(report.game_id)
        collisions, friendly_torpedoes = _friendly_incidents(state)
        axis_score, allies_score = state.score.get("axis", 0), state.score.get("allies", 0)
        utility = 0.0
        if report.winner:
            utility = 1.0 if report.winner.value == "axis" else -1.0
        utility += max(-0.25, min(0.25, (axis_score - allies_score) * 0.005))
        if not report.passed or collisions or friendly_torpedoes:
            utility = -2.0
        return {
            "ok": report.passed and not collisions and not friendly_torpedoes,
            "winner": report.winner.value if report.winner else None,
            "utility": utility, "axis_score": axis_score, "allies_score": allies_score,
            "friendly_collisions": collisions, "friendly_torpedo_hits": friendly_torpedoes,
            "turn": state.turn, "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error": report.failure_reason,
        }
    except Exception as error:
        return {
            "ok": False, "winner": None, "utility": -2.0, "axis_score": 0,
            "allies_score": 0, "friendly_collisions": 0, "friendly_torpedo_hits": 0,
            "turn": 0, "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error": f"{type(error).__name__}: {error}",
        }


def regret_matching(matrix: list[list[float]], iterations: int = 5000) -> list[float]:
    """Deterministic row-player regret matching over a zero-sum empirical matrix."""
    n = len(matrix)
    if not n:
        return []
    regrets = [0.0] * n
    average = [0.0] * n
    opponent = [1.0 / n] * n
    for _ in range(iterations):
        positive = [max(0.0, value) for value in regrets]
        total = sum(positive)
        strategy = [value / total for value in positive] if total else [1.0 / n] * n
        for i, probability in enumerate(strategy):
            average[i] += probability
        action_values = [sum(matrix[i][j] * opponent[j] for j in range(n)) for i in range(n)]
        current = sum(strategy[i] * action_values[i] for i in range(n))
        regrets = [regrets[i] + action_values[i] - current for i in range(n)]
        # The opponent uses regret matching on the negated transpose.
        opp_values = [-sum(strategy[i] * matrix[i][j] for i in range(n)) for j in range(n)]
        best = max(range(n), key=lambda j: (opp_values[j], -j))
        step = 2.0 / (2.0 + _)
        opponent = [(1.0 - step) * value + (step if j == best else 0.0) for j, value in enumerate(opponent)]
    total = sum(average) or 1.0
    return [value / total for value in average]


class League:
    def __init__(self, config: Config, resume: bool = False) -> None:
        self.config = config
        self.root = Path(config.out)
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.root / "checkpoint.json"
        self.status_path = self.root / "status.json"
        self.games_path = self.root / "games.jsonl"
        self.database_path = self.root / "results.sqlite3"
        self.dashboard_path = self.root / "dashboard.html"
        self.started = time.time()
        self.stop_requested = False
        self._io_lock = threading.RLock()
        self._init_database()
        if resume:
            if not self.checkpoint_path.exists():
                raise FileNotFoundError(f"No checkpoint at {self.checkpoint_path}")
            self.state = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            self.config = Config(**self.state["config"])
            # Migrate early JSON-only checkpoints once, then use the WAL ledger.
            legacy_games = self.state.pop("games", {})
            for key, row in legacy_games.items():
                self._record_game(key, row, append_log=False)
            self.state["games"] = self._load_games()
            self._migrate_fitness_state()
        else:
            self.state = {
                "version": 1, "config": asdict(config), "stage": "initializing", "round": 0,
                "strategies": self._initial_strategies(), "games": {}, "ga": {},
                "meta_distribution": {}, "created_at": time.time(),
                "fitness_revision": config.fitness_revision,
            }
            self._checkpoint()
        source_dashboard = Path(__file__).with_name("psro_dashboard.html")
        if source_dashboard.exists():
            self.dashboard_path.write_text(source_dashboard.read_text(encoding="utf-8"), encoding="utf-8")

    def _migrate_fitness_state(self) -> None:
        """Discard polluted strategy state while retaining reusable game rows.

        Revision 1 inverted the ``-2`` invalid-game sentinel when the evolving
        individual played Allies, allowing a failed game to improve fitness.
        The SQLite ledger remains valuable.  Resetting only the strategic
        projection lets deterministic job definitions reuse matching valid
        rows while stale descendants are detected and recomputed.
        """
        previous = int(self.state.get("fitness_revision", 1))
        if previous >= self.config.fitness_revision:
            return
        self.state.update({
            "fitness_revision": self.config.fitness_revision,
            "config": asdict(self.config),
            "stage": "fitness_revision_migration",
            "round": 0,
            "strategies": self._initial_strategies(),
            "ga": {},
            "meta_distribution": {},
        })
        for key in (
            "payoff_matrix", "current_best", "last_error", "running_jobs",
            "expected_games", "last_progress_at",
        ):
            self.state.pop(key, None)
        self._checkpoint()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _init_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS games (key TEXT PRIMARY KEY, payload TEXT NOT NULL, finished_at REAL NOT NULL)"
            )

    def _load_games(self) -> dict[str, dict[str, Any]]:
        with self._connect() as connection:
            return {
                key: json.loads(payload)
                for key, payload in connection.execute("SELECT key, payload FROM games")
            }

    def _record_game(self, key: str, row: dict[str, Any], *, append_log: bool = True) -> None:
        previous = self.state.setdefault("games", {}).get(key)
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO games(key, payload, finished_at) VALUES (?, ?, ?)",
                (key, payload, float(row.get("finished_at", time.time()))),
            )
        self.state["games"][key] = row
        if row.get("error"):
            self.state["last_error"] = row["error"]
        elif previous is not None and not previous.get("ok"):
            remaining = [
                game for game in self.state["games"].values()
                if not game.get("ok") and game.get("error")
            ]
            latest = max(remaining, key=lambda game: game.get("finished_at", 0), default=None)
            self.state["last_error"] = latest.get("error") if latest else None
        if append_log:
            _append_jsonl(self.games_path, row)

    @staticmethod
    def _initial_strategies() -> list[dict[str, Any]]:
        names = [
            "balanced", "torpedo", "line", "brawl", "evolved", "direct_attack",
            "area_denial", "break_crossing_t", "formation_split", "crossfire", "cover_withdrawal",
        ]
        strategies = []
        for name in names:
            profile = CHAMPIONS.get(name, PROFILES.get(name))
            if profile is None:
                continue
            strategies.append({"name": name, "profile": _profile_dict(profile), "origin": "initial"})
        return strategies

    def _checkpoint(self) -> None:
        with self._io_lock:
            self.state["updated_at"] = time.time()
            # Per-game payloads live in SQLite WAL.  Keeping them out of the phase checkpoint
            # avoids O(number_of_games squared) write amplification during multi-hour runs.
            snapshot = {key: value for key, value in self.state.items() if key != "games"}
            snapshot["game_count"] = len(self.state.get("games", {}))
            _atomic_json(self.checkpoint_path, snapshot)
            self._status()

    def _status(self) -> None:
        with self._io_lock:
            now = time.time()
            games = self.state.get("games", {})
            valid_games = sum(1 for row in games.values() if row.get("ok"))
            invalid_games = len(games) - valid_games
            durations = [row.get("elapsed_ms", 0) / 1000 for row in games.values() if row.get("elapsed_ms")]
            expected = int(self.state.get("expected_games", len(games)))
            remaining = max(0, expected - len(games))
            mean = sum(durations[-200:]) / max(1, len(durations[-200:]))
            progress_age = max(0.0, now - float(self.state.get("last_progress_at", now)))
            running_jobs = int(self.state.get("running_jobs", 0))
            status = {
                "stage": self.state.get("stage"), "round": self.state.get("round", 0),
                "completed_games": len(games), "expected_games": expected,
                "valid_games": valid_games, "invalid_games": invalid_games,
                "progress": len(games) / expected if expected else 0.0,
                "eta_seconds": mean * remaining / max(1, self.config.workers),
                "heartbeat": now, "progress_age_seconds": progress_age,
                "running_jobs": running_jobs,
                "stalled": running_jobs > 0 and progress_age >= 300,
                "strategies": [item["name"] for item in self.state["strategies"]],
                "meta_distribution": self.state.get("meta_distribution", {}),
                "current_best": self.state.get("current_best"),
                "primary_scenario": self.config.primary_scenario,
                "last_error": self.state.get("last_error"),
                "status_write_error": self.state.get("status_write_error"),
            }
            try:
                _atomic_json(self.status_path, status)
            except PermissionError as error:
                # status.json is a disposable live projection.  A browser or
                # scanner holding it must never kill a multi-hour rules run;
                # keep the last complete file and retry on the next heartbeat.
                self.state["status_write_error"] = f"{type(error).__name__}: {error}"
            else:
                self.state.pop("status_write_error", None)

    def _run_jobs(self, jobs: list[tuple[str, dict[str, Any]]]) -> None:
        # Invalid/interrupted rows are evidence, not cache hits. Re-run their
        # deterministic keys after a code fix and replace the SQLite payload.
        missing = [
            (key, job) for key, job in jobs
            if key not in self.state["games"]
            or not self.state["games"][key].get("ok")
            or any(self.state["games"][key].get(field) != value for field, value in job.items())
        ]
        self.state["expected_games"] = len(
            set(self.state["games"]) | {key for key, _job in jobs}
        )
        self._checkpoint()
        if self.stop_requested:
            self.state["stage"] = "interrupted"
            self.state["last_error"] = None
            self._checkpoint()
            raise TrainingInterrupted("training interrupted before scheduling more games")
        if not missing:
            return
        self.state["last_progress_at"] = time.time()
        self.state["running_jobs"] = len(missing)
        heartbeat_stop = threading.Event()

        def heartbeat() -> None:
            while not heartbeat_stop.wait(2.0):
                self._status()

        heartbeat_thread = threading.Thread(target=heartbeat, name="psro-heartbeat", daemon=True)
        heartbeat_thread.start()
        try:
            with ProcessPoolExecutor(max_workers=self.config.workers) as pool:
                futures = {pool.submit(_run_game, job): (key, job) for key, job in missing}
                for future in as_completed(futures):
                    key, job = futures[future]
                    row = {**job, **future.result(), "key": key, "finished_at": time.time()}
                    self._record_game(key, row)
                    self.state["last_progress_at"] = time.time()
                    self.state["running_jobs"] = max(0, int(self.state["running_jobs"]) - 1)
                    self._checkpoint()
                    if self.stop_requested:
                        for pending in futures:
                            pending.cancel()
                        break
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=3.0)
            self.state["running_jobs"] = 0
            self._status()
        if self.stop_requested:
            self.state["stage"] = "interrupted"
            self.state["last_error"] = None
            self._checkpoint()
            raise TrainingInterrupted("training interrupted after persisting completed games")

    def _matrix_jobs(self) -> list[tuple[str, dict[str, Any]]]:
        strategies = self.state["strategies"]
        jobs = []
        for axis in strategies:
            for allies in strategies:
                for scenario_index, scenario in enumerate(self.config.scenarios):
                    for seed_index in range(self.config.seeds_per_slot):
                        seed = self.config.seed + scenario_index * 10_000 + seed_index
                        key = _game_key(
                            self.config.ruleset, "matrix", axis["name"], allies["name"], scenario, seed
                        )
                        jobs.append((key, {
                            "kind": "matrix", "axis_name": axis["name"], "allies_name": allies["name"],
                            "axis_profile": axis["profile"], "allies_profile": allies["profile"],
                            "scenario": scenario, "seed": seed,
                            "ruleset": self.config.ruleset, "realistic_command": True,
                        }))
        return jobs

    def _matrix(self) -> list[list[float]]:
        strategies = self.state["strategies"]
        result = []
        for axis in strategies:
            row = []
            for allies in strategies:
                values = [
                    game["utility"] for game in self.state["games"].values()
                    if game.get("kind") == "matrix" and game.get("axis_name") == axis["name"]
                    and game.get("allies_name") == allies["name"]
                    and game.get("ruleset") == self.config.ruleset
                ]
                row.append(sum(values) / max(1, len(values)))
            result.append(row)
        # Remove first-player/side bias by antisymmetrizing reciprocal cells.
        return [[(result[i][j] - result[j][i]) / 2.0 for j in range(len(result))] for i in range(len(result))]

    def _random_profile(self, rng: random.Random, base: TacticalProfile | None = None) -> TacticalProfile:
        base = base or PROFILES["adaptive"]
        values = base.model_dump()
        for name, lo, hi in GENES:
            center = float(getattr(base, name))
            value = max(lo, min(hi, center + rng.gauss(0, (hi - lo) * 0.15)))
            values[name] = int(round(value)) if name in INTEGER_GENES else value
        values["torpedo_doctrine"] = "adaptive"
        return TacticalProfile(**values)

    def _br_jobs(self, round_index: int, generation: int, population: list[dict[str, Any]], mixture) -> list:
        strategies = self.state["strategies"]
        # Deterministic stratified opponent draw; higher mixture mass receives more slots.
        opponent_slots = sorted(
            range(len(strategies)), key=lambda index: (-mixture[index], strategies[index]["name"])
        )[: (1 if self.config.smoke else max(3, min(6, len(strategies))))]
        jobs = []
        for individual in population:
            for opponent_index in opponent_slots:
                opponent = strategies[opponent_index]
                for scenario_index, scenario in enumerate(self.config.scenarios):
                    repeats = 1 if self.config.smoke else (2 if scenario == self.config.primary_scenario else 1)
                    for repeat in range(repeats):
                        for side in (("axis",) if self.config.smoke else ("axis", "allies")):
                            seed = (
                                self.config.seed + 500_000 + round_index * 100_000
                                + generation * 10_000 + individual["id"] * 100 + opponent_index * 3 + repeat
                            )
                            axis_profile = individual["profile"] if side == "axis" else opponent["profile"]
                            allies_profile = opponent["profile"] if side == "axis" else individual["profile"]
                            key = _game_key(
                                self.config.ruleset, "br", round_index, generation,
                                individual["id"], opponent["name"], scenario, repeat, side,
                            )
                            jobs.append((key, {
                                "kind": "br", "round": round_index, "generation": generation,
                                "individual": individual["id"], "individual_side": side,
                                "opponent": opponent["name"], "mixture_weight": mixture[opponent_index],
                                "axis_profile": axis_profile, "allies_profile": allies_profile,
                                "scenario": scenario, "seed": seed,
                                "ruleset": self.config.ruleset, "realistic_command": True,
                            }))
        return jobs

    def _fitness(self, round_index: int, generation: int, individual: int) -> float:
        rows = [
            game for game in self.state["games"].values()
            if game.get("kind") == "br" and game.get("round") == round_index
            and game.get("generation") == generation and game.get("individual") == individual
            and game.get("ruleset") == self.config.ruleset
        ]
        # Invalid adjudications are never outcomes and may not be side-flipped.
        # A finite sentinel keeps checkpoints strict-JSON compatible.
        if not rows or any(not game.get("ok") for game in rows):
            return INVALID_FITNESS
        values = []
        for game in rows:
            utility = game["utility"] if game["individual_side"] == "axis" else -game["utility"]
            primary_bonus = 1.5 if game["scenario"] == self.config.primary_scenario else 1.0
            values.append(utility * primary_bonus * max(0.05, game["mixture_weight"]))
        return sum(values) / max(1, sum(
            (1.5 if game["scenario"] == self.config.primary_scenario else 1.0)
            * max(0.05, game["mixture_weight"]) for game in rows
        ))

    def _breed(self, population: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
        ranked = sorted(population, key=lambda item: (-item["fitness"], item["id"]))
        elite_count = max(2, self.config.population // 8)
        parents = ranked[: max(elite_count, self.config.population // 3)]
        children = [{"id": i, "profile": item["profile"]} for i, item in enumerate(ranked[:elite_count])]
        while len(children) < self.config.population:
            left, right = rng.choice(parents), rng.choice(parents)
            lp, rp = left["profile"], right["profile"]
            values = dict(lp)
            for name, lo, hi in GENES:
                value = (float(lp[name]) + float(rp[name])) / 2 + rng.gauss(0, (hi - lo) * 0.07)
                value = max(lo, min(hi, value))
                values[name] = int(round(value)) if name in INTEGER_GENES else value
            values["torpedo_doctrine"] = "adaptive"
            children.append({"id": len(children), "profile": _profile_dict(TacticalProfile(**values))})
        return children

    def _train_best_response(self, round_index: int, mixture: list[float]) -> dict[str, Any]:
        rng = random.Random(self.config.seed + round_index * 997)
        ga = self.state["ga"].setdefault(str(round_index), {})
        population = ga.get("population")
        start_generation = int(ga.get("generation", 0))
        if population is None:
            population = [
                {"id": index, "profile": _profile_dict(self._random_profile(rng))}
                for index in range(self.config.population)
            ]
        for generation in range(start_generation, self.config.generations):
            self.state["stage"] = f"best_response_round_{round_index}_generation_{generation}"
            self._run_jobs(self._br_jobs(round_index, generation, population, mixture))
            for individual in population:
                individual["fitness"] = self._fitness(round_index, generation, individual["id"])
            best = max(population, key=lambda item: (item["fitness"], -item["id"]))
            self.state["current_best"] = {"name": f"round-{round_index}-gen-{generation}", "fitness": best["fitness"]}
            ga.update({"generation": generation + 1, "population": population, "best": best})
            self._checkpoint()
            if generation + 1 < self.config.generations:
                population = self._breed(population, rng)
                ga["population"] = population
                self._checkpoint()
        return ga["best"]

    def run(self) -> None:
        for round_index in range(int(self.state.get("round", 0)), self.config.rounds):
            self.state["round"] = round_index
            self.state["stage"] = f"payoff_matrix_round_{round_index}"
            self._run_jobs(self._matrix_jobs())
            matrix_keys = {key for key, _job in self._matrix_jobs()}
            invalid_matrix = [
                game for key, game in self.state["games"].items()
                if key in matrix_keys and not game.get("ok")
            ]
            if invalid_matrix:
                raise RuntimeError(f"baseline payoff matrix contains {len(invalid_matrix)} invalid games")
            matrix = self._matrix()
            mixture = regret_matching(matrix)
            self.state["meta_distribution"] = {
                strategy["name"]: mixture[index]
                for index, strategy in enumerate(self.state["strategies"])
            }
            self.state["payoff_matrix"] = matrix
            self._checkpoint()
            best = self._train_best_response(round_index, mixture)
            if best["fitness"] <= -1.5:
                raise RuntimeError("all best-response candidates were invalid; champion not registered")
            name = f"psro-r{round_index + 1}"
            if not any(item["name"] == name for item in self.state["strategies"]):
                self.state["strategies"].append({
                    "name": name, "profile": best["profile"], "origin": "best_response",
                    "fitness": best["fitness"],
                })
            self.state["round"] = round_index + 1
            self._checkpoint()
        self.state["stage"] = "complete"
        self._checkpoint()


def serve_dashboard(directory: Path, port: int) -> ThreadingHTTPServer:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)
        def log_message(self, _format, *_args):
            return
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Crash-resumable PSRO-lite torpedo league")
    parser.add_argument("--out", default="rl/results/psro-realistic-v1")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--serve-dashboard", action="store_true")
    parser.add_argument("--dashboard-port", type=int, default=8765)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = Config(out=args.out, workers=args.workers, dashboard_port=args.dashboard_port)
    if args.smoke:
        config.rounds, config.population, config.generations = 1, 1, 1
        config.seeds_per_slot, config.workers = 1, min(args.workers, 2)
        config.scenarios = ["IBS-S-EM-01"]
        config.smoke = True
    league = League(config, resume=args.resume)
    if args.smoke and not args.resume:
        keep = {"balanced"}
        league.state["strategies"] = [
            strategy for strategy in league.state["strategies"] if strategy["name"] in keep
        ]
        league._checkpoint()
    dashboard = serve_dashboard(league.root, config.dashboard_port) if args.serve_dashboard else None
    if dashboard:
        print(f"Dashboard: http://127.0.0.1:{config.dashboard_port}/dashboard.html", flush=True)
    def request_stop(*_args):
        league.stop_requested = True
        league._checkpoint()
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    try:
        league.run()
    except TrainingInterrupted:
        league.state["stage"] = "interrupted"
        league.state["last_error"] = None
        league._checkpoint()
        return 130
    except Exception as error:
        league.state["stage"] = "failed"
        league.state["last_error"] = f"{type(error).__name__}: {error}"
        league._checkpoint()
        raise
    finally:
        league._checkpoint()
        if dashboard:
            dashboard.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
