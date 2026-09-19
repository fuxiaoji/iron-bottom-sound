# MODE_SEMANTICS_AUDIT.md — P0 mode-semantics audit at current HEAD

**Audited commit**: `48846a9` (branch `research/m2-0-organizational-intelligence`, parent of the research branch).
Everything below was verified in source at this commit, not from documents.

## 1. Classic mode (`realistic_command=False`)

| item | verified behaviour | source |
|---|---|---|
| movement action object | per-ship `MovementOrder(ship_id, plan, speed, commands)`; the commander emits one order per alive own ship each `MOVEMENT_PLANNING` | `models.py` (MovementOrder), `tactical.py::choose_plan` |
| TacticalCommander decision granularity | **per ship** — `_plan_movement` scores candidates per ship (formation preferences `w_formation`/`line_ahead` are scoring weights only; they do NOT merge ships into one decision entity) | `tactical.py` |
| gunnery granularity | per ship / per mount (`GunneryOrder` with mount targets) | `tactical.py::_plan_gunnery`, `models.GunneryOrder` |
| torpedo granularity | per ship / per launcher (`TorpedoOrder`) | `models.TorpedoOrder` |
| observation boundary | `observe(side)`: own ships revealed; enemies position-visible per fog rule, damage optionally hidden (`optional_rules.hidden_damage`); **no formation concept exists in classic mode at all** | `engine.observe` |
| legal-action boundary | `legal_actions(side)` returns phase schema; movement candidates enumerated per owned ship via `movement_candidates(state, ship)` | `engine.legal_actions` |
| profiles | `PROFILES`: balanced, fleet, line, brawl, torpedo, cautious, adaptive, direct_attack, area_denial, break_crossing_t, formation_split, crossfire, cover_withdrawal (13) + champion `evolved` | `tactical.PROFILES`, `champions.CHAMPIONS` |
| supported scenarios | 15 catalogued; **playable: IBS-S-01, IBS-S-03, IBS-S-EM-01** (12 raise "catalogued but not playable") | `engine.reset` |

## 2. Realistic mode (`realistic_command=True`)

| item | verified behaviour | source |
|---|---|---|
| formation_setup | dedicated phase; `FormationSetupOrder(formation_id, name, ship_ids, leader_id, flagship_id, reserve_flagship_id, succession_order, spacing, heading)`; every ship must be in exactly one formation; flagship != reserve; leader/flagships must be members | `realistic_command.validate_setup` (~:142-160) |
| formation state | `FormationState` with `flagship_id`, `reserve_flagship_id`, `succession_order`, `status` ("active"/"dissolved"), `disruption_turn`, `command_status` per ship ("attached"/"detaching"/"retreating"/"withdrawn") | `models.py`, `realistic_command.py:215 resolve_setup` |
| formation movement | side submits **one `FormationMovementOrder` per active formation** (leader_plan + optional speed_decision); `expand_movement_orders` expands to per-ship orders: members follow the leader's trail with spacing | `realistic_command.py:432` |
| shared speed | formation speed shared via `speed_decision`; damage-induced speed incompatibility forces slow-down or detach | `realistic_command.py`, `after_movement` |
| detach | `speed_decision.action == "detach"` names ships; `apply_detachments` emits `ship_detached`; detached ships enter autonomous withdrawal toward an edge | `realistic_command.py:625` |
| command succession | flagship unavailable (sunk / captain killed / retreating/withdrawn) → `formation_command_transferred` to the next succession entry | `realistic_command.py:665 refresh_command_chain` |
| command disruption | transfer sets `disruption_turn` → next turn `command_disrupted` (formation movement restricted) | same |
| dissolution | no legal successor → `formation.status = "dissolved"` (state field; the attached ships are released rather than left orphaned) | `realistic_command.py:676,686,744` |
| gunnery / torpedo granularity | **unchanged from classic**: `prepare_gunnery` adapts batches but gunnery remains per-ship/per-mount; torpedo planning remains per-ship/per-launcher | `realistic_command.py:647`, `engine._torpedo_candidates` |
| enemy sees hierarchy? | **No.** `PlayerObservation` has no formation field at all (classic or realistic); formation membership/flagship/succession are state-internal and never exported through `observe()`. Saved-game summaries explicitly "never include units or sealed orders". | `models.PlayerObservation` |

## 3. The sentence this audit exists for

> **当前系统本质上仍是 side-level centralized commander。** Classic 与 realistic 的
> TacticalCommander / RealisticCommander 都是一次性为整个 side 产出完整
> OrderBatch 的集中式决策器——classic 逐舰、realistic 逐编队——都不是"每艘舰一个
> decentralized MARL agent"。`PlayerObservation` 是 side 级的；没有 per-ship local
> observation、没有 per-ship policy 接口。若论文进入 MARL，需要研究侧 wrapper 显式
> 定义 `o_i`（per-ship local observation）、`o_G`（group observation）与 CTDE critic
> 的全局可见性；本阶段不实现。

## 4. Document/code mismatch (recorded, NOT fixed)

```
docs/rules/realistic-command.md §三.1:  "每方建立一至四个编队"   (1-4)
realistic_command.py:44:                MAX_FORMATIONS_PER_SIDE = 8
```

Per the M2-0 plan: **not fixed here**; all formal realistic-mode experiments in
this phase use **≤4 formations** so no conclusion depends on the un-unified
boundary. (The M2-0 research wrapper operates on classic semantics and is not
bound by realistic formation rules at all.)

## 5. Confound statement (why classic-vs-realistic is not a valid abstraction experiment)

Realistic mode changes far more than control granularity: shared speed,
permanent detach + autonomous withdrawal, command disruption (a next-turn
control constraint), succession, dissolution, and formation-level legality.
A `classic flat vs realistic formation` win/loss comparison therefore measures
a bundle of rule changes plus the control hierarchy. Track A isolates the
granularity variable with a research-side **ResearchGroupExecutor** on classic
semantics (plan §8); realistic mode is used only for Track B, where the
command-state machinery is the object of study.
