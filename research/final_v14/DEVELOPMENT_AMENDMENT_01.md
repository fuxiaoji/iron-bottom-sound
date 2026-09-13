# Development implementation amendment 01

2026-09-13. Before any frozen-test result. The head-on speed-one engineering pilot was too optimistic about normal-form policy-generation iteration counts. The first development instance (head_on, speed .85, distance16, T6) spent several minutes on the full-flexible/committed solve. No calendar result from that run had been written; its independently generated physical payoff pair is retained. This is an efficiency limitation, not evidence about calendar value signs.

The initial run freeze, code snapshot and log are archived in development_amendment_01/. Stop only the two v14 processes started by this task. The new portfolio runs at most64 policy-generation iterations, then solves the SAME full perfect-recall sequence-form game if the response gap remains above tolerance. The sequence-form strategy is saved in its own representation; the earlier restricted policy cannot be passed off as the final strategy. Physical model, design, denominator, numerical tolerance and test configurations are unchanged. Initial pricing time is included in total runtime.

The correctness suite is rerun before development resumes. A new RUN_FREEZE records the implementation. The engineering pilot keeps its original source snapshot and is not relabeled as a held-out speedup benchmark. No Q1 gate has passed.
