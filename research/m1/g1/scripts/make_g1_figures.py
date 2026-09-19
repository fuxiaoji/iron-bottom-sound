"""G1 figures: value divergence, regret distributions, confidence-regret relation."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "research" / "m1" / "g1"
FIG = OUT / "figures"; FIG.mkdir(exist_ok=True)

lines=[json.loads(l) for l in (OUT/"IBS_ALIAS_PAIRS.jsonl").open()]
main=[r for r in lines if not r["is_control_b"]]
ctl=[r for r in lines if r["is_control_b"]]
ev=[r for r in main if r.get("regret") and r["n_candidates_shared"]>=2
    and r["public_obs_equal"] and r["legal_actions_equal"] and r["own_sealed_equal"]]
evc=[r for r in ctl if r.get("regret") and r["n_candidates_shared"]>=2]

def divergence(r,key):
    ds=[abs(x.get(f"{key}_mean")-y.get(f"{key}_mean")) for x,y in zip(r["Q"]["A"],r["Q"]["B"])
        if x.get(f"{key}_mean") is not None and y.get(f"{key}_mean") is not None]
    return max(ds) if ds else 0.0

# Fig 1: value divergence histogram (outcome)
fig,ax=plt.subplots(figsize=(6,3.6))
ax.hist([divergence(r,"outcome") for r in ev], bins=16, color="#3b7dd8", edgecolor="white")
ax.set_xlabel(r"max$_a$ |Q$_A$(a) − Q$_B$(a)|  (outcome)")
ax.set_ylabel("pairs")
ax.set_title("G1: hidden commitment changes VALUES (120 evaluable pairs)")
fig.tight_layout(); fig.savefig(FIG/"G1_value_divergence.png", dpi=150); plt.close(fig)

# Fig 2: normalized regret, main vs control (damage), no confidence filter
fig,ax=plt.subplots(figsize=(6.4,3.8))
ax.hist([r["regret_damage_diff"]["normalized_regret"] for r in ev if r.get("regret_damage_diff")],
        bins=16, alpha=.75, color="#3b7dd8", edgecolor="white", label="main pairs (n=120)")
ax.hist([r["regret_damage_diff"]["normalized_regret"] for r in evc if r.get("regret_damage_diff")],
        bins=16, alpha=.65, color="#e0803a", edgecolor="white", label="control B distant (n=44)")
ax.axvline(0.10, color="crimson", ls="--", lw=1, label="gate 0.10")
ax.set_xlabel("normalized shared-action regret (damage_diff, no CI filter)")
ax.set_ylabel("pairs"); ax.set_title("G1: decision aliasing regret, pilot (5 replicates)")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG/"G1_regret_distribution.png", dpi=150); plt.close(fig)

# Fig 3: confidence vs regret anti-correlation
fig,ax=plt.subplots(figsize=(6,3.8))
xs=[r["regret"]["normalized_regret"] if r.get("regret") else 0 for r in ev]
ys=[max(r["regret"]["signal_A"], r["regret"]["signal_B"]) if r.get("regret") else 0 for r in ev]
conf=[r["regret"]["q_ranking_confident"] if r.get("regret") else False for r in ev]
ax.scatter([x for x,c in zip(xs,conf) if not c], [y for y,c in zip(ys,conf) if not c],
           s=14, alpha=.6, color="#999", label="ranking not confident")
ax.scatter([x for x,c in zip(xs,conf) if c], [y for y,c in zip(ys,conf) if c],
           s=26, color="#2e8b57", label="ranking confident")
ax.set_xlabel("normalized shared-action regret (outcome)")
ax.set_ylabel("max branch ranking signal")
ax.set_title("G1: confident rankings cluster at ~0 regret")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG/"G1_confidence_vs_regret.png", dpi=150); plt.close(fig)
print("figures written")
