"""v14 table generation (master plan section 4: four main tables).

Table 1  notation and assumptions
Table 2  closest-work differences
Table 3  frozen experimental design
Table 4  main results (budget frontier, optimal calendars, certified intervals)

Tables 1-3 are generated from frozen metadata (DESIGN.json, the literature
positioning file, the run freezes) and therefore contain no experimental
result.  Table 4 is generated only from the frozen solver outputs through
analysis_v14.py, so every number in it is traceable to a value file.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V14 = REPO / "research" / "final_v14"
OUT = V14 / "tables"
TEX = REPO / "paper_v14" / "tables"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print("wrote", path.relative_to(REPO))


def table1() -> None:
    rows = [
        ("$S\\subseteq\\{1,\\dots,T-1\\}$", "public revision calendar; $|S|\\le K$",
         "frozen and announced before play; initial epoch $t=0$ is not a revision"),
        ("$K$", "revision budget", "$W_K=\\max_{|S|\\le K}V(S,R)$ is nondecreasing (Prop.~1)"),
        ("$\\kappa\\in\\{F,C\\}$", "opponent class", "$F$ fully flexible, $C$ committed; classes are not mixed in a comparison"),
        ("$\\Pi_S$", "own policy set under calendar $S$", "sealed blocks between consecutive updates; current block and unexecuted suffix are private"),
        ("$V(S,R)$", "game value with own calendar $S$ and opponent calendar $R$", "mixed minimax; finite horizon, $\\gamma=1$"),
        ("$C_q(j\\mid i)$", "counterfactual conditional law of opponent path $j$ given own path $i$", "does not assume opponent commitment; reduces to $q_j$ for committed $q$"),
        ("$\\mathrm{BR}_S(q)$", "exact best response of own calendar $S$ against $q$", "complete permitted policy class (Thm.~3)"),
        ("$d(t,e)$", "interval loss for committing over $[t,e)$ against $F$", "$\\ge0$, $d(t,t+1)=0$; used in the interval certificate"),
        ("$x_{ik},\\psi_{ik}$", "vessel position and heading", "$=\\gamma_i(s_i-\\ell_k)$ and the local tangent; history matters"),
        ("$L(h_t)$", "formation interaction differential", "sum over vessel pairs of the directional kernel difference"),
    ]
    body = "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in rows)
    w(TEX / "table1_notation.tex", r"""\begin{table}[!htb]
\centering\small
\caption{Notation and the assumptions each symbol carries.  Every
comparison in this paper fixes the opponent speed, opponent range, opponent
class, geometry, horizon, formation model and payoff; only the own calendar
and the own speed capability vary within a comparison.}
\label{tab:notation}
\begin{tabular}{p{2.5cm}p{4.4cm}p{6.6cm}}
\toprule
Symbol & Meaning & Assumption or scope \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table2() -> None:
    rows = [
        ("Huang--Zhu (arXiv:2102.05469)", "purchases observation opportunities in an LQG pursuit--evasion game",
         "we budget \emph{command revisions} on a public calendar; information is observed continuously, action is not",
         "neither model subsumes the other"),
        ("Hogeboom-Burr--Y\\\"uksel (arXiv:2005.06673)", "more information cannot hurt the informed player (zero-sum comparison)",
         "our inclusion lemma is a finite special case; used as a correctness condition",
         "not claimed as new"),
        ("Chen--Waggoner (arXiv:1703.08636)", "substitutes vs complements of signals depend on the decision problem",
         "we give a binary-action counterexample showing calendars need not be submodular",
         "extends the caution to revision calendars"),
        ("McMahan et al. (ICML 2003)", "robust planning against adversarial costs via response oracles",
         "our pricing recurrence specialises one-sided generation to sealed-block histories",
         "specialisation, not a new oracle theory"),
        ("Bo\\v{s}ansk\\'y et al. (JAIR 2014)", "exact double oracle for extensive-form zero-sum games",
         "we optimise the information structure (calendar), not a strategy inside a fixed one",
         "no raw node-count comparison across different games"),
        ("McAleer et al. (XDO, 2021)", "double oracle with mixing at information states",
         "our root-policy generation is not XDO and carries no polynomial iteration guarantee",
         "oracle tailored to a small history lattice"),
        ("Kroer--Sandholm (NeurIPS 2018)", "unified abstraction bounds for extensive-form games",
         "our deletion certificate bounds loss of a specified feasible calendar policy by an exact full response",
         "narrower than their general theorem"),
    ]
    body = "\n".join(f"{a} & {b} & {c} & {d} \\\\" for a, b, c, d in rows)
    w(TEX / "table2_literature.tex", r"""\begin{table}[!htb]
\centering\small
\caption{Closest work and the precise difference.  The rightmost column states
what we do \emph{not} claim, so that standard components are not restated as
novelty.}
\label{tab:literature}
\begin{tabular}{p{3.1cm}p{3.6cm}p{4.4cm}p{2.4cm}}
\toprule
Work & What it already gives & Our relation & Not claimed \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table3() -> None:
    d = json.loads((V14 / "DESIGN.json").read_text())
    cells = d["cells"]
    phase_rows = []
    for ph, label in (("development", "Development"),
                      ("test", "Frozen test"),
                      ("robustness", "Robustness"),
                      ("ablation", "Ablation")):
        sub = [c for c in cells if ph in c["phases"]]
        geo = sorted({c["geometry"] for c in sub})
        spd = sorted({c["speed"] for c in sub})
        Ts = sorted({c["T"] for c in sub})
        grids = sorted({c["grid"] for c in sub})
        ab = sorted({c["ablation"] for c in sub})
        ncond = sum(2 * (1 + (1 if c.get("mirror_solve_all") else 0)) for c in sub)
        phase_rows.append((label, f"{len(sub)}", ", ".join(geo),
                           f"{min(spd):.2f}--{max(spd):.2f}",
                           ", ".join(str(t) for t in Ts),
                           ", ".join(f"Grid-{g}" for g in grids),
                           f"{ncond}", ", ".join(a for a in ab)))
    body = "\n".join(" & ".join(r) + " \\\\" for r in phase_rows)
    w(TEX / "table3_design.tex", r"""\begin{table}[!htb]
\centering\small
\caption{Frozen experimental design (declared before any output of the
corresponding phase was produced; see the design freeze hash in the
reproducibility package).  ``Conditions'' counts solver runs: two opponent
classes per cell, times two sides where the mirror is solved.  Speeds are the
focal player's forced operating speeds relative to the opponent's; all other
model parameters are frozen.}
\label{tab:design}
\begin{tabular}{lccccccc}
\toprule
Phase & Cells & Geometries & Focal speed & $T$ & Action grid & Conditions & Ablation \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table4() -> None:
    f = V14 / "analysis" / "budget_frontier.csv"
    r = V14 / "analysis" / "retention_budgets.csv"
    if not f.exists():
        print("table4: budget_frontier.csv not available yet; skipped")
        return
    fr = list(csv.DictReader(open(f)))
    rt = list(csv.DictReader(open(r))) if r.exists() else []
    # main results: per (cell, side, opponent) the frontier summary
    from collections import defaultdict
    grp = defaultdict(list)
    for row in fr:
        grp[(row["cell"], row["side"], row["opponent"])].append(row)
    lines = []
    for (cell, side, opp), rs in sorted(grp.items()):
        rs = sorted(rs, key=lambda x: int(x["K"]))
        W0 = float(rs[0]["W_K"]); Wmax = float(rs[-1]["W_K"])
        Kstar = min(int(x["K"]) for x in rs if abs(float(x["W_K"]) - Wmax) < 1e-9)
        loss = Wmax - W0
        lines.append((cell, side, opp, f"{Wmax:+.3f}", f"{loss:+.3f}", str(Kstar),
                      rs[-1]["S_star"], f"{float(rs[-1]['gap']):.1e}",
                      rs[-1]["status"]))
    body = "\n".join(" & ".join(x) + " \\\\" for x in lines)
    w(TEX / "table4_results.tex", r"""\begin{table}[!htb]
\centering\small
\caption{Budget frontier summary over the frozen design.  $W_{\max}$ is the
full-flexibility value, ``loss'' is $W_{\max}-W_0$ (what the revision budget is
worth), $K^\star$ is the smallest budget attaining $W_{\max}$,
$S^\star$ is a maximizing calendar, and the gap is the certified solver
residual of that cell.  Cells whose solver status is not certified are marked
and are not used for ratio statements.}
\label{tab:results}
\begin{tabular}{lcccccccc}
\toprule
Cell & Side & Opp. & $W_{\max}$ & Loss & $K^\star$ & $S^\star$ & Gap & Status \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


if __name__ == "__main__":
    table1(); table2(); table3(); table4()
