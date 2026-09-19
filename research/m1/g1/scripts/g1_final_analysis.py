"""Final G1 gate analysis on the 15-replicate power-extension results.

Gate (task-pre-declared, unchanged):
  >=25 nontrivial valid pairs; >=2 scenarios; all pairs naturally reachable;
  public/legal/own identical; hidden commitment the only difference;
  >=20% of valid pairs with normalized shared-action regret >= 0.10;
  >=5 strong manually auditable cases; controls clearly lower.

Valid-for-primary = evaluable AND q_ranking_confident AND control-A exact-0.
"""
import json, statistics, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research" / "m1" / "g1" / "scripts"))
sys.path.insert(0, str(REPO / "backend" / "src"))
import g1_lab as L
from g1_driver import compute_regret

def main():
    lines=[json.loads(l) for l in (L.OUT/"IBS_ALIAS_PAIRS.jsonl").open()]
    p15=json.loads((L.OUT/"g1_power15.json").read_text())
    rows=[]
    for r in lines:
        res=p15.get(r["pair_id"])
        if res is None:
            continue
        merged=dict(r)
        merged["Q"]=res["Q"]; merged["n_candidates_shared"]=res["n_candidates_shared"]
        merged["control_a_max_diff"]=res["control_a_max_diff"]
        reg=compute_regret(res["Q"]["A"],res["Q"]["B"],"outcome")
        regd=compute_regret(res["Q"]["A"],res["Q"]["B"],"damage_diff")
        merged["regret"]=reg; merged["regret_damage_diff"]=regd
        rows.append(merged)
    main=[r for r in rows if not r["is_control_b"]]
    ctl=[r for r in rows if r["is_control_b"]]
    def ok(r):
        cad = r.get("control_a_max_diff")
        return (r["public_obs_equal"] and r["legal_actions_equal"]
                and r["own_sealed_equal"]
                and cad is not None and cad < 1e-9)  # NB: 0.0 is a PASS, not missing
    for key,attr in (("outcome","regret"),("damage_diff","regret_damage_diff")):
        valid=[r for r in main if ok(r) and r[attr] and r[attr]["q_ranking_confident"]]
        regs=[r[attr]["normalized_regret"] for r in valid]
        n10=sum(1 for x in regs if x>=0.10)
        print(f"\n[{key}] valid(confident) pairs: {len(valid)} "
              f"(S-03: {sum(1 for r in valid if r['scenario']=='IBS-S-03')}, "
              f"S-01: {sum(1 for r in valid if r['scenario']=='IBS-S-01')})")
        if regs:
            print(f"  >=0.10: {n10}/{len(regs)} ({100*n10/len(regs):.0f}%) | "
                  f"median={statistics.median(regs):.4f} max={max(regs):.4f}")
        # nontrivial = argmax differs OR R>0
        nontriv=[r for r in valid if r[attr] and (r[attr]["argmax_differs"] or r[attr]["R"]>1e-9)]
        print(f"  nontrivial: {len(nontriv)}")
    # controls at 15 reps
    for key,attr in (("outcome","regret"),("damage_diff","regret_damage_diff")):
        cr=[r[attr]["normalized_regret"] for r in ctl if ok(r) and r[attr] and r[attr]["q_ranking_confident"]]
        print(f"[control-B confident @15reps, {key}]: n={len(cr)} "
              f"median={statistics.median(cr) if cr else None} max={max(cr) if cr else None}")
    # save merged analysis
    (L.OUT/"g1_analysis15.json").write_text(json.dumps(rows, ensure_ascii=False))
    print("\nwrote g1_analysis15.json")

if __name__=="__main__":
    main()
