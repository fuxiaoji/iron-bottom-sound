#!/usr/bin/env python3
"""Reviewer revisions pass 2 (fault-tolerant)."""
import pathlib
import sys

P = pathlib.Path("/Users/Zhuanz1/Desktop/code/seawar/iron-bottom-sound/paper/main.tex")
s = P.read_text(encoding="utf-8")
applied, failed = [], []

def sub(old, new, name):
    global s
    if old in s:
        s = s.replace(old, new, 1)
        applied.append(name)
    else:
        failed.append(name)

# Major 1 refinement
sub("""Speed becomes valuable only in
combination with a range advantage: at $\\etar=1.33$ every speed ratio
yields strongly positive values ($+2.8$ to $+3.2$), and at $\\etar=0.75$
negative ones.""",
"""Speed becomes valuable only in
interaction with a range advantage: at $\\etar=1.33$ the value is strongly
positive for $\\etav\\le1$ ($+2.8$ to $+3.0$) but decays through $+0.45$
to $-0.31$ for the fastest ratios, and at $\\etar=0.75$ it is negative
throughout ($-0.2$ to $-2.6$); across the whole scan the range ratio
$\\etar$ dominates the sign of the value.""",
"M1-range-interaction")

# Major 2: E06 statistics
sub("""Against the non-maneuvering \\emph{straight} baseline
the geometry policy produces a large, significant paired damage
differential in every geometry ($+7.2$ [$+5.8,+8.6$] parallel,
$+3.1$ [$+1.2,+5.3$] head-on, $+8.7$ [$+7.2,+10.3$] crossing hull points
in favor of the policy side; $97$--$100\\%$ of pairs positive).  Against
the doctrine profiles (\\emph{line}, \\emph{balanced}) the policy is
statistically indistinguishable (all CIs straddle zero)---consistent with
the degeneracy proposition: in a symmetric duel a mature heuristic already
captures most positional value, and the surrogate's contribution is to
\\emph{guarantee} it from first principles rather than to dominate.
Figure~\\ref{fig:e06} shows the paired forest plot.""",
"""Against the non-maneuvering \\emph{straight} baseline
the geometry policy produces a large, significant paired damage
differential in every geometry: $+7.2$ [$+5.8,+8.6$] in the parallel
geometry ($100\\%$ of pairs positive), $+8.7$ [$+7.2,+10.3$] in the
crossing geometry ($96.7\\%$), and $+3.1$ [$+1.2,+5.3$] head-on---the last
with the weakest consistency ($63.3\\%$ of pairs positive; the interval
remains above zero, but the policy's advantage is least stable when both
sides start converging head-on).  Against the doctrine profiles the
picture is mixed and mostly null: after a Bonferroni-style correction for
the nine paired cells only the straight-baseline cells survive, the
crossing cell against \\emph{balanced} is positive ($+1.83$ [$+0.10,+3.77$]),
and the head-on cell against \\emph{line} points the other way
($-1.40$ [$-3.37,+0.63$]).  The fair summary is parity with mature
heuristics---consistent with the degeneracy proposition: in a symmetric
duel a mature doctrine commander already captures most positional value,
and the surrogate's contribution is to \\emph{guarantee} it from first
principles rather than to dominate.  Figure~\\ref{fig:e06} shows the
paired forest plot.""",
"M2-e06-stats")

# Major 6b
sub("""The fitted
$M_r$ recovers the engine's eight discrete range bands as a smooth curve
(e.g., the CA fit inverts to $-24,-15,-12,-6,0,+2,+4$ at the band centers,
matching the engine's table to the unit), and the fitted $M_\\ell$ recovers
the longitudinal-fire penalty bands, including their reversal of sign
relative to naive expectations for light guns.""",
"""The fitted
$M_r$ tracks the engine's seven discrete range bands as a smooth curve:
the CA fit inverts to $-24.9, -16.4, -13.4, -4.8, +1.2, +3.2, +5.2$ at the
band centers against the engine's $-24, -15, -12, -6, 0, +2, +4$ (mean
absolute deviation $\\approx1.2$ modifier points, a small systematic
offset toward the origin), and the fitted $M_\\ell$ recovers the
longitudinal-fire penalty bands, including their sign relative to naive
expectations for light guns.""",
"M6b-inversion")

# Major 6c
sub("""the engine's coarse hit-table granularity makes the target's
gun-position value landscape \\emph{tiered}---across 580 legal plans the
cruiser's $J$ takes only 8 distinct values, and the top tier ($J/J_{\\text{ref}}=1$)
is shared by 25.5 tied routes on average.""",
"""the engine's coarse hit-table granularity makes the target's
gun-position value landscape \\emph{tiered}: each measurement's plan space
holds 340--600 legal plans, within which $J$ takes on average only 8
distinct values (4--14 across cells), and the top tier
($J/J_{\\text{ref}}=1$) is shared by 25.5 tied routes on average
(12--32.5 across cells).""",
"M6c-tiers")

# Major 8
sub("""$V_{\\text{denial}} = 0.0000$
with bootstrap $95\\%$ CI $[0.0000, 0.0000]$ in \\emph{every} geometry and
under all threat weightings ($w=0.343$, $w=1$, and constant-threat
condition D).  The pre-registered acceptance (CI above zero in at least
three geometries) therefore \\textbf{fails}, and we report it as a null
result with its mechanism.""",
"""$V_{\\text{denial}}$ is
structurally identical to zero---all 216 samples equal $0$ exactly (the
bootstrap interval degenerates to $[0,0]$)---in \\emph{every} geometry and
under all threat weightings ($w=0.343$, $w=1$, and constant-threat
condition D).  The pre-specified acceptance (denial above zero in at least
three geometries) therefore \\textbf{fails}, and we report it as a null
result with its mechanism.""",
"M8-structural-zero")

# Major 4 + 5: deviations paragraph
sub("""\\paragraph{Interpretation.}  ``Torpedoes that miss but change the battle'""",
"""\\paragraph{Deviations from the pre-analysis plan and design confounds.}
Two protocol deviations occurred before measurement and are recorded in
the repository's experiment log: (i)\\ the originally planned
``launch on turn~1, response on turn~2'' design proved structurally
infeasible---a pilot scan of $\\approx700$ candidate geometries showed the
turn-1 track already sweeps the target's turn-2 reachable set, collapsing
every contact into close broadside shots---so the protocol measures
same-turn perfect-information responses, mirroring the engine's own
torpedo-assist intercept model; (ii)\\ geometries were selected by the
same pilot scan so that a stable low-hit opportunity pool exists.  The
analysis gates were fixed in the project's planning document and scripts
before the measurements reported here; no external registry was used.
Two design confounds qualify the direct-hit contrast: it comes from a
single geometry (close), jointly changing range, hit expectancy, and
track-tier overlap; and the low-hit pool's $\\mathbb{E}[\\text{hits}]$ is
constant at $1/12$ (zero variance), so the ``low-hit regime'' is a single
point of the hit distribution.  A geometry $\\times$ salvo-size factorial
that separates these factors is the natural continuation.

\\paragraph{Interpretation.}  ``Torpedoes that miss but change the battle'""",
"M4M5-deviations")

# Major 9 + E05 cluster caveat
sub("""The pre-specified acceptance is therefore
\\textbf{not met}, and per the plan's decision rule the engagement graph is
demoted from a headline claim to a secondary/appendix analysis""",
"""The pre-specified acceptance is therefore
\\textbf{not met}, and per the plan's decision rule the engagement graph is
demoted from a headline claim to a secondary/appendix analysis (one
statistical caveat points the same way: the bootstrap resamples
ship-turn samples rather than whole games, so game-level clustering would
widen the intervals around an already-sub-threshold estimate)""",
"M9-e05-cluster")

# Minor: E03 ghost labels
sub("\\section{Layer 2: The Committed-Maneuver Game (E02, E03)}",
    "\\section{Layer 2: The Committed-Maneuver Game (E02)}",
    "minor-e03-title")
sub("\\caption{E03 mechanism analysis: game value along the speed-ratio axis at",
    "\\caption{Speed-mechanism analysis (produced by the E02 script): game value along the speed-ratio axis at",
    "minor-e03-caption")

# Minor: E04 target class
sub("A destroyer (Fubuki class, Type~90 torpedoes) attacks a\nheavy cruiser (New Orleans class) across",
    "A destroyer (Fubuki class, Type~90 torpedoes) attacks a\nheavy cruiser (Northampton class) across",
    "minor-e04-class")

# Minor: abstract classes
sub("across destroyer, cruiser,\nand battleship classes.",
    "across four ship classes (DD/CL/CA/BB).",
    "minor-abstract-classes")

# Minor: J_ref definition
sub("The threat weight $w=0.343$\nis the engine collision table's expected damage fraction for the cruiser's\ndisplacement band (36-outcome enumeration)",
    "All denial values are in units of the gun-position value $J$; normalized values divide by the reference position value $J_{\\text{ref}}=J(\\tau_0^*)$.  The threat weight $w=0.343$\nis the engine collision table's expected damage fraction for the cruiser's\ndisplacement band (36-outcome enumeration)",
    "minor-jref")

# Minor: references
sub("""\\bibitem{networked2020}
``Optimising structure in a networked Lanchester model for fires and
man{\\oe}uvre in warfare,'' \\emph{Journal of the Operational Research
Society}, vol.~72, no.~8, pp.~1863--1878, 2021.""",
"""\\bibitem{networked2020}
A.~C. Kalloniatis, K.~Hoek, M.~Zuparic, and M.~Brede, ``Optimising
structure in a networked Lanchester model for fires and man{\\oe}uvre in
warfare,'' \\emph{Journal of the Operational Research Society}, vol.~72,
no.~8, pp.~1863--1878, 2021.""",
"minor-ref-networked")
sub("""\\bibitem{cubic1993}
``The cubic algorithm for global games with application to pursuit-evasion
games,'' \\emph{Computers \\& Mathematics with Applications}, vol.~26,
no.~6, pp.~13--31, 1993.""",
"""\\bibitem{cubic1993}
E.~A. Galperin, ``The cubic algorithm for global games with application to
pursuit-evasion games,'' \\emph{Computers \\& Mathematics with
Applications}, vol.~26, no.~6, pp.~13--31, 1993.""",
"minor-ref-cubic")
sub("""\\bibitem{wez2022}
``A multi-UCAV cooperative occupation method based on weapon engagement
zones for beyond-visual-range air combat,'' \\emph{Defence Technology},
vol.~18, no.~6, pp.~1006--1022, 2022.""",
"""\\bibitem{wez2022}
W.~Wu, J.~Shi, Y.~Wu, Y.~Wang, and Y.~Lyu, ``A multi-UCAV cooperative
occupation method based on weapon engagement zones for beyond-visual-range
air combat,'' \\emph{Defence Technology}, vol.~18, no.~6, pp.~1006--1022,
2022.""",
"minor-ref-wez")

# Minor: reproducibility commit
sub("""All runs are
seeded; paired comparisons share scenario, seed and initial placement;
confidence intervals are bootstrap or exact (matrix-game LP).""",
"""All runs are
seeded; paired comparisons share scenario, seed and initial placement;
confidence intervals are bootstrap or exact (matrix-game LP).  The frozen
engine commit for every number in this paper is \\texttt{fc77a65}
(\\texttt{github.com/fuxiaoji/iron-bottom-sound}).""",
"minor-repro-commit")

# Minor: seeds wording
sub("""36 paired seeds per cell (288 measurement samples).""",
"""36 paired seeds per cell, yielding 216 low-hit plus 72 direct-hit
measurement samples (the direct-hit pool exists only in the close
geometry).""",
"minor-e04-seeds")

# Minor: lambda note
sub("with $\\delta_B=-\\alpha_B$, $\\delta_R=\\pi-\\alpha_R$, and aspects from the\n$\\pm30^\\circ$ bow/stern sector rule.  No tactical doctrine enters $L$.",
    "with $\\delta_B=-\\alpha_B$, $\\delta_R=\\pi-\\alpha_R$, and aspects from the\n$\\pm30^\\circ$ bow/stern sector rule; $\\lambda=1$ throughout (asymmetric\nvalue weightings are not explored, and the degeneracy proposition of\nSection~\\ref{sec:degeneracy} additionally presumes identical kernels).  No\ntactical doctrine enters $L$.",
    "minor-lambda")

# Minor: E01 baselines limitation
sub("""(i)~The surrogate is calibrated per ship
class-pair on open-water geometry; terrain, smoke, radar illumination and
formation effects are not in $L$.""",
"""(i)~The surrogate is calibrated per ship
class-pair on open-water geometry; terrain, smoke, radar illumination and
formation effects are not in $L$, calibration has not been tested across
unseen ship pairs, and no weaker surrogate baselines (isotropic kernel,
axial-walk bearings) were run, so the $\\rho=0.991$ largely certifies the
fidelity of the calibration pipeline rather than a margin over simpler
surrogates.""",
"minor-e01-baselines")

# Minor: fig1 caption
sub("""\\caption{E01 calibration.  Top: heavy-cruiser kernel $K(r,\\delta)$
(left) against engine-true expected hits (right) at neutral target speed;
the anisotropy (bow/starboard/stern/port arcs) is structural and exact.
Bottom: held-out calibration scatter for all four classes.}""",
"""\\caption{E01 calibration (CA shown as representative; DD/CL/BB maps are
included in the repository results).  Top: heavy-cruister kernel
$K(r,\\delta)$ (left) against engine-true expected hits (right) at neutral
target speed; the anisotropy (bow/starboard/stern/port arcs) is structural
and exact.  Bottom: held-out calibration scatter for all four classes.}""",
"minor-fig1")

# Minor: lines count
sub("""The IBS engine (Python, $\\approx$13.9k lines; deterministic) implements a""",
"""The IBS engine (Python, $\\approx$13.8k lines across the engine package;
deterministic) implements a""",
"minor-lines")

P.write_text(s, encoding="utf-8")
print("applied:", len(applied))
for a in applied:
    print("  +", a)
print("failed:", len(failed))
for f in failed:
    print("  -", f)
