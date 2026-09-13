"""E04 research layer: torpedo direct-kill vs maneuver-denial decomposition.

Doctrine-free measurement modules above the authoritative rules engine:
    routes.py    - full legal movement-plan space (mirrors engine.movement rules)
    lane.py      - analytic torpedo-lane timeline (mirrors engine impulse loop)
    scenarios.py - synthetic geometries + engine-driven sandbox progression
    protocol.py  - E04 A/C/D measurement protocol (per-seed paired samples)

Every rule quantity (hit probability, modifiers, arcs, gun pressure, torpedo
effect table) is read from the engine; no doctrine weights are used anywhere.
"""
