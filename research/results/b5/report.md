# B5 nonholonomic reposition cost (v2, refined)

Scenario: R 16 hex ahead on a shared course, d_perp lateral;
B: 90-deg turn out toward the flank line, run as needed, turn
back, hold abeam.  C = J_stay - J_maneuver (discounted, T=24).

## v1 artifact diagnosis
- v1 placed R at (d_perp, -16) on a +x course: d_perp was
  longitudinal, so d = 2/4/6 only moved range 16.1 -> 17.1 hex.
- v1 turned B away from R: range left the 24-hex kernel clip by
  t=3; the only d-sensitivity was the |delta|>=150 end-on flip,
  which fired for d<=6 but not d=8 -> the single 0.258-vs-0 step.
- v1 coupling was a no-op: round(30/60)=0 pulses on every turn,
  so engine_coupled == independent to machine precision.

## Results

| d | coupling | eta_v | T_repos | head.exc | path | min r | L>0 | J_stay | J_man | C |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | independent | 0.8 | 0 | 180 | 115.2 | 16.0 | 4 | +4.099 | +1.290 | +2.810 |
| 1 | independent | 0.8 | 1 | 180 | 115.2 | 16.0 | 5 | +4.097 | +1.559 | +2.537 |
| 2 | independent | 0.8 | 1 | 180 | 115.2 | 16.1 | 5 | +4.089 | +1.566 | +2.523 |
| 3 | independent | 0.8 | 2 | 180 | 115.2 | 16.3 | 24 | +4.077 | +3.453 | +0.624 |
| 4 | independent | 0.8 | 2 | 180 | 115.2 | 16.5 | 24 | +4.061 | +3.456 | +0.605 |
| 5 | independent | 0.8 | 2 | 180 | 115.2 | 16.8 | 24 | +4.039 | +3.456 | +0.583 |
| 6 | independent | 0.8 | 2 | 180 | 115.2 | 17.0 | 24 | +4.014 | +3.455 | +0.559 |
| 7 | independent | 0.8 | 3 | 180 | 115.2 | 17.3 | 24 | +3.986 | +3.452 | +0.534 |
| 8 | independent | 0.8 | 3 | 180 | 115.2 | 17.6 | 24 | +3.955 | +3.448 | +0.507 |
| 9 | independent | 0.8 | 3 | 180 | 115.2 | 17.9 | 24 | +3.917 | +3.441 | +0.475 |
| 10 | independent | 0.8 | 3 | 180 | 115.2 | 18.3 | 23 | +0.000 | +3.185 | -3.185 |
| 0 | engine_coupled | 0.8 | 0 | 180 | 110.4 | 16.0 | 24 | +4.099 | +3.546 | +0.553 |
| 1 | engine_coupled | 0.8 | 1 | 180 | 110.4 | 16.0 | 24 | +4.097 | +3.564 | +0.532 |
| 2 | engine_coupled | 0.8 | 1 | 180 | 110.4 | 16.1 | 24 | +4.089 | +3.397 | +0.693 |
| 3 | engine_coupled | 0.8 | 2 | 180 | 110.4 | 16.3 | 24 | +4.077 | +3.407 | +0.670 |
| 4 | engine_coupled | 0.8 | 2 | 180 | 110.4 | 16.5 | 24 | +4.061 | +3.414 | +0.646 |
| 5 | engine_coupled | 0.8 | 2 | 180 | 110.4 | 16.8 | 24 | +4.039 | +3.416 | +0.624 |
| 6 | engine_coupled | 0.8 | 3 | 180 | 110.4 | 17.1 | 24 | +4.014 | +3.413 | +0.601 |
| 7 | engine_coupled | 0.8 | 3 | 180 | 110.4 | 17.5 | 24 | +3.986 | +3.406 | +0.580 |
| 8 | engine_coupled | 0.8 | 3 | 180 | 110.4 | 17.9 | 24 | +3.955 | +3.394 | +0.561 |
| 9 | engine_coupled | 0.8 | 3 | 180 | 110.4 | 18.4 | 24 | +3.917 | +3.378 | +0.539 |
| 10 | engine_coupled | 0.8 | 4 | 180 | 110.4 | 18.9 | 23 | +0.000 | +3.112 | -3.112 |
| 0 | independent | 1.0 | 0 | 180 | 144.0 | 16.0 | 4 | +4.099 | +1.222 | +2.877 |
| 1 | independent | 1.0 | 1 | 180 | 144.0 | 16.0 | 4 | +4.097 | +1.226 | +2.871 |
| 2 | independent | 1.0 | 1 | 180 | 144.0 | 16.1 | 4 | +4.089 | +1.244 | +2.846 |
| 3 | independent | 1.0 | 1 | 180 | 144.0 | 16.3 | 5 | +4.077 | +1.318 | +2.759 |
| 4 | independent | 1.0 | 2 | 180 | 144.0 | 16.5 | 5 | +4.061 | +1.336 | +2.724 |
| 5 | independent | 1.0 | 2 | 180 | 144.0 | 16.8 | 5 | +4.039 | +1.350 | +2.689 |
| 6 | independent | 1.0 | 2 | 180 | 144.0 | 17.1 | 24 | +4.014 | +3.434 | +0.580 |
| 7 | independent | 1.0 | 2 | 180 | 144.0 | 17.3 | 24 | +3.986 | +3.433 | +0.553 |
| 8 | independent | 1.0 | 2 | 180 | 144.0 | 17.5 | 24 | +3.955 | +3.431 | +0.524 |
| 9 | independent | 1.0 | 3 | 180 | 144.0 | 17.8 | 24 | +3.917 | +3.427 | +0.490 |
| 10 | independent | 1.0 | 3 | 180 | 144.0 | 18.2 | 23 | +0.000 | +3.172 | -3.172 |
| 0 | engine_coupled | 1.0 | 0 | 180 | 138.0 | 16.0 | 24 | +4.099 | +3.528 | +0.572 |
| 1 | engine_coupled | 1.0 | 1 | 180 | 138.0 | 16.0 | 24 | +4.097 | +3.530 | +0.567 |
| 2 | engine_coupled | 1.0 | 1 | 180 | 138.0 | 16.1 | 24 | +4.089 | +3.531 | +0.558 |
| 3 | engine_coupled | 1.0 | 2 | 180 | 138.0 | 16.3 | 24 | +4.077 | +3.356 | +0.721 |
| 4 | engine_coupled | 1.0 | 2 | 180 | 138.0 | 16.5 | 24 | +4.061 | +3.355 | +0.705 |
| 5 | engine_coupled | 1.0 | 2 | 180 | 138.0 | 16.8 | 24 | +4.039 | +3.353 | +0.686 |
| 6 | engine_coupled | 1.0 | 2 | 180 | 138.0 | 17.1 | 24 | +4.014 | +3.351 | +0.663 |
| 7 | engine_coupled | 1.0 | 3 | 180 | 138.0 | 17.5 | 24 | +3.986 | +3.348 | +0.638 |
| 8 | engine_coupled | 1.0 | 3 | 180 | 138.0 | 17.9 | 24 | +3.955 | +3.345 | +0.611 |
| 9 | engine_coupled | 1.0 | 3 | 180 | 138.0 | 18.4 | 24 | +3.917 | +3.340 | +0.576 |
| 10 | engine_coupled | 1.0 | 3 | 180 | 138.0 | 18.9 | 23 | +0.000 | +3.088 | -3.088 |
| 0 | independent | 1.25 | 0 | 180 | 180.0 | 16.0 | 3 | +4.099 | +0.956 | +3.144 |
| 1 | independent | 1.25 | 1 | 180 | 180.0 | 16.0 | 3 | +4.097 | +0.960 | +3.137 |
| 2 | independent | 1.25 | 1 | 180 | 180.0 | 16.1 | 4 | +4.089 | +1.221 | +2.869 |
| 3 | independent | 1.25 | 1 | 180 | 180.0 | 16.3 | 4 | +4.077 | +1.222 | +2.856 |
| 4 | independent | 1.25 | 2 | 180 | 180.0 | 16.5 | 4 | +4.061 | +1.034 | +3.027 |
| 5 | independent | 1.25 | 2 | 180 | 180.0 | 16.8 | 4 | +4.039 | +1.032 | +3.007 |
| 6 | independent | 1.25 | 2 | 180 | 180.0 | 17.1 | 5 | +4.014 | +1.278 | +2.736 |
| 7 | independent | 1.25 | 2 | 180 | 180.0 | 17.3 | 5 | +3.986 | +1.275 | +2.711 |
| 8 | independent | 1.25 | 2 | 180 | 180.0 | 17.5 | 5 | +3.955 | +1.281 | +2.675 |
| 9 | independent | 1.25 | 2 | 180 | 180.0 | 17.8 | 24 | +3.917 | +3.359 | +0.557 |
| 10 | independent | 1.25 | 2 | 180 | 180.0 | 18.1 | 23 | +0.000 | +3.110 | -3.110 |
| 0 | engine_coupled | 1.25 | 0 | 180 | 172.5 | 16.0 | 4 | +4.099 | +1.190 | +2.909 |
| 1 | engine_coupled | 1.25 | 1 | 180 | 172.5 | 16.0 | 5 | +4.097 | +1.441 | +2.655 |
| 2 | engine_coupled | 1.25 | 1 | 180 | 172.5 | 16.1 | 23 | +4.089 | +3.282 | +0.807 |
| 3 | engine_coupled | 1.25 | 1 | 180 | 172.5 | 16.3 | 24 | +4.077 | +3.520 | +0.557 |
| 4 | engine_coupled | 1.25 | 2 | 180 | 172.5 | 16.5 | 24 | +4.061 | +3.353 | +0.707 |
| 5 | engine_coupled | 1.25 | 2 | 180 | 172.5 | 16.8 | 24 | +4.039 | +3.351 | +0.688 |
| 6 | engine_coupled | 1.25 | 2 | 180 | 172.5 | 17.1 | 24 | +4.014 | +3.349 | +0.665 |
| 7 | engine_coupled | 1.25 | 2 | 180 | 172.5 | 17.5 | 24 | +3.986 | +3.346 | +0.640 |
| 8 | engine_coupled | 1.25 | 2 | 180 | 172.5 | 17.9 | 24 | +3.955 | +3.343 | +0.612 |
| 9 | engine_coupled | 1.25 | 3 | 180 | 172.5 | 18.4 | 24 | +3.917 | +3.339 | +0.577 |
| 10 | engine_coupled | 1.25 | 3 | 180 | 172.5 | 18.9 | 23 | +0.000 | +3.087 | -3.087 |

## Platform-effect check
- flat (d-independent) series: 0/6
- verdict: PLATFORM EFFECT GONE: C_reposition now varies with d_perp (v1 flatness was an artifact)
  - eta_v=0.8 independent: 11 distinct C values, spread=5.9945, flat=False
  - eta_v=0.8 engine_coupled: 11 distinct C values, spread=3.8050, flat=False
  - eta_v=1.0 independent: 11 distinct C values, spread=6.0497, flat=False
  - eta_v=1.0 engine_coupled: 11 distinct C values, spread=3.8085, flat=False
  - eta_v=1.25 independent: 11 distinct C values, spread=6.2531, flat=False
  - eta_v=1.25 engine_coupled: 11 distinct C values, spread=5.9955, flat=False
