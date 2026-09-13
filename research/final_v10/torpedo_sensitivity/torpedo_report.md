# v10 Phase 5: delayed-threat sensitivity under leader-follower motion

| geometry | eta_r | model | threat | corridor | intensity | base set | surviving | C_resp |
|---|---|---|---|---|---|---|---|---|
| head_on | 1.0 | rigid_line_ahead | narrow_weak | 3.0 | 0.5 | 45 | 40 | 0.111 |
| head_on | 1.0 | rigid_line_ahead | narrow_strong | 3.0 | 2.0 | 45 | 30 | 0.333 |
| head_on | 1.0 | rigid_line_ahead | broad_weak | 8.0 | 0.5 | 45 | 40 | 0.111 |
| head_on | 1.0 | rigid_line_ahead | broad_strong | 8.0 | 2.0 | 45 | 30 | 0.333 |
| head_on | 1.0 | rigid_line_ahead | wide_weak | 14.0 | 0.5 | 45 | 40 | 0.111 |
| head_on | 1.0 | rigid_line_ahead | wide_strong | 14.0 | 2.0 | 45 | 30 | 0.333 |
| head_on | 1.0 | leader_follower | narrow_weak | 3.0 | 0.5 | 246 | 246 | 0.000 |
| head_on | 1.0 | leader_follower | narrow_strong | 3.0 | 2.0 | 246 | 32 | 0.870 |
| head_on | 1.0 | leader_follower | broad_weak | 8.0 | 0.5 | 246 | 246 | 0.000 |
| head_on | 1.0 | leader_follower | broad_strong | 8.0 | 2.0 | 246 | 32 | 0.870 |
| head_on | 1.0 | leader_follower | wide_weak | 14.0 | 0.5 | 246 | 246 | 0.000 |
| head_on | 1.0 | leader_follower | wide_strong | 14.0 | 2.0 | 246 | 32 | 0.870 |
| parallel | 1.2 | rigid_line_ahead | narrow_weak | 3.0 | 0.5 | 20 | 20 | 0.000 |
| parallel | 1.2 | rigid_line_ahead | narrow_strong | 3.0 | 2.0 | 20 | 20 | 0.000 |
| parallel | 1.2 | rigid_line_ahead | broad_weak | 8.0 | 0.5 | 20 | 20 | 0.000 |
| parallel | 1.2 | rigid_line_ahead | broad_strong | 8.0 | 2.0 | 20 | 20 | 0.000 |
| parallel | 1.2 | rigid_line_ahead | wide_weak | 14.0 | 0.5 | 20 | 20 | 0.000 |
| parallel | 1.2 | rigid_line_ahead | wide_strong | 14.0 | 2.0 | 20 | 20 | 0.000 |
| parallel | 1.2 | leader_follower | narrow_weak | 3.0 | 0.5 | 22 | 22 | 0.000 |
| parallel | 1.2 | leader_follower | narrow_strong | 3.0 | 2.0 | 22 | 22 | 0.000 |
| parallel | 1.2 | leader_follower | broad_weak | 8.0 | 0.5 | 22 | 22 | 0.000 |
| parallel | 1.2 | leader_follower | broad_strong | 8.0 | 2.0 | 22 | 6 | 0.727 |
| parallel | 1.2 | leader_follower | wide_weak | 14.0 | 0.5 | 22 | 22 | 0.000 |
| parallel | 1.2 | leader_follower | wide_strong | 14.0 | 2.0 | 22 | 6 | 0.727 |
| crossing | 0.8 | rigid_line_ahead | narrow_weak | 3.0 | 0.5 | 10 | 10 | 0.000 |
| crossing | 0.8 | rigid_line_ahead | narrow_strong | 3.0 | 2.0 | 10 | 10 | 0.000 |
| crossing | 0.8 | rigid_line_ahead | broad_weak | 8.0 | 0.5 | 10 | 10 | 0.000 |
| crossing | 0.8 | rigid_line_ahead | broad_strong | 8.0 | 2.0 | 10 | 10 | 0.000 |
| crossing | 0.8 | rigid_line_ahead | wide_weak | 14.0 | 0.5 | 10 | 10 | 0.000 |
| crossing | 0.8 | rigid_line_ahead | wide_strong | 14.0 | 2.0 | 10 | 10 | 0.000 |
| crossing | 0.8 | leader_follower | narrow_weak | 3.0 | 0.5 | 6 | 6 | 0.000 |
| crossing | 0.8 | leader_follower | narrow_strong | 3.0 | 2.0 | 6 | 6 | 0.000 |
| crossing | 0.8 | leader_follower | broad_weak | 8.0 | 0.5 | 6 | 6 | 0.000 |
| crossing | 0.8 | leader_follower | broad_strong | 8.0 | 2.0 | 6 | 0 | 1.000 |
| crossing | 0.8 | leader_follower | wide_weak | 14.0 | 0.5 | 6 | 6 | 0.000 |
| crossing | 0.8 | leader_follower | wide_strong | 14.0 | 2.0 | 6 | 0 | 1.000 |

## Mechanism check

| model | coverage effect | intensity effect |
|---|---|---|
| rigid_line_ahead | +0.0000 | +0.0000 |
| leader_follower | +0.2500 | +0.6667 |

Representations agree on the sign pattern: **False**