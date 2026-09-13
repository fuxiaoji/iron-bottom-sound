# v10 Phase 4: reposition-cost sensitivity

| severity | model | C_reposition (mean over cells) |
|---|---|---|
| gentle | rigid_line_ahead | +0.283 |
| medium | rigid_line_ahead | -0.836 |
| tight | rigid_line_ahead | +2.688 |
| gentle | leader_follower | -0.996 |
| medium | leader_follower | -0.964 |
| tight | leader_follower | -2.686 |

Qualitative trend preserved: **False**

| severity | geometry | eta_r | model | J_man | J_hold | C_reposit | path len | heading disp | min range |
|---|---|---|---|---|---|---|---|---|---|
| gentle | head_on | 1.0 | rigid_line_ahead | -2.383 | +0.000 | -2.383 | 30.0 | 0.0 | 2.8 |
| gentle | head_on | 1.0 | leader_follower | -5.440 | +0.000 | -5.440 | 30.0 | 10.0 | 1.9 |
| gentle | parallel | 1.2 | rigid_line_ahead | +14.571 | +13.126 | +1.445 | 30.0 | 0.0 | 5.7 |
| gentle | parallel | 1.2 | leader_follower | +12.068 | +13.126 | -1.057 | 30.0 | 10.0 | 6.6 |
| gentle | crossing | 0.8 | rigid_line_ahead | -1.609 | -3.396 | +1.788 | 30.0 | 0.0 | 9.3 |
| gentle | crossing | 0.8 | leader_follower | +0.112 | -3.396 | +3.508 | 30.0 | 10.0 | 10.1 |
| medium | head_on | 1.0 | rigid_line_ahead | -5.658 | +0.000 | -5.658 | 30.0 | 0.0 | 5.1 |
| medium | head_on | 1.0 | leader_follower | -6.355 | +0.000 | -6.355 | 29.9 | 20.0 | 3.7 |
| medium | parallel | 1.2 | rigid_line_ahead | +18.738 | +13.126 | +5.612 | 30.0 | 0.0 | 1.7 |
| medium | parallel | 1.2 | leader_follower | +14.583 | +13.126 | +1.457 | 29.9 | 20.0 | 2.3 |
| medium | crossing | 0.8 | rigid_line_ahead | -5.859 | -3.396 | -2.463 | 30.0 | 0.0 | 6.5 |
| medium | crossing | 0.8 | leader_follower | -1.389 | -3.396 | +2.007 | 29.9 | 20.0 | 8.2 |
| tight | head_on | 1.0 | rigid_line_ahead | -6.748 | +0.000 | -6.748 | 30.0 | 0.0 | 6.9 |
| tight | head_on | 1.0 | leader_follower | -9.780 | +0.000 | -9.780 | 29.7 | 30.0 | 5.0 |
| tight | parallel | 1.2 | rigid_line_ahead | +24.535 | +13.126 | +11.409 | 30.0 | 0.0 | 5.0 |
| tight | parallel | 1.2 | leader_follower | +15.624 | +13.126 | +2.498 | 29.7 | 30.0 | 4.0 |
| tight | crossing | 0.8 | rigid_line_ahead | +0.005 | -3.396 | +3.401 | 30.0 | 0.0 | 2.8 |
| tight | crossing | 0.8 | leader_follower | -4.172 | -3.396 | -0.776 | 29.7 | 30.0 | 5.2 |