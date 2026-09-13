"""Research layer for geometry-aware differential-game analysis.

Discipline (see ../iron_bottom_sound_research_plan.md):
- The rule engine (`iron_bottom_sound.engine`) is the sole adjudicator.
- This layer is read-only: it never mutates `GameState`, never reads hidden
  information for policy decisions, and never copies rule constants.  All
  table lookups go through engine public/private query functions.
"""
