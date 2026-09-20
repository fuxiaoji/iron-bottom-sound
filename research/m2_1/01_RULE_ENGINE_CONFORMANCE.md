# 01_RULE_ENGINE_CONFORMANCE.md — P0 rule-to-engine conformance audit

**Audited commit**: research branch `research/m2-1-platform-audit` @ `184f605`.
Every row was checked in source and, where marked `probe`, by executing the
rule path directly this session. No production file was modified.

| rule_id_or_section | source_rule | engine_code_path | existing_test | probe_test | status | notes |
|---|---|---|---|---|---|---|
| Phase order R1 | reinforce→move-plan→torp-plan→move-res→gunnery→torp-eff→fire-end | `engine.advance` :1741-1800 | full剧本 tests | probe (phase walk) | SOURCE_EXACT | order verified live |
| S-01 axis no gunnery T1 / no torpedo <T4 | scenario special | `engine._torpedo_candidates` blocked_reason "想定特例" | scenario tests | **probe: blocked_reason returned at turn 1** | SOURCE_EXACT | gunnery T1 restriction enforced in `_resolve_gunnery` special case |
| Secret/sealed movement+torpedo | dual sealed batch | `engine._seal_orders` :1712, `_sealed_batches` :1718 | realistic tests | probe (submit→seal→obs) | SOURCE_EXACT | both batches sealed before resolution |
| Observation never leaks sealed orders | fog | `engine.observe` (no sealed_orders field) | api tests | **probe: axis plan string absent from allies obs JSON after sealing** | SOURCE_EXACT | also probe: `formation` appears only as null `formation_id` fields per ship (classic) — no hierarchy leak |
| Simultaneous movement | same-MF collision | `_resolve_movement` collision by MF | collision tests | source read | SOURCE_EXACT | per-MF group resolution :3039+ |
| First MF straight / 60° free / 120°=1 MF | movement rules | `movement_commands` (P=60, PP=120+1MF), `_movement_program` | plan tests | **probe: `1PP2` → [advance, turn_port_120, advance, advance], cost 4** | SOURCE_EXACT | |
| Acceleration/deceleration + BB-BC braking | `_legal_speed_range` | :1671 | speed tests | probe (range returned 0-6 vs current 5) | SOURCE_EXACT | BB/BC stricter per `_forced_constraints` |
| Collision simultaneous | same-hex/mid-MF | `_resolve_movement`, `_resolve_ship_collision` | friendly-collision tests (2026-09-03 fix) | source read | SOURCE_EXACT | |
| Visibility/arcs/facing/speed modifier | gunnery mods | `_gunnery_modifiers` (range, target_speed, longitudinal, caliber, MFC, fire, radar/starshell/searchlight) | gunnery tests | source read | SOURCE_EXACT | |
| Obstruction / misfire | line-of-fire block | `_line_blocked` (probe read :2600) | gunnery tests | source read | SOURCE_EXACT | |
| Simultaneous gunnery damage | both sealed batches resolved at once | `_resolve_gunnery` uses `_sealed_batches(GUNNERY)` | gunnery tests | probe (both sides' batches sealed pre-resolution) | SOURCE_EXACT | |
| Damage persistence | hull/mount/MFC/radar/fire/rudder/bridge/speed/captain | `ShipState` fields, `_damage_snapshot` | damage tests | source read | SOURCE_EXACT | |
| Torpedo path/delay/reload/speed | launcher arcs, MF-synced tracks, reload turns | `_torpedo_candidates`, `_resolve_torpedoes` | torpedo tests | source read | SOURCE_EXACT | |
| **Illegal movement fallback** | original wargame has an illegal-plan fallback procedure | **`validate_orders` rejects before submit** (:1488-1535); no fallback execution path exists | - | probe (invalid plans never enter state) | INTENTIONAL_INTERFACE_STRICTER | per plan §4 this audit compares only validator-passed actions; NOT a bug — deliberate digital-interface choice |
| S-01 victory | 7 turns, VP, ≥4 lead | `scenario_rules.resolve_victory` S-01 branch | scenario tests | source read | SOURCE_EXACT | lead≥4 else draw |
| S-03 victory | sink/cripple KM DDs | `resolve_victory` S-03 branch: qualifying = sunk or speed_track all ≤2 | scenario tests | source read | SOURCE_EXACT | **coarse as the plan warns** — M2.1 reports material/speed diagnostics alongside |
| EM-01 victory | damage points, 25 margin | `erma_damage_points` branch + `refresh_score` (hull/BB MFC/radar/primary/speed) | erma tests | source read | SOURCE_EXACT | dense scoring confirmed |
| Realistic formation follow/shared speed | leader trail + spacing | `expand_movement_orders` :432 | realistic tests | M2-0 probes | SOURCE_EXACT | |
| Realistic detach/withdrawal | speed crisis | `apply_detachments` :625, `ship_detached`/`ship_withdrawn` events | realistic tests | M2-0 census observed 41-446/match | SOURCE_EXACT | |
| Realistic succession/disruption/dissolution | flagship loss | `refresh_command_chain` :665; disruption = state flag `disruption_turn` (NO event type) | realistic tests | M2-0 census (F2) | SOURCE_EXACT | audit note: disruption is state-only |
| Formation cap 1-4 vs code | player rules 1-4 | `MAX_FORMATIONS_PER_SIDE = 8` | test asserts vs constant | read | **PROJECT_EXTENSION (recorded, not fixed)** | per plan: formal experiments use ≤4; research wrapper unaffected |
| Realistic gunnery/torpedo stay per-ship | combat individual | `prepare_gunnery` :647, `_torpedo_candidates` own-sealed only | realistic tests | M0/M2-0 probes | SOURCE_EXACT | |

## Summary

```
RULE_ENGINE_CONFORMANCE = PASS
```

- 0 BUG, 0 UNKNOWN, 0 NOT_IMPLEMENTED.
- 1 INTENTIONAL_INTERFACE_STRICTER (illegal-move fallback → pre-submit reject);
  per plan §4 this **defines** the action space (validator-passed only) rather
  than blocking.
- 1 PROJECT_EXTENSION recorded (formation cap 8 vs docs 4); formal
  rule-sensitive experiments use ≤4 formations.
- No blocker: leverage experiments proceed.
