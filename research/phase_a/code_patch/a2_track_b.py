"""Phase A.2 §2 — Track B valid rerun.

Universe = (initial seed) x (original perturbation grid), M = ceil(2500/G) clipped
to [12,24] with G the original grid size; the first M deterministic seeds of a
frozen list are used. Boundary = adjacent-severity label change inside a fixed
(seed, agent/subset, time-window, modality) severity line. Primary recall =
fraction of true transition edges localised to within one severity interval.
GENERIC_ACTIVE is a real label-based ExtraTrees ensemble; STRUCTURED_ACTIVE does
severity-line localisation. K <= 10% of the universe, 30 acquisition repetitions.

    .venv_phase_a/bin/python research/phase_a/scripts/a2_track_b.py [--labels-only]
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry  # noqa: E402
from phase_a_common import PA, FrozenActor, Perturbation, make_task_env  # noqa: E402
from track_b import MODALITIES, WINDOWS, WIN_LEN, load_actor, run_perturbed, sampling_q25  # noqa: E402

TASKS = ("balance", "sampling")
KS = (25, 50, 100, 200)
REPS = 30
SEED_FIRST = 60_000
OUT = PA / "raw" / "track_b_a2"
OUT.mkdir(parents=True, exist_ok=True)
N_AGENTS = {"balance": 3, "sampling": 3}


def base_grid(n_agents):
    """The original perturbation grid G (kept exactly as in Phase A)."""
    grid = []
    for modality, severities in MODALITIES.items():
        for si, sev in enumerate(severities):
            for w in WINDOWS:
                for a in range(n_agents):
                    grid.append((modality, si, w, (a,)))
                if modality in ("dropout", "obs_noise"):
                    import itertools
                    for a, b in itertools.combinations(range(n_agents), 2):
                        grid.append((modality, si, w, (a, b)))
    grid.sort()
    return grid


def severity_levels(modality):
    return len(MODALITIES[modality])


def main() -> int:
    t0 = time.time()
    labels_only = "--labels-only" in sys.argv
    reg = Registry()
    out = {"universe_rule": "M = ceil(2500/G) clipped [12,24]; first M frozen seeds",
           "K": list(KS), "reps": REPS, "tasks": {}}
    for task in TASKS:
        n_agents = N_AGENTS[task]
        grid = base_grid(n_agents)
        G = len(grid)
        M = max(12, min(24, math.ceil(2500 / G)))
        seeds = [SEED_FIRST + i for i in range(M)]
        universe = [(s, g) for s in seeds for g in grid]
        q25 = sampling_q25() if task == "sampling" else None
        actor, mseed = load_actor(task)
        cache = OUT / f"labels_{task}.csv"
        if cache.exists():
            rows = list(csv.DictReader(open(cache)))
            print(f"[{task}] loaded {len(rows)} cached labels", flush=True)
        else:
            rows = []
            for idx, (seed, g) in enumerate(universe):
                modality, si, w, agents = g
                sev = MODALITIES[modality][si]
                pert = Perturbation(modality, agents, w, w + WIN_LEN, sev)
                with reg.unit(f"B2_{task}_{idx}", "B", task, "universe_label") as u:
                    ret, fail, steps, _ent = run_perturbed(actor, task, pert, seed, q25, n_agents)
                    rows.append({"task": task, "initial_seed": seed, "modality": modality,
                                 "severity_idx": si, "window": w, "agents": "|".join(map(str, agents)),
                                 "severity": sev, "return": ret, "failure": int(fail),
                                 "status": "SUCCESS"})
                    u.success({"failure": int(fail)}, sim_queries=1, sim_steps=steps)
                if (idx + 1) % 200 == 0:
                    print(f"  {task} labels {idx+1}/{len(universe)} {time.time()-t0:.0f}s", flush=True)
            with open(cache, "w", newline="") as fh:
                w2 = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w2.writeheader()
                for r in rows:
                    w2.writerow(r)
        lab = {}
        for r in rows:
            key = (int(r["initial_seed"]), r["modality"], r["window"],
                   tuple(int(x) for x in r["agents"].split("|")), int(r["severity_idx"]))
            lab[key] = int(r["failure"])
        fail_frac = sum(lab.values()) / max(1, len(lab))
        # severity lines and true transitions
        lines = defaultdict(list)
        for key in lab:
            seed, modality, w, agents, si = key
            lines[(seed, modality, w, agents)].append((si, lab[key]))
        true_edges, multi, nonmono = [], 0, 0
        for lk, seq in lines.items():
            seq.sort()
            levels = [si for si, _ in seq]
            labels = [y for _, y in seq]
            edges = [(levels[i], levels[i + 1]) for i in range(len(seq) - 1)
                     if labels[i] != labels[i + 1]]
            if edges:
                true_edges += [(lk, e) for e in edges]
                if len(edges) > 1:
                    multi += 1
                flips = sum(1 for i in range(len(labels) - 1)
                            if labels[i] != labels[i + 1] and i >= 1
                            and labels[i - 1] == labels[i + 1])
                if flips:
                    nonmono += 1
        n_lines = len(lines)
        out["tasks"][task] = {"G": G, "M": M, "universe": len(universe), "median_seed": mseed,
                              "failure_fraction": fail_frac, "n_lines": n_lines,
                              "transition_line_fraction": len({lk for lk, _ in true_edges}) / max(1, n_lines),
                              "multi_transition_line_fraction": multi / max(1, n_lines),
                              "nonmonotone_line_fraction": nonmono / max(1, n_lines),
                              "n_true_edges": len(true_edges)}
        print(f"[{task}] G={G} M={M} universe={len(universe)} fail={fail_frac:.3f} "
              f"lines={n_lines} edges={len(true_edges)}", flush=True)
        json.dump({"true_edges": [[list(map(str, k)), list(e)] for k, e in true_edges],
                   "n_lines": n_lines, "failure_fraction": fail_frac},
                  open(OUT / f"truth_{task}.json", "w"), default=str)
        if labels_only:
            continue
        # ---------------- acquisition comparisons
        keys = list(lab)
        feat = {k: [k[0] % 97, list(MODALITIES).index(k[1]), k[2], k[3][0],
                    len(k[3]), k[4], MODALITIES[k[1]][k[4]]] for k in keys}
        edges_by_line = defaultdict(list)
        for lk, e in true_edges:
            edges_by_line[lk].append(e)
        results = {}
        from sklearn.ensemble import ExtraTreesClassifier
        for method in ("RANDOM", "STRATIFIED_RANDOM", "GENERIC_ACTIVE", "STRUCTURED_ACTIVE"):
            for K in KS:
                hits, ratios = [], []
                for rep in range(REPS):
                    rng = random.Random(1000 * rep + K)
                    if method == "RANDOM":
                        order = keys[:]
                        rng.shuffle(order)
                        q = order[:K]
                    elif method == "STRATIFIED_RANDOM":
                        by = defaultdict(list)
                        for k in keys:
                            by[(k[1], k[3])].append(k)
                        for v in by.values():
                            rng.shuffle(v)
                        q, i = [], 0
                        while len(q) < K:
                            prog = False
                            for v in by.values():
                                if i < len(v) and len(q) < K:
                                    q.append(v[i]); prog = True
                            i += 1
                            if not prog:
                                break
                    elif method == "GENERIC_ACTIVE":
                        pool = keys[:]
                        rng.shuffle(pool)
                        q = pool[:max(8, K // 4)]
                        while len(q) < K:
                            X = np.array([feat[k] for k in q])
                            y = np.array([lab[k] for k in q])
                            if len(set(y.tolist())) < 2:
                                cand = [k for k in keys if k not in q]
                                q.append(rng.choice(cand)); continue
                            clf = ExtraTreesClassifier(n_estimators=40, random_state=rep)
                            clf.fit(X, y)
                            cand = [k for k in keys if k not in q]
                            Xc = np.array([feat[k] for k in cand])
                            P = clf.predict_proba(Xc)
                            ent = -(P * np.log(P + 1e-12)).sum(axis=1)
                            q.append(cand[int(np.argmax(ent))])
                    else:  # STRUCTURED_ACTIVE: severity-line localisation
                        line_keys = defaultdict(list)
                        for k in keys:
                            line_keys[(k[0], k[1], k[2], k[3])].append(k)
                        order = []
                        lk_list = list(line_keys)
                        rng.shuffle(lk_list)
                        for lk in lk_list:
                            ks = sorted(line_keys[lk], key=lambda k: k[4])
                            order += [ks[len(ks) // 2], ks[0], ks[-1]]
                        seen = set(order)
                        order += [k for k in keys if k not in seen]
                        q = order[:K]
                    qs = set(q)
                    found = 0
                    for lk, (si_lo, si_hi) in true_edges:
                        base = [k for k in qs if k[:4] == lk[:4] or
                                (k[0], k[1], k[2], k[3]) == lk]
                        levels_q = {k[4] for k in base if k[0] == lk[0] and k[1] == lk[1]
                                    and k[2] == lk[2] and k[3] == lk[3]}
                        if any(abs(si - si_lo) <= 1 or abs(si - si_hi) <= 1 for si in levels_q):
                            found += 1
                    hits.append(found / max(1, len(true_edges)))
                results[f"{method}@{K}"] = {"mean_recall": float(np.mean(hits)),
                                            "std": float(np.std(hits)), "n": len(hits),
                                            "raw": hits}
                print(f"  {task} {method} K={K}: recall={np.mean(hits):.4f}", flush=True)
        out["tasks"][task]["acquisition"] = {k: {kk: vv for kk, vv in v.items() if kk != "raw"}
                                             for k, v in results.items()}
        json.dump(results, open(OUT / f"acquisition_{task}.json", "w"), default=str)
        rec = reg.reconcile()
        print(f"[{task}] registry ok={rec['ok']}", flush=True)
    out["wall_seconds"] = round(time.time() - t0, 1)
    out["registry"] = reg.reconcile()
    (PA / "metrics" / "a2_track_b.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote metrics/a2_track_b.json ({out['wall_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
