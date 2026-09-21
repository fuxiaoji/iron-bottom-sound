"""500 random-action episodes for a task (Track A's NR denominator)."""
import csv, json, random, sys, time
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardened import Registry
from phase_a_common import PA, make_task_env
TASK = sys.argv[1] if len(sys.argv) > 1 else "balance"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 500
reg = Registry(); rows=[]
for e in range(N):
    with reg.unit(f"rand_{TASK}_{e}", "A0", TASK, "random_policy") as u:
        env = make_task_env(TASK, 1, seed=9000+e); env.reset(seed=9000+e)
        tot, steps = 0.0, 0
        while steps < 100:
            obs, rew, dones, infos = env.step(env.get_random_actions())
            tot += float(sum(float(r.sum()) for r in rew)); steps += 1
            if bool(torch.as_tensor(dones).any()): break
        rows.append({"task": TASK, "mode": "random", "episode_seed": 9000+e, "return": tot, "length": steps})
        u.success({"return": tot}, sim_steps=steps)
with open(PA/"raw"/"track_common"/f"random_baseline_{TASK}.csv","w",newline="") as fh:
    w=csv.DictWriter(fh, fieldnames=["task","mode","episode_seed","return","length"]); w.writeheader()
    for r in rows: w.writerow(r)
vals=[r["return"] for r in rows]
(PA/"raw"/"track_common"/f"random_baseline_{TASK}.json").write_text(json.dumps(
    {"task":TASK,"n":len(vals),"mean":sum(vals)/len(vals)}, indent=1))
print(json.dumps({"task":TASK,"n":len(vals),"mean":round(sum(vals)/len(vals),3)}, indent=1))
