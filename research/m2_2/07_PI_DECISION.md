# 07_PI_DECISION.md — what only the PI can decide

M2.2 stopped here by instruction. Four decisions are now the PI's, in dependency
order.

## 1. Which mechanism value is the research object?

The frozen `M_broad` was implemented fleet-wide and it decides the MG1 verdict
against the compiler: gold -12.17 < random -6.32 < beam +5.47. Restricted to the
case's own pair, the same formula gives gold +1.89 > random +1.44 > current
+1.36, and the case becomes a compiler gap. Both are the frozen formula; they
differ only in scope, and they disagree in sign.

- Option A — fleet margin stays primary. Then MG1's case is unusable as a
  compiler test and the fleet-margin operationalisation itself becomes the
  finding ("unmasking is individually good and collectively bad").
- Option B — pair margin. Then the compiler question is well-posed on MG1, and
  MG3/MG4 keep their own panels. `M_range` for MG3 is untouched either way (it is
  zero for a different reason: M22-F4).
- Option C — report both panels everywhere and treat the divergence as the
  quantity of interest.

Recommendation: **C**, because the divergence is measured, exact, reproducible,
and is the same symmetry effect the project has now seen three times.

## 2. MG3 — what to do with M22-F4

`MG3_RANGE_CONTROL = VALID PASS` was measured by a meter with no visibility
gate; the arms are at 15/17 hexes against a 13-hex visibility with radar off, so
neither arm is executable. The historical verdict is preserved verbatim in this
bundle. The PI decides whether to (i) re-scope the MG3 verdict as meter-limited,
(ii) build a replacement range-control case inside the envelope under a new
pre-registration, or (iii) leave MG3 as recorded and cite M22-F4 as a caveat.

## 3. MG4 — promote the public-information gap?

"The long-range torpedo corridor is real and not identifiable from
observation-grade information" is currently a side-result of a compiler audit.
It is the strongest negative the project has, it is engine-verified, and its
evidence is a tie-set structure rather than a single number. The PI decides
whether it becomes a research object in its own right.

## 4. B1 census

Gated off by the pre-registration and not run. If the PI wants natural
opportunity numbers, decision 1 must be taken first and a new pre-registration
written; running the census under the frozen fleet metric is known in advance to
be uninformative for MG1.

## Explicitly not done, per instruction

No re-running MG2/MG5 to reach 4/5. No MAPPO/QMIX/GNN/Transformer. No invented
paper method. No production rule edits. No value-realisation claim, no RL, no
paper writing. Nothing is called optimal or an oracle.
