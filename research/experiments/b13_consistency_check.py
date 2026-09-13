"""B13 data-consistency auto-check.

Verifies that the b13 result files under research/results/b13/ tell one
consistent story, with canonical_results.json as the source of truth
(per provenance.json, which resolved the 2026-09 mean-vs-best-plan
conflict between results.json and report.md).

Checks (hard FAIL on any mismatch):
  1. canonical_results.json exists, parses, and has the required blocks.
  2. cells.csv agrees with canonical_results.json (per geometry: n,
     engine_mean_diff, engine_positive_frac, engine_class, model value,
     model_class, sign_agree).
  3. report.md numbers agree with canonical_results.json (per-geometry
     engine/model values, classes, strict/lower-bound marks, all four
     gates, overall verdict, generation timestamp).
  4. model_predictions.json agrees with canonical["model_predictions"].
  5. games.csv shape agrees with canonical["_meta"] (total rows and
     seeds per (policy, geometry) cell).
  6. Every *.json parses; every expected file is present.

Informational only (not failing): results.json vs canonical -- results.json
is marked SUPERSEDED in provenance.json, so a mismatch there is documented.

Output: one PASS/FAIL line per check on stdout, a final verdict line, and
exit code 0 (all pass) or 1 (any failure).
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
B13 = Path(os.environ.get("B13_DIR", REPO / "research" / "results" / "b13"))

EXPECTED_FILES = ("canonical_results.json", "cells.csv", "report.md",
                  "games.csv", "model_predictions.json", "results.json",
                  "provenance.json")

FLOAT_TOL = 5e-4          # report.md prints 3-4 decimals
GEOMETRIES = ("head_on", "parallel", "crossing")

checks: list[tuple[str, bool, str]] = []  # (name, ok, detail)


def check(name: str, ok: bool, detail: str = "") -> bool:
    checks.append((name, bool(ok), detail))
    return bool(ok)


def close(a: float, b: float, tol: float = FLOAT_TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def _load_json(path: Path):
    """json.load with a None sentinel on missing/unparseable files."""
    try:
        return json.load(open(path))
    except Exception:  # noqa: BLE001
        return None


def parse_num(s: str) -> float:
    return float(s.replace("+", "").strip())


def main() -> int:
    # ---- 0. inventory -----------------------------------------------------
    for fname in EXPECTED_FILES:
        p = B13 / fname
        check(f"file:{fname}", p.is_file(),
              "present" if p.is_file() else "MISSING")
    json_files = sorted(B13.glob("*.json"))
    for p in json_files:
        try:
            json.load(open(p))
            check(f"json-parses:{p.name}", True)
        except Exception as e:  # noqa: BLE001
            check(f"json-parses:{p.name}", False, f"parse error: {e}")
    for p in sorted(B13.glob("*.csv")):
        try:
            rows = list(csv.reader(open(p)))
            check(f"csv-parses:{p.name}", len(rows) > 1, f"{len(rows) - 1} rows")
        except Exception as e:  # noqa: BLE001
            check(f"csv-parses:{p.name}", False, f"parse error: {e}")
    unexpected = sorted(p.name for p in B13.iterdir()
                        if p.suffix not in (".json", ".csv", ".md", ".png")
                        and p.name not in EXPECTED_FILES)
    if unexpected:
        check("inventory:no-unexpected-files", False,
              f"unexpected files: {unexpected}")
    else:
        check("inventory:no-unexpected-files", True)

    # ---- 1. canonical exists and has the required blocks -------------------
    canon_path = B13 / "canonical_results.json"
    canon = _load_json(canon_path)
    if not canon_path.is_file() or not isinstance(canon, dict):
        print("FAIL: canonical_results.json missing or unparseable -- "
              "nothing to check against")
        return _verdict()
    for key in ("_meta", "model_predictions", "engine_results", "cells",
                "gates", "overall"):
        check(f"canonical:block:{key}", key in canon,
              "ok" if key in canon else "MISSING BLOCK")
    if not all(ok for name, ok, _ in checks if name.startswith("canonical:")):
        return _verdict()

    canon_cells = {c["geometry"]: c for c in canon["cells"]}

    # ---- 2. cells.csv vs canonical ----------------------------------------
    try:
        with (B13 / "cells.csv").open(newline="", encoding="utf-8") as fh:
            csv_cells = {r["geometry"]: r for r in csv.DictReader(fh)}
    except Exception:  # noqa: BLE001
        csv_cells = None
    if csv_cells is None:
        for g in GEOMETRIES:
            for field in ("n", "engine_mean_diff", "positive_frac",
                          "engine_class", "model_value", "model_class",
                          "sign_agree"):
                check(f"cells:{g}:{field}", False, "cells.csv unparseable")
    else:
        check("cells:geometry-set", set(csv_cells) == set(canon_cells),
              f"csv={sorted(csv_cells)} canonical={sorted(canon_cells)}")
        for g in GEOMETRIES:
            if g not in csv_cells or g not in canon_cells:
                continue
            row, cc = csv_cells[g], canon_cells[g]
            check(f"cells:{g}:n", close(row["n"], cc["engine_n"]),
                  f"csv n={row['n']} vs canonical engine_n={cc['engine_n']}")
            check(f"cells:{g}:engine_mean_diff",
                  close(row["engine_mean_diff"], cc["engine_mean_diff"]),
                  f"csv {row['engine_mean_diff']} vs canonical {cc['engine_mean_diff']}")
            check(f"cells:{g}:positive_frac",
                  close(row["engine_positive_frac"], cc["engine_positive_frac"]),
                  f"csv {row['engine_positive_frac']} vs canonical {cc['engine_positive_frac']}")
            check(f"cells:{g}:engine_class", row["engine_class"] == cc["engine_class"],
                  f"csv {row['engine_class']} vs canonical {cc['engine_class']}")
            check(f"cells:{g}:model_value",
                  close(row["model_value_vs_straight"], cc["model_best_payoff"]),
                  f"csv model_value_vs_straight={row['model_value_vs_straight']} "
                  f"vs canonical model_best_payoff={cc['model_best_payoff']}")
            check(f"cells:{g}:model_class", row["model_class"] == cc["model_class"],
                  f"csv {row['model_class']} vs canonical {cc['model_class']}")
            check(f"cells:{g}:sign_agree",
                  close(row["sign_agree"], cc["sign_agree_strict"], 0.5),
                  f"csv {row['sign_agree']} vs canonical {cc['sign_agree_strict']}")

    # ---- 3. report.md vs canonical -----------------------------------------
    report = (B13 / "report.md").read_text(encoding="utf-8")
    m = re.search(r"Generated:\s*(\S+)", report)
    check("report:generated", bool(m) and m.group(1) == canon["_meta"]["generated"],
          f"report '{m.group(1) if m else None}' vs canonical "
          f"'{canon['_meta']['generated']}'")
    for g in GEOMETRIES:
        cc, er = canon_cells[g], canon["engine_results"][g]
        m = re.search(rf"^- {g}: engine ([+-][\d.]+) \((\d+)% pos\) "
                      rf"\| model best ([+-][\d.]+) \((\w+)\) "
                      rf"\| strict sign ([✓✗]) \| lower bound ([✓✗])",
                      report, re.MULTILINE)
        if not check(f"report:{g}:line", bool(m),
                     "matched" if m else "pattern not found"):
            continue
        eng, pos, mod, cls, strict, lower = m.groups()
        check(f"report:{g}:engine", close(eng, er["mean_diff"]),
              f"report {eng} vs canonical {er['mean_diff']}")
        check(f"report:{g}:pos_pct", int(pos) == round(100 * er["positive_frac"]),
              f"report {pos}% vs canonical {er['positive_frac']}")
        check(f"report:{g}:model", close(mod, cc["model_best_payoff"]),
              f"report {mod} vs canonical {cc['model_best_payoff']}")
        check(f"report:{g}:class", cls == cc["model_class"],
              f"report {cls} vs canonical {cc['model_class']}")
        check(f"report:{g}:strict_mark",
              (strict == "✓") == bool(cc["sign_agree_strict"]),
              f"report '{strict}' vs sign_agree_strict={cc['sign_agree_strict']}")
        check(f"report:{g}:lower_mark",
              (lower == "✓") == bool(cc["sign_agree_lower_bound"]),
              f"report '{lower}' vs sign_agree_lower_bound={cc['sign_agree_lower_bound']}")
    gates = canon["gates"]
    for label, key, field in (("sign strict", "sign_agreement_strict", "pct"),
                              ("sign lower bound", "sign_agreement_lower_bound", "pct"),
                              ("regime", "regime_agreement", "pct")):
        m = re.search(rf"{label}: (\d+)% \(?(PASS|FAIL)\)?", report)
        want = gates[key]
        if not check(f"report:gate:{key}:pct", bool(m),
                     "matched" if m else "pattern not found"):
            continue
        ok = (int(m.group(1)) == want[field]
              and m.group(2) == ("PASS" if want["pass"] else "FAIL"))
        check(f"report:gate:{key}:pass", ok,
              f"report '{m.group(0)}' vs canonical {want}")
    m = re.search(r"rank ρ: ([\d.]+) \((PASS|FAIL)\)", report)
    want = gates["rank_correlation"]
    if check("report:gate:rank_correlation:pct", bool(m),
             "matched" if m else "pattern not found"):
        ok = (close(m.group(1), want["rho"])
              and m.group(2) == ("PASS" if want["pass"] else "FAIL"))
        check("report:gate:rank_correlation:pass", ok,
              f"report '{m.group(0)}' vs canonical {want}")
    m = re.search(r"Overall: \*\*(\w+)\*\*", report)
    check("report:overall", bool(m) and m.group(1) == canon["overall"],
          f"report '{m.group(1) if m else None}' vs canonical '{canon['overall']}'")

    # ---- 4. model_predictions.json vs canonical ----------------------------
    mp = _load_json(B13 / "model_predictions.json")
    if mp is None:
        for g in GEOMETRIES:
            for field in ("model_best_vs_straight", "model_sign",
                          "model_class"):
                check(f"model_predictions:{g}:{field}", False,
                      "file missing or unparseable")
    else:
        for g in GEOMETRIES:
            want = canon["model_predictions"].get(g, {})
            got = mp.get(g, {})
            for field in ("model_best_vs_straight", "model_sign",
                          "model_class"):
                check(f"model_predictions:{g}:{field}",
                      got.get(field) == want.get(field),
                      f"file {got.get(field)!r} vs canonical {want.get(field)!r}")

    # ---- 5. games.csv shape vs canonical _meta -----------------------------
    try:
        with (B13 / "games.csv").open(newline="", encoding="utf-8") as fh:
            games = list(csv.DictReader(fh))
        if not games:
            raise ValueError("no data rows")
    except Exception:  # noqa: BLE001
        check("games:total", False, "games.csv missing or unparseable")
        check("games:seeds_per_cell", False, "games.csv missing or unparseable")
        games = None
    if games is not None:
        meta = canon["_meta"]
        check("games:total", len(games) == meta["total_games"],
              f"{len(games)} rows vs total_games={meta['total_games']}")
        cell_counts = Counter((r["policy"], r["geometry"]) for r in games)
        bad = {k: v for k, v in cell_counts.items() if v != meta["seeds_per_cell"]}
        check("games:seeds_per_cell", not bad,
              f"expected {meta['seeds_per_cell']} per cell, deviations: {bad}"
              if bad else f"{len(cell_counts)} cells x {meta['seeds_per_cell']} seeds")

    # ---- 6. informational: results.json vs canonical (SUPERSEDED) ----------
    try:
        old = json.load(open(B13 / "results.json"))
        same = ({c["geometry"]: c for c in old.get("cells", [])} == canon_cells
                and old.get("overall") == canon["overall"])
        prov = json.load(open(B13 / "provenance.json"))
        status = prov.get("files", {}).get("results.json", {}).get("status", "")
        note = ("matches canonical" if same else
                "DIFFERS from canonical (expected: marked "
                f"'{status}' in provenance.json)")
        print(f"INFO: results.json {note}")
    except Exception as e:  # noqa: BLE001
        print(f"INFO: results.json could not be compared: {e}")

    return _verdict()


def _verdict() -> int:
    failed = [(n, d) for n, ok, d in checks if not ok]
    width = max(len(n) for n, _, _ in checks) if checks else 0
    for n, ok, d in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}  {d}")
    verdict = "PASS" if not failed else "FAIL"
    print(f"\nB13 CONSISTENCY: {verdict}  "
          f"({len(checks) - len(failed)}/{len(checks)} checks passed)")
    if failed:
        print("failed checks:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
