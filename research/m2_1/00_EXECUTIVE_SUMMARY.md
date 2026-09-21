# 00_EXECUTIVE_SUMMARY.md — M2.1-R2.1 Mechanistic Gold Repair

**Repair complete. `MECHANISTIC_GOLD_GATE = FAIL` (3 of 5). Stage B/C not
entered. Stopped for PI review.**

```
MG1_BROADSIDE             = VALID_PASS  (FROZEN — not re-run, not re-tuned)
MG2_CROSSING_THE_T        = FAIL        (repaired meter)
MG3_RANGE_CONTROL         = VALID_PASS  (FROZEN)
MG4_REAL_TORPEDO_CORRIDOR = PASS        (repaired)
MG5_LOCAL_FORCE           = FAIL        (repaired meter; assumption unsupported)

MECHANISTIC_GOLD_GATE = FAIL  (3/5; unchanged requirement >= 4)
```

## The two repairs that matter

**F21 (PI-identified, fixed).** `measure_side()` counted one gun mount once
per visible target, so usable-GF and expected-hits were not legal allocations.
The repaired meter: each mount allocated at most once; the engine's own
grouping (`attackers` concentration bonus, `target_count` split penalty, and
per-`mount.kind` hit-table lookups) applied exactly; visibility (`_can_see`)
required in addition to `_mount_can_bear`; every arm's batch passes
`validate_orders(_prepared=True)`. Two further fidelity defects surfaced
during the repair (modifier grouping, visibility) and are recorded.

Effect: MG2's exchange ratio fell from 1.68x (illegal) to **1.56x (legal)** and
its raking fraction is 0.44 — **MG2 = FAIL** on the unchanged
bow/stern >= 50% condition. MG5 stays FAIL: with a legal meter DISPERSE still
beats CONCENTRATE (19.22 vs
13.19).

**F22 + corridor rebuild (MG4, fixed).** Three separate defects had produced
the M2.1-R2 false negative: aiming was taken from the engine's
intercept-only combo API; the "safe route" test used hull damage rather than
torpedo contact; and the space-time segment was off by one hex (path[allowance]
vs path[allowance+1]). With all three fixed:

- **persistence probe PASS** — 6/6 tracks survive to T+1 with
  `range_remaining > 0`, `distance_travelled > 0`, and are visible to the
  victim (PI's engine reading confirmed);
- **corridor PASS** — a real, validated long-range launch (setting range 25)
  covers **28 of the victim's 29 legal next-turn routes**
  (contact fraction 0.966), the only safe
  route being "hold";
- `RouteReduction = 0.966` (gate >= 0.25);
- **the space-time prediction matches the engine's own `torpedo_contact`
  verdict on 29/29 routes.**

## Where the four-layer decomposition now stands

| layer | evidence | status |
|---|---|---|
| rule mechanics — aspect/heading | MG1 (frozen): +92.9% expected hits broadside vs narrow | **strong leverage** |
| rule mechanics — range | MG3 (frozen): 2.56 vs 0.94 expected hits over 2 hexes | **strong leverage** |
| rule mechanics — torpedo area denial | MG4-R: 28/29 routes denied, engine-verified | **strong leverage** |
| rule mechanics — crossing the T | MG2-R: exchange 1.56x but raking only 0.44 | **not yet demonstrated** (positioning, not rules) |
| rule mechanics — local force | MG5-R: DISPERSE better | **not supported at this scale** |
| compiler fidelity | Stage B | NOT TESTED |
| value realization | Stage C | NOT TESTED |

The PI's revision of the earlier claim is now itself revised by evidence:
> not just "gun deployment and range control have strong rule-level leverage",
> but **torpedo area denial does too** — a legal long-range corridor removes
> 28 of 29 next-turn route options, verified against the engine's own contact
> events. Crossing-the-T's failure is now localised to *reaching* the raking
> position, which is precisely the compiler question Stage B was built for.

## Integrity

- `PRE_REGISTRATION_R21.md` written before any repaired measurement; MG1/MG3
  frozen; MG2/MG5 states reused (no re-search); MG4's search rule frozen
  (geometric conditions only) before any RouteReduction was computed.
- New failure records: F21 (double counting), F22 (space-time off-by-one),
  plus modulus-grouping and visibility fidelity fixes.
- Budget: ~1,200 engine evaluations; 0 paid LLM; production engine untouched.
