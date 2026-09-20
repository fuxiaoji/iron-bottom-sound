"""Re-run G1/G2 with F10-fixed intents (their json entries predate the fix)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(REPO := Path(__file__).resolve().parents[4] / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repair.gold_cases import CASES, evaluate_case, _state_for, reach_move  # noqa
from iron_bottom_sound.models import Side  # noqa

OUT = Path(__file__).resolve().parents[2] / "metrics" / "gold_cases.json"
d = json.loads(OUT.read_text())
for case_name, builder, scenarios in CASES:
    if case_name not in ("G1_BROADSIDE_UNMASKING", "G2_CROSSING_THE_T"):
        continue
    built = None
    for scenario in scenarios:
        for seed in range(1, 9):
            for turn in (2, 3):
                eng, st = reach_move(scenario, seed, turn)
                if st is None:
                    continue
                try:
                    built = builder(eng, st, Side.ALLIES)
                except Exception:
                    built = None
                if built and len(built["candidates"]) >= 2:
                    ident = len(set(built["candidates"].values())) == 1
                    if ident:
                        print(f"{case_name}: candidates identical, skipping seed", flush=True)
                        continue
                    st_cached = _state_for(case_name, scenario, seed, Side.ALLIES.value, turn)
                    res = evaluate_case(case_name, built, scenario, seed, Side.ALLIES.value, turn)
                    separated = None
                    if built["good"] and built["good"] in res["e0"] and built["bad"] in res["e0"]:
                        g = res["e0"][built["good"]].get("T2")
                        b = res["e0"][built["bad"]].get("T2")
                        if g is not None and b is not None:
                            separated = (g - b) >= 0.05
                    d["cases"][case_name] = {
                        "scenario": scenario, "seed": seed, "turn": turn,
                        "side": Side.ALLIES.value,
                        "candidates": list(built["candidates"]), **res,
                        "tactical_separation_T2": separated}
                    print(f"{case_name}: {scenario} s{seed} t{turn} sep={separated}", flush=True)
                    break
            if built and len(built["candidates"]) >= 2:
                break
        if built and len(built["candidates"]) >= 2:
            break
n_sep = sum(1 for c in d["cases"].values() if c.get("tactical_separation_T2"))
d["gate"] = {"built": 5, "separated": n_sep,
             "required": ">=4 of 5 with clear separation",
             "verdict": "PASS" if n_sep >= 4 else "GOLD_EVALUATOR_GATE=FAIL"}
OUT.write_text(json.dumps(d, indent=1))
print(json.dumps(d["gate"]))
