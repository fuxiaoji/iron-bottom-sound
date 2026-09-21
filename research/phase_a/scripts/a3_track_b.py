"""Phase A.3 Track B — acquisition positive control (§2.4) + valid tournament (§2.5).

The corrected STRUCTURED_ACTIVE: endpoint probes per severity line, then true
bisection that strictly shrinks a candidate transition interval; cross-line
allocation round-robins unresolved lines in a frozen order. Everything runs on the
immutable A.2 label tables — no new simulation.

    .venv_phase_a/bin/python research/phase_a/scripts/a3_track_b.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry  # noqa: E402

PA = Path(__file__).resolve().parents[1]
OUT = PA / "raw" / "track_b_a3"
OUT.mkdir(parents=True, exist_ok=True)
TASKS = ("balance", "sampling")
KS = (25, 50, 100, 200)
REPS = 30
# severity levels per modality, exactly as in the frozen grid
SEV_LEVELS = {"obs_noise": 4, "act_noise": 2, "act_drop": 2, "act_delay": 1, "dropout": 1}


def load_lines(task):
    """Immutable label table -> line dict {(seed,modality,window,agents): [(sev_idx,label)]}."""
    rows = list(csv.DictReader(open(PA / "raw" / "track_b_a2" / f"labels_{task}.csv")))
    lines = defaultdict(list)
    cells = {}
    for r in rows:
        key = (r["initial_seed"], r["modality"], r["window"], r["agents"])
        si, y = int(r["severity_idx"]), int(r["failure"])
        lines[key].append((si, y))
        cells[key + (si,)] = y
    for k in lines:
        lines[k].sort()
    return lines, cells


def truth_edges(lines):
    """True transition edges: adjacent severity pairs with differing labels."""
    edges = []
    for lk, seq in lines.items():
        for (s1, y1), (s2, y2) in zip(seq, seq[1:]):
            if y1 != y2:
                edges.append((lk, s1, s2))
    return edges


def recall(edge_list, queried):
    """Primary: both severity levels of the true adjacent pair queried in-line."""
    qlines = defaultdict(set)
    for (lk, si) in queried:
        qlines[lk].add(si)
    hit = sum(1 for (lk, s1, s2) in edge_list
              if s1 in qlines[lk] and s2 in qlines[lk])
    return hit / max(1, len(edge_list))


# ---------------------------------------------------------------- methods
def order_random(keys, rng):
    k = list(keys)
    rng.shuffle(k)
    return [(x[:-1], x[-1]) for x in k]


def order_stratified(keys, rng):
    by = defaultdict(list)
    for x in keys:
        by[(x[1], x[3])].append(x)
    for v in by.values():
        rng.shuffle(v)
    groups = list(by.values())
    out, i = [], 0
    while len(out) < len(keys):
        placed = False
        for g in groups:
            if i < len(g):
                out.append(g[i])
                placed = True
                if len(out) >= len(keys):
                    break
        if not placed:
            break
        i += 1
    return [(x[:-1], x[-1]) for x in out]


def order_generic(keys, labels_full, K_total, rng, trace=False):
    """Real label-based active learner (ExtraTrees vote entropy). Only queried
    labels are visible — labels_full is the environment, accessed via query()."""
    from sklearn.ensemble import ExtraTreesClassifier

    def feat(x):
        return [hash(x[0]) % 997, list(SEV_LEVELS).index(x[1]), x[2],
                int(x[3].split("|")[0]), len(x[3]), x[4]]
    keys = list(keys)
    rng.shuffle(keys)
    q = keys[:max(8, K_total // 4)]
    qlab = [labels_full[x] for x in q]
    order = [(x[:-1], x[-1]) for x in q]
    while len(q) < K_total:
        if len(set(qlab)) < 2:
            cand = [x for x in keys if x not in q]
            x = rng.choice(cand)
        else:
            clf = ExtraTreesClassifier(n_estimators=40, random_state=rng.randrange(2**31))
            X = np.array([feat(x) for x in q])
            clf.fit(X, qlab)
            cand = [x for x in keys if x not in q]
            if not cand:
                break
            Xc = np.array([feat(x) for x in cand])
            P = clf.predict_proba(Xc)
            ent = -(P * np.log(P + 1e-12)).sum(axis=1)
            x = cand[int(np.argmax(ent))]
        q.append(x)
        qlab.append(labels_full[x])
        order.append((x[:-1], x[-1]))
    return order


def order_structured(lines, keys, K_total, rng):
    """Corrected STRUCTURED_ACTIVE.

    Frozen line order; each unprobed line gets endpoint probes; disagreeing
    endpoints open a candidate interval that is bisected (each query strictly
    shrinks it) until the adjacent flip is localised; round-robin over unresolved
    lines. Uses only pre-query metadata + queried labels.
    """
    line_keys = sorted(lines)
    rng.shuffle(line_keys)                      # frozen per-repetition order
    multi = [lk for lk in line_keys if len(lines[lk]) >= 2]
    single = [lk for lk in line_keys if len(lines[lk]) < 2]
    queried = []
    spent = 0
    unresolved = []                             # (line, lo_idx, hi_idx) over sorted levels
    line_budget = max(2, K_total // 8)
    # pass 1+2 interleaved: round-robin endpoints, then bisection
    while spent < K_total and (multi or unresolved or single):
        progressed = False
        for lk in list(multi):
            if spent >= K_total:
                break
            seq = lines[lk]
            lo, hi = seq[0], seq[-1]
            for x in (lo[0], hi[0]):
                if spent < K_total:
                    queried.append((lk, x))
                    spent += 1
                    progressed = True
            if lo[1] != hi[1]:
                unresolved.append((lk, 0, len(seq) - 1))
            multi.remove(lk)
            if spent >= K_total:
                break
        # bisection round-robin
        for item in list(unresolved):
            if spent >= K_total:
                break
            lk, lo_i, hi_i = item
            seq = lines[lk]
            if hi_i - lo_i <= 1:
                unresolved.remove(item)
                continue
            mid_i = (lo_i + hi_i) // 2
            queried.append((lk, seq[mid_i][0]))
            spent += 1
            progressed = True
            if seq[mid_i][1] == seq[lo_i][1]:
                lo_i = mid_i
            else:
                hi_i = mid_i
            if hi_i - lo_i <= 1:
                unresolved.remove(item)
            else:
                unresolved[unresolved.index(item)] = (lk, lo_i, hi_i)
            if spent - max(2, K_total // 8) * max(0, 1) > K_total:  # safety
                break
        if not progressed:
            # single-severity lines: query them to fill budget (no edge possible)
            for lk in single:
                for x in lines[lk]:
                    if spent >= K_total:
                        break
                    queried.append((lk, x[0]))
                    spent += 1
                if spent >= K_total:
                    break
            break
    return queried


# ---------------------------------------------------------------- positive control
def positive_control():
    """Synthetic pool with the same line/severity geometry and monotone transitions."""
    rng = random.Random(20260922)
    # mirror the real geometry: per "seed", line-type counts as measured
    n_seeds = 16
    line_types = (["obs_noise4"] * 30 + ["act_noise2"] * 15 + ["act_drop2"] * 15
                  + ["single1"] * 45)                     # per seed
    pool = {}
    truth = {}
    trans_frac = 0.30
    for s in range(n_seeds):
        for li, lt in enumerate(line_types):
            levels = {"obs_noise4": 4, "act_noise2": 2, "act_drop2": 2, "single1": 1}[lt]
            has_t = levels >= 2 and rng.random() < trans_frac
            thr = rng.randrange(1, levels) if has_t else None
            base_fail = rng.random() < 0.25
            for si in range(levels):
                if has_t:
                    y = int(si >= thr)
                else:
                    y = int(base_fail)
                pool[(s, li, si)] = y
                truth[(s, li, si)] = y
    lines = defaultdict(list)
    for (s, li, si), y in pool.items():
        lines[(s, li)].append((si, y))
    for k in lines:
        lines[k].sort()
    edges = []
    for lk, seq in lines.items():
        for (s1, y1), (s2, y2) in zip(seq, seq[1:]):
            if y1 != y2:
                edges.append((lk, s1, s2))
    keys = sorted(pool)

    def recall_pc(queried, K):
        q = queried[:K]
        ql = defaultdict(set)
        for lk, si in q:
            ql[lk].add(si)
        hit = sum(1 for (lk, s1, s2) in edges if s1 in ql[lk] and s2 in ql[lk])
        return hit / max(1, len(edges))

    res, traces = {}, {}
    for K in (25, 50, 100, 200):
        rr, ss = [], []
        for rep in range(REPS):
            r = random.Random(50_000 + rep)
            rr.append(recall_pc(order_random(keys, r), K))
            s_order = order_structured(lines, keys, K, random.Random(60_000 + rep))
            ss.append(recall_pc(s_order, K))
            if rep == 0:
                traces[K] = {"random_first10": order_random(keys, r)[:10],
                             "structured_first10": s_order[:10]}
        res[K] = {"random": sum(rr) / len(rr), "structured": sum(ss) / len(ss),
                  "ratio": (sum(ss) / len(ss)) / max(1e-9, sum(rr) / len(rr))}
    ok = res[50]["ratio"] > 1.0 and res[100]["ratio"] > 1.0
    return {"pass": ok, "n_pool": len(pool), "n_lines": len(lines),
            "n_edges": len(edges), "recall": res,
            "gate": "structured beats random at K=50 AND K=100",
            "status": "PASS" if ok else "B_MEASUREMENT_BLOCKER"}


# ---------------------------------------------------------------- real tables
def main() -> int:
    t0 = time.time()
    reg = Registry()
    out = {"positive_control": positive_control(), "tasks": {}}
    print(json.dumps({"positive_control": out["positive_control"]}, indent=1)[:900], flush=True)
    if not out["positive_control"]["pass"]:
        (PA / "metrics" / "a3_track_b.json").write_text(json.dumps(out, indent=1))
        print("B_MEASUREMENT_BLOCKER — corrected acquisition fails its own control")
        return 1

    for task in TASKS:
        lines, cells = load_lines(task)
        keys = sorted(cells)
        edges = truth_edges(lines)
        n_trans_lines = len({lk for lk, _s1, _s2 in edges})
        fail_frac = sum(cells.values()) / len(cells)
        # non-monotone / multi-edge lines
        lab_lines = defaultdict(list)
        for (lk, s1, s2) in edges:
            lab_lines[lk].append((s1, s2))
        out["tasks"][task] = {"n_cells": len(cells), "n_lines": len(lines),
                              "failure_fraction": fail_frac,
                              "n_true_edges": len(edges),
                              "transition_line_fraction": n_trans_lines / len(lines),
                              "acquisition": {}}
        print(f"[{task}] cells={len(cells)} lines={len(lines)} fail={fail_frac:.3f} "
              f"edges={len(edges)} trans_lines={n_trans_lines}", flush=True)
        for method in ("RANDOM", "STRATIFIED_RANDOM", "GENERIC_ACTIVE", "STRUCTURED_ACTIVE"):
            for K in KS:
                rec, traces_saved = [], 0
                for rep in range(REPS):
                    with reg.unit(f"B3_{task}_{method}_{K}_{rep}", "B", task, method) as u:
                        rng = random.Random(70_000 + 1000 * rep + K)
                        if method == "RANDOM":
                            o = order_random(keys, rng)
                        elif method == "STRATIFIED_RANDOM":
                            o = order_stratified(keys, rng)
                        elif method == "GENERIC_ACTIVE":
                            o = order_generic(keys, cells, K, rng)
                        else:
                            o = order_structured(lines, keys, K, rng)
                        oK = o[:K]
                        r = recall(edges, oK)
                        rec.append(r)
                        u.success({"recall": r})
                        if rep == 0 and traces_saved == 0:
                            (OUT / f"trace_{task}_{method}_K{K}_rep0.json").write_text(
                                json.dumps({"order_first_K": [list(a) + [b] for a, b in oK]}))
                            traces_saved = 1
                out["tasks"][task]["acquisition"][f"{method}@{K}"] = {
                    "mean_recall": float(np.mean(rec)), "std": float(np.std(rec))}
                print(f"  {task} {method} K={K}: {np.mean(rec):.4f}", flush=True)
        (OUT / f"acquisition_{task}.json").write_text(
            json.dumps(out["tasks"][task]["acquisition"], indent=1))
    rec2 = reg.reconcile()
    out["registry"] = rec2
    out["wall_seconds"] = round(time.time() - t0, 1)
    (PA / "metrics" / "a3_track_b.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"reconcile ok={rec2['ok']} wall={out['wall_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
