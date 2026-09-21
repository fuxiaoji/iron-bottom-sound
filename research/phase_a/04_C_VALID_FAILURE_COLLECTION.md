# 04_C_VALID_FAILURE_COLLECTION.md

**Not run.** C1 is gated on C0 passing (plan §5); C0 returned
`C_GENERATOR_FEASIBILITY_FAIL` on both tasks, so no fresh collection, no attempt
budget was consumed beyond C0, and no injection metadata exists for A.3
(`raw/track_c_failures/` is empty by design). The 1000-attempt cap and the
first-50-valid rule therefore never came into play.
