"""Phase A.3 Track C — C0 generator feasibility calibration → C1 → C2 → C3.

Frozen per PRE_REGISTRATION_PHASE_A3.md §2: families act_drop / obs_corrupt /
act_delay; one affected agent; windows start at step 40 with length ≤ 8 (locality
cap); ordered settings, first-in-band (yield 10–30 %, LCB > 5 %, errors ≤ 1 %)
wins; dedicated calibration seeds 80 000+; fresh collection seeds 90 000+; no
repair matrix and no attribution outcome during C0. Material-causality semantics
are frozen (balance native; sampling clean ≥ Q50, faulted < Q25, drop ≥ 0.5·IQR).

    .venv_phase_a/bin/python research/phase_a/scripts/a3_track_c.py [--stage C0|C1|C2|C3|all]
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry  # noqa: E402
from phase_a_common import PA, FrozenActor, make_task_env  # noqa: E402

TASKS = ("balance", "sampling")
N_AGENTS = {"balance": 3, "sampling": 3}
MAX_STEPS = 100
WINDOW_START = 40
CAL_SEED = 80_000
EVAL_SEED = 90_000
SETTINGS = {
    "act_drop": [(0.5, 8), (1.0, 8), (1.0, 4), (1.0, 2), (1.0, 1)],
    "obs_corrupt": [(0.3, 8), (0.6, 8), (1.2, 8), (1.2, 4), (1.2, 2), (1.2, 1)],
    "act_delay": [(2, 8), (4, 8), (4, 4)],
}
REPAIR_WINDOWS = (10, 30, 50, 70, 90)     # 20-step slots, as frozen earlier
REPAIR_SLOT_LEN = 20
N_PAIRS = 100
BAND = (0.10, 0.30)
LCB = 0.05
OUT = PA / "raw"
for sub in ("track_c_calibration", "track_c_failures", "track_c_repairs"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)


def sem(task):
    if task == "sampling":
        s = json.loads((PA / "ENVIRONMENT_LOCK.json").read_text())["sampling_semantics"]
        return {"Q25": s["clean_Q25"], "Q50": s["clean_Q50"], "IQR": s["clean_IQR"]}
    return None


def load_actor(task):
    sel = json.loads((PA / "raw" / "track_common" / "checkpoint_selection.json").read_text())
    seed = sel["selection"][task]["median_seed"]
    ck = sorted((PA / "runs" / f"mappo_{task}_s{seed}").rglob("checkpoint_600000.pt"))[-1]
    return FrozenActor(ck)


def batch_episode(env_seed, task, actor, n_envs, fault=None, repair=None):
    """One vectorised episode block.

    fault = (modality, severity, agent, win_start, win_len); repair = (agent, slot)
    suppresses the fault inside REPAIR_WINDOWS[slot] for that agent.
    Returns per-env (return, success, done_step).
    """
    env = make_task_env(task, n_envs, seed=env_seed)
    obs = env.reset(seed=env_seed)
    g = torch.Generator().manual_seed((env_seed * 7919 + 13) % (2 ** 31))
    totals = torch.zeros(n_envs)
    done_step = torch.full((n_envs,), MAX_STEPS, dtype=torch.long)
    alive = torch.ones(n_envs, dtype=torch.bool)
    memory = {}
    steps = 0
    w0 = fault[3] if fault is not None else 0
    wlen = fault[4] if fault is not None else 0
    while steps < MAX_STEPS:
        acts = actor.act(obs)
        if fault is not None:
            modality, sev, agent = fault[0], fault[1], fault[2]
            in_window = WINDOW_START <= steps < WINDOW_START + wlen
            if repair is not None:
                slot = repair[1]
                in_slot = (REPAIR_WINDOWS[slot] <= steps <
                           REPAIR_WINDOWS[slot] + REPAIR_SLOT_LEN)
                if repair[0] == agent and in_slot:
                    in_window = False
            if in_window:
                if modality == "act_drop":
                    keep = (torch.rand(acts[agent].shape, generator=g) > sev).float()
                    acts[agent] = acts[agent] * keep
                elif modality == "obs_corrupt":
                    i = agent
                    obs[i] = obs[i] + torch.randn(obs[i].shape, generator=g) * sev
                    acts = actor.act(obs)
                elif modality == "act_delay":
                    prev = memory.get(agent)
                    if prev is not None:
                        acts[agent] = prev
        for i, a in enumerate(acts):
            memory[i] = a.detach().clone()
        obs, rew, dones, infos = env.step(acts)
        for i, r in enumerate(rew):
            totals[i] += float(r.sum())
        d = torch.as_tensor(dones).flatten()
        for i in range(n_envs):
            if alive[i] and bool(d[i]):
                alive[i] = False
                done_step[i] = steps + 1
        newly = ~alive
        steps += 1
    if task == "balance":
        og = torch.as_tensor(env.scenario.on_the_ground).flatten() > 0
        success = (~og).tolist()
    else:
        success = [None] * n_envs
    return totals.tolist(), success, done_step.tolist()


def valid_failure(task, clean_ret, clean_ok, fault_ret, fault_ok, s):
    if task == "balance":
        return bool(clean_ok) and not bool(fault_ok)
    return bool(clean_ret >= s["Q50"] and fault_ret < s["Q25"]
                and clean_ret - fault_ret >= 0.5 * s["IQR"])


def lcb_wilson(p, n, z=1.96):
    if n == 0:
        return 0.0
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half


# ---------------------------------------------------------------- C0
def run_c0(reg):
    out = {"settings_order": {k: v for k, v in SETTINGS.items()},
           "band": BAND, "lcb": LCB, "n_pairs": N_PAIRS,
           "calibration_seeds": f"{CAL_SEED}+ (dedicated, never reused)",
           "tasks": {}}
    for task in TASKS:
        actor = load_actor(task)
        s = sem(task)
        n_agents = N_AGENTS[task]
        fam = {}
        for family, settings in SETTINGS.items():
            chosen = None
            rows = []
            for set_idx, (strength, wlen) in enumerate(settings):
                if chosen:
                    break
                if family == "act_delay":
                    fault_spec = ("act_delay", strength, None, WINDOW_START, wlen)
                else:
                    fault_spec = (family, strength, None, WINDOW_START, wlen)
                per_agent = math.ceil(N_PAIRS / n_agents)
                t0 = time.time()
                clean_rets, fault_rets, clean_oks, fault_oks, errs = [], [], [], [], 0
                for a in range(n_agents):
                    env_seed = CAL_SEED + 1000 * set_idx + 10 * a
                    fs = (fault_spec[0], fault_spec[1], a, fault_spec[3], fault_spec[4])
                    try:
                        cr, cok, _d1 = batch_episode(env_seed, task, actor, per_agent)
                        fr, fok, _d2 = batch_episode(env_seed, task, actor, per_agent,
                                                     fault=fs)
                    except Exception as exc:
                        errs += per_agent
                        rows.append({"setting": (strength, wlen), "agent": a,
                                     "status": "ERROR_WITH_TRACE",
                                     "error": f"{type(exc).__name__}: {exc}"})
                        continue
                    for i in range(per_agent):
                        ok = valid_failure(task, cr[i], cok[i], fr[i], fok[i], s)
                        clean_rets.append(cr[i]); fault_rets.append(fr[i])
                        clean_oks.append(cok[i]); fault_oks.append(fok[i])
                        rows.append({"setting": (strength, wlen), "agent": a,
                                     "env": i, "clean_return": cr[i],
                                     "fault_return": fr[i], "valid": int(ok),
                                     "status": "SUCCESS"})
                n = len(clean_rets)
                yield_n = sum(valid_failure(task, c, co, f, fo, s)
                              for c, co, f, fo in zip(clean_rets, clean_oks,
                                                      fault_rets, fault_oks))
                y = yield_n / max(1, n)
                # sanity diagnostic: the fault MUST shift the return distribution,
                # otherwise it is not being applied (A3-C2 check)
                mc = sum(clean_rets) / max(1, n)
                mf = sum(fault_rets) / max(1, n)
                mean_shift = mf - mc
                low = lcb_wilson(y, n)
                in_band = (n >= N_PAIRS and BAND[0] <= y <= BAND[1] and low > LCB)
                print(f"  [{task}] {family} strength={strength} w={wlen}: "
                      f"n={n} yield={y:.3f} lcb={low:.3f} in_band={in_band} "
                      f"mean_clean={mc:.1f} mean_fault={mf:.1f} shift={mean_shift:+.1f} "
                      f"({time.time()-t0:.0f}s)", flush=True)
                if in_band and chosen is None:
                    chosen = {"family": family, "strength": strength, "window": wlen,
                              "yield": y, "lcb": low, "n_pairs": n}
                rows.append({"setting": (strength, wlen), "summary": True,
                             "n_pairs": n, "yield": y, "lcb": low,
                             "mean_clean": mc, "mean_fault": mf,
                             "in_band": in_band, "status": "SUCCESS"})
            # per-episode rows and summary rows have different fields; write with
            # a fixed superset schema and extrasaction="ignore" (A3-C1 fix)
            sup = ["setting", "agent", "env", "clean_return", "fault_return",
                   "valid", "status", "error", "summary", "n_pairs", "yield",
                   "lcb", "in_band"]
            with open(OUT / "track_c_calibration" / f"{task}_{family}.csv", "w",
                      newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=sup, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    if "setting" in r and not isinstance(r["setting"], str):
                        r = dict(r); r["setting"] = json.dumps(r["setting"])
                    w.writerow(r)
            fam[family] = {"chosen": chosen,
                           "tried": len(rows) and len({str(r.get("setting"))
                                                       for r in rows})}
        n_pass = sum(1 for f in fam.values() if f["chosen"])
        verdict = ("PASS" if n_pass >= 2 else
                   "C_GENERATOR_NARROW" if n_pass == 1 else
                   "C_GENERATOR_FEASIBILITY_FAIL")
        out["tasks"][task] = {"families": fam, "n_families_passed": n_pass,
                              "C0_verdict": verdict}
        print(f"[{task}] C0 = {verdict} ({n_pass} families in band)", flush=True)
    (PA / "metrics" / "a3_track_c0.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main() -> int:
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "C0"
    reg = Registry()
    if stage in ("C0", "all"):
        run_c0(reg)
    rec = reg.reconcile()
    print(json.dumps(rec["totals"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
