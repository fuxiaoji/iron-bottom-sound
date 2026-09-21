"""Mandatory runner hardening (Phase A v3.1 §"Mandatory runner hardening").

- EXPERIMENT_REGISTRY.csv is append-only, one row per attempted unit.
- Exactly one FINAL status per attempt, written in a `finally` block:
  SUCCESS / REJECTED_WITH_REASON / ERROR_WITH_TRACE.
- Exception type, message and a traceback file path are saved on error.
- A JSONL checkpoint is written at least every 10 units.
- `reconcile()` asserts attempted == success + rejected + error per
  task x track x method; a failed reconciliation forbids emitting a verdict.
"""

from __future__ import annotations

import csv
import json
import random
import traceback
from collections import defaultdict
from pathlib import Path

PA = Path(__file__).resolve().parents[1]
REGISTRY = PA / "raw" / "EXPERIMENT_REGISTRY.csv"
JSONL = PA / "raw" / "registry_checkpoint.jsonl"
TRACE_DIR = PA / "logs" / "traces"
FIELDS = ["unit_id", "track", "task", "method", "attempted", "status", "reason",
          "exception_type", "exception_message", "trace_path", "sim_queries",
          "sim_steps", "wall_seconds", "payload"]


class Registry:
    """Append-only attempt registry with per-unit final status."""

    def __init__(self, path: Path = REGISTRY):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", newline="") as fh:
                csv.DictWriter(fh, fieldnames=FIELDS).writeheader()
        self.jsonl = JSONL
        self.trace_dir = TRACE_DIR
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.counts = defaultdict(lambda: {"attempted": 0, "SUCCESS": 0,
                                           "REJECTED_WITH_REASON": 0,
                                           "ERROR_WITH_TRACE": 0})
        self._since_ckpt = 0

    def _write(self, row: dict):
        with open(self.path, "a", newline="") as fh:
            csv.DictWriter(fh, fieldnames=FIELDS).writerow(row)

    def unit(self, unit_id, track, task, method):
        """Context manager guaranteeing exactly one final status in finally."""
        return _Unit(self, unit_id, track, task, method)

    def _finalise(self, unit_id, track, task, method, status, reason="",
                  exc=None, sim_queries=0, sim_steps=0, wall_seconds=0.0, payload=None):
        key = (track, task, method)
        self.counts[key]["attempted"] += 1
        self.counts[key][status] += 1
        exc_type = exc_message = trace_path = ""
        if exc is not None:
            exc_type = type(exc).__name__
            exc_message = str(exc)[:400]
            trace_path = str(self.trace_dir / f"{unit_id}.trace")
            with open(trace_path, "w") as fh:
                fh.write("".join(traceback.format_exception(
                    type(exc), exc, exc.__traceback__)))
        row = {"unit_id": unit_id, "track": track, "task": task, "method": method,
               "attempted": 1, "status": status, "reason": reason,
               "exception_type": exc_type, "exception_message": exc_message,
               "trace_path": trace_path, "sim_queries": sim_queries,
               "sim_steps": sim_steps, "wall_seconds": round(wall_seconds, 3),
               "payload": json.dumps(payload or {}, default=str)[:800]}
        self._write(row)
        with open(self.jsonl, "a") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        self._since_ckpt += 1
        if self._since_ckpt >= 10:
            self.checkpoint()
            self._since_ckpt = 0

    def checkpoint(self):
        with open(self.jsonl, "a") as fh:
            fh.write(json.dumps({"checkpoint": True,
                                 "counts": {f"{k[0]}|{k[1]}|{k[2]}": v
                                            for k, v in self.counts.items()}}) + "\n")

    def reconcile(self, strict=True) -> dict:
        """attempted == success + rejected + error, per task x track x method."""
        bad = {}
        for key, c in self.counts.items():
            total = c["SUCCESS"] + c["REJECTED_WITH_REASON"] + c["ERROR_WITH_TRACE"]
            if total != c["attempted"]:
                bad[f"{key[0]}|{key[1]}|{key[2]}"] = {"attempted": c["attempted"],
                                                      "sum_of_statuses": total}
        out = {"ok": not bad, "violations": bad,
               "counts": {f"{k[0]}|{k[1]}|{k[2]}": dict(v) for k, v in self.counts.items()},
               "totals": {"attempted": sum(c["attempted"] for c in self.counts.values()),
                          "SUCCESS": sum(c["SUCCESS"] for c in self.counts.values()),
                          "REJECTED_WITH_REASON": sum(c["REJECTED_WITH_REASON"] for c in self.counts.values()),
                          "ERROR_WITH_TRACE": sum(c["ERROR_WITH_TRACE"] for c in self.counts.values())}}
        if strict and not out["ok"]:
            raise AssertionError(f"registry reconciliation failed: {bad}")
        return out


class _Unit:
    def __init__(self, reg: Registry, unit_id, track, task, method):
        self.reg, self.unit_id, self.track, self.task, self.method = reg, unit_id, track, task, method
        self.status = "ERROR_WITH_TRACE"
        self.reason = "unit exited without setting a status"
        self.exc = None
        self.sim_queries = self.sim_steps = 0
        self.wall_seconds = 0.0
        self.payload = {}

    def __enter__(self):
        return self

    def success(self, payload=None, **kw):
        self.status, self.reason = "SUCCESS", ""
        self.payload = payload or {}
        for k, v in kw.items():
            setattr(self, k, v)

    def reject(self, reason, payload=None, **kw):
        self.status, self.reason = "REJECTED_WITH_REASON", reason
        self.payload = payload or {}
        for k, v in kw.items():
            setattr(self, k, v)

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self.status, self.exc = "ERROR_WITH_TRACE", exc
            self.reason = f"{exc_type.__name__}: {exc}"[:200]
        self.reg._finalise(self.unit_id, self.track, self.task, self.method,
                           self.status, self.reason, self.exc,
                           self.sim_queries, self.sim_steps, self.wall_seconds,
                           self.payload)
        return False          # never swallow: the exception propagates


# ---------------------------------------------------------------- statistics
def bootstrap_ci_mean(values, n=10_000, seed=20260921, alpha=0.05):
    if not values:
        return None
    rng = random.Random(seed)
    k = len(values)
    means = []
    for _ in range(n):
        means.append(sum(values[rng.randrange(k)] for _ in range(k)) / k)
    means.sort()
    return [means[int((alpha / 2) * n)], means[int((1 - alpha / 2) * n)]]


def bootstrap_ci_paired(a, b, n=10_000, seed=20260921, alpha=0.05):
    """CI of mean(a - b) with paired resampling over units."""
    if not a or len(a) != len(b):
        return None
    diffs = [x - y for x, y in zip(a, b)]
    return bootstrap_ci_mean(diffs, n=n, seed=seed, alpha=alpha)


def cohens_d(a, b):
    import math
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    return None if sp == 0 else (ma - mb) / sp


def quantiles(values):
    v = sorted(values)
    if not v:
        return {}
    def q(p):
        return v[int(p * (len(v) - 1))]
    q25, q50, q75 = q(0.25), q(0.50), q(0.75)
    return {"Q25": q25, "Q50": q50, "Q75": q75, "IQR": q75 - q25,
            "mean": sum(v) / len(v), "n": len(v)}
