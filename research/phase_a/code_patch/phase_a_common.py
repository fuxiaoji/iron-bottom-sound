"""Phase A shared plumbing: frozen policy loader, env factory, episode runner with
perturbation hooks, and registry helpers.

The actor is reconstructed from the BenchMARL checkpoint rather than driven
through BenchMARL's trainer, because Tracks A/B/C need per-state branching,
rollout cloning and mid-episode perturbation — none of which the trainer exposes.
The reconstruction is validated against the training run's own evaluation series
(see SELF_CHECK in eval_clean.py).

Architecture recovered from the checkpoint: obs -> Linear(256) -> Tanh ->
Linear(256) -> Tanh -> Linear(2*action_dim) -> [mean, log_std]; the deterministic
action is tanh(mean) (MAPPO with use_tanh_normal=True and
evaluation_deterministic_actions=True in the frozen config).
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import torch
from vmas import make_env

REPO = Path(__file__).resolve().parents[3]
PA = REPO / "research" / "phase_a"
TASKS = ("navigation", "balance")
N_AGENTS = {"navigation": 4, "balance": 3}
MAX_STEPS = 100


# ---------------------------------------------------------------- policy
class FrozenActor:
    """Deterministic MAPPO actor reconstructed from a BenchMARL checkpoint."""

    def __init__(self, checkpoint_path: Path):
        d = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        p = {k.split("actor_network_params.", 1)[1]: v
             for k, v in d["loss_agents"].items() if "actor_network_params." in k}
        self.W0 = p["module.0.module.0.mlp.params.0.weight"]
        self.b0 = p["module.0.module.0.mlp.params.0.bias"]
        self.W2 = p["module.0.module.0.mlp.params.2.weight"]
        self.b2 = p["module.0.module.0.mlp.params.2.bias"]
        self.W4 = p["module.0.module.0.mlp.params.4.weight"]
        self.b4 = p["module.0.module.0.mlp.params.4.bias"]
        self.obs_dim = self.W0.shape[1]
        self.action_dim = self.W4.shape[0] // 2
        self.source = str(checkpoint_path)

    @torch.no_grad()
    def mean_action(self, obs: torch.Tensor) -> torch.Tensor:
        h = torch.tanh(obs @ self.W0.T + self.b0)
        h = torch.tanh(h @ self.W2.T + self.b2)
        out = h @ self.W4.T + self.b4
        mean, _log_std = out.chunk(2, dim=-1)
        return torch.tanh(mean)

    @torch.no_grad()
    def act(self, obs_list: list[torch.Tensor]) -> list[torch.Tensor]:
        return [self.mean_action(o) for o in obs_list]


def checkpoint_for(task: str, seed: int, frames: int = 600_000) -> Path:
    """Locate the end-of-training checkpoint for (task, seed). Raises if absent —
    a missing checkpoint is a REJECTED row at the registry level, never a silent
    fallback to a different seed."""
    run_dir = PA / "runs" / f"mappo_{task}_s{seed}"
    cands = sorted(run_dir.rglob(f"checkpoint_{frames}.pt"))
    if not cands:
        cands = sorted(run_dir.rglob("checkpoint_*.pt"),
                       key=lambda p: int(p.stem.split("_")[1]))
    if not cands:
        raise FileNotFoundError(f"no checkpoint under {run_dir}")
    return cands[-1]


# ---------------------------------------------------------------- env
def make_task_env(task: str, num_envs: int, seed: int | None = None):
    env = make_env(scenario=task, num_envs=num_envs, device="cpu",
                   continuous_actions=True, max_steps=MAX_STEPS)
    if seed is not None:
        env.reset(seed=seed)
    return env


def native_success(task: str, info: dict, n_agents: int) -> bool:
    """Pre-registered native success predicate (PRE_REGISTRATION_PHASE_A §4)."""
    if task == "navigation":
        fr = info.get("final_rew")
        if fr is None:
            raise KeyError("navigation info lacks final_rew")
        return bool((torch.as_tensor(fr) > 0).all())
    if task == "balance":
        gr, pr = info.get("ground_rew"), info.get("pos_rew")
        if gr is None or pr is None:
            raise KeyError("balance info lacks ground_rew/pos_rew")
        return bool(((torch.as_tensor(gr) > 0).all()) and ((torch.as_tensor(pr) > 0).all()))
    raise ValueError(task)


# ---------------------------------------------------------------- perturbations
class Perturbation:
    """One configuration of the frozen Track B space.

    modality: 'obs_noise' | 'act_noise' | 'act_drop' | 'act_delay' | 'dropout'
    agents  : indices affected
    t_start, t_end : inclusive window of environment steps
    severity: sigma (noise), probability (drop), or ignored
    """

    def __init__(self, modality, agents, t_start, t_end, severity):
        self.modality = modality
        self.agents = tuple(agents)
        self.t_start = int(t_start)
        self.t_end = int(t_end)
        self.severity = float(severity)

    def key(self):
        return (self.modality, self.agents, self.t_start, self.t_end, self.severity)

    def to_dict(self):
        return {"modality": self.modality, "agents": list(self.agents),
                "t_start": self.t_start, "t_end": self.t_end,
                "severity": self.severity}

    def active(self, t):
        return self.t_start <= t <= self.t_end


def _torch_gen(rng):
    """torch.randn needs a torch.Generator; derive one deterministically from the
    Python RNG so every perturbation stream stays reproducible and disjoint."""
    g = torch.Generator()
    g.manual_seed(rng.randrange(2 ** 31))
    return g


def apply_observation_noise(obs_list, pert, rng):
    out = []
    for i, o in enumerate(obs_list):
        if i in pert.agents:
            out.append(o + torch.randn(o.shape, generator=_torch_gen(rng)) * pert.severity)
        else:
            out.append(o)
    return out


def apply_action_perturbation(actions, pert, rng, memory):
    out = []
    for i, a in enumerate(actions):
        if i not in pert.agents:
            out.append(a)
            continue
        if pert.modality == "act_noise":
            out.append(torch.clamp(
                a + torch.randn(a.shape, generator=_torch_gen(rng)) * pert.severity, -1, 1))
        elif pert.modality == "act_drop":
            keep = (torch.rand(a.shape, generator=_torch_gen(rng)) > pert.severity).float()
            out.append(a * keep)
        elif pert.modality == "act_delay":
            out.append(memory.get(i, a))       # one-step delayed action
        elif pert.modality == "dropout":
            out.append(torch.zeros_like(a))
        else:
            out.append(a)
    return out


# ---------------------------------------------------------------- registry
def write_registry(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_row(path: Path, row: dict, fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)
