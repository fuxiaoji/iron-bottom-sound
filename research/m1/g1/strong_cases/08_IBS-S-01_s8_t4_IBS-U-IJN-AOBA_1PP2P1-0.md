# Strong case 8: `IBS-S-01_s8_t4_IBS-U-IJN-AOBA_1PP2P1-0`

- scenario `IBS-S-01`, seed 8, turn 4, phase torpedo_planning
- public observation identical: YES (sha 215df76e55b9924c)
- legal action set identical: YES (sha 23b466b1efcccee6)
- own sealed movement identical: YES (sha 60a18410081a143f)
- axis (hidden) view differs: True

## Hidden axis movement commitment

**Branch A** (what the axis commander actually ordered):
```
  IBS-U-IJN-AOBA               plan='1PP2P1'  <-- CHANGED
  IBS-U-IJN-FURUTAKA           plan='1P4P1'
  IBS-U-IJN-KINUGASA           plan='2P2S1S'
  IBS-U-IJN-HATSUYUKI          plan='1S2S2P'
  IBS-U-IJN-CHITOSE            plan='2'
  IBS-U-IJN-NISSHIN            plan='1P1'
  IBS-U-IJN-ASAGUMO            plan='1S'
  IBS-U-IJN-NATSUGUMO          plan='1S1S'
  IBS-U-IJN-YAMAGUMO           plan='1S1S'
  IBS-U-IJN-SHIRAYUKI          plan='1S1S'
  IBS-U-IJN-MURAKUMO           plan='2S'
  IBS-U-IJN-AKIZUKI            plan='2S'
```

**Branch B** (the alternative legal commitment):
```
  IBS-U-IJN-AOBA               plan='0'  <-- CHANGED
  IBS-U-IJN-FURUTAKA           plan='1P4P1'
  IBS-U-IJN-KINUGASA           plan='2P2S1S'
  IBS-U-IJN-HATSUYUKI          plan='1S2S2P'
  IBS-U-IJN-CHITOSE            plan='2'
  IBS-U-IJN-NISSHIN            plan='1P1'
  IBS-U-IJN-ASAGUMO            plan='1S'
  IBS-U-IJN-NATSUGUMO          plan='1S1S'
  IBS-U-IJN-YAMAGUMO           plan='1S1S'
  IBS-U-IJN-SHIRAYUKI          plan='1S1S'
  IBS-U-IJN-MURAKUMO           plan='2S'
  IBS-U-IJN-AKIZUKI            plan='2S'
```

Differing ship: `IBS-U-IJN-AOBA` (青叶), plan '1PP2P1' ->
'0', distance to nearest allies ship at decision time:
2 hexes.

## Public board at the decision point (identical in both branches; allies view)

Branch A board (byte-render; branch B renders identically because the public
observation hash is equal):
```
    A  B  C  D  E  F  G  H  I  J  K  L  M  N  O  P  Q  R  S  T  U  V  W  X  Y  Z AA BB CC DD EE FF GG HH II JJ KK LL MM NN OO PP QQ RR SS TT
 1 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 2 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 3 .. .. .. .. .. .. .. .. a3 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 4 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. a5 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 5 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 6 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. a2 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 7 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 8 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
 9 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. xx .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
10 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
11 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. e1 .. .. e8* .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
12 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. e7 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
13 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. a1~ .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
14 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
15 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
16 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. e2 .. .. .. .. .. .. .. .. .. .. e6 .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
17 .. .. .. .. a6 a9 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. e4 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
18 .. .. .. .. a7 a10 a12 .. .. .. .. .. .. .. .. .. .. .. e5 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
19 .. .. .. .. a8 a11 a13 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
20 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
21 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. a4* .. .. .. .. .. e3 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
22 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
23 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
24 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
25 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
26 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
27 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
28 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
29 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
30 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
31 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
32 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
33 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
34 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
35 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
36 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
37 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
38 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..
39 .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ..

图例: a1~=青叶(IBS-U-IJN-AOBA) | a2=古鹰(IBS-U-IJN-FURUTAKA) | a3=衣笠(IBS-U-IJN-KINUGASA) | a4*=吹雪(IBS-U-IJN-FUBUKI) | a5=初雪(IBS-U-IJN-HATSUYUKI) | e1=拉菲(IBS-U-USN-LAFFEY) | e2=旧金山(IBS-U-USN-SAN-FRANCISCO) | e3=博伊西(IBS-U-USN-BOISE) | e4=盐湖城(IBS-U-USN-SALT-LAKE-CITY) | e5=海伦娜(IBS-U-USN-HELENA) | e6=布坎南(IBS-U-USN-BUCHANAN) | e7=麦卡拉(IBS-U-USN-MCCALLA) | e8*=邓肯(IBS-U-USN-DUNCAN) | a6=千岁(IBS-U-IJN-CHITOSE) | a7=日进(IBS-U-IJN-NISSHIN) | a8=朝云(IBS-U-IJN-ASAGUMO) | a9=夏云(IBS-U-IJN-NATSUGUMO) | a10=山云(IBS-U-IJN-YAMAGUMO) | a11=白雪(IBS-U-IJN-SHIRAYUKI) | a12=丛云(IBS-U-IJN-MURAKUMO) | a13=秋月(IBS-U-IJN-AKIZUKI) | xx=沉船 | ..=海  残血*  起火~ | 航向:1=东北 2=东南 3=南 4=西南 5=西北 6=北
```

## Q tables (shared candidate set, 6 candidates, 5 dice-stream replicates)

| candidate | Q_outcome A | Q_outcome B | Q_damage A | Q_damage B |
|---|---|---|---|---|
| c0 (0 torpedo) | +0.27 ± 0.11 | +0.27 ± 0.11 | +0.010 ± 0.010 | +0.030 ± 0.010 |
| c1 (3 torpedo) | +0.00 ± 0.00 | +0.20 ± 0.10 | -0.023 ± 0.010 | +0.028 ± 0.007 |
| c2 (1 torpedo) | +0.07 ± 0.06 | +0.00 ± 0.09 | -0.017 ± 0.010 | +0.009 ± 0.011 |
| c3 (1 torpedo) | +0.20 ± 0.10 | +0.20 ± 0.10 | +0.013 ± 0.011 | +0.027 ± 0.007 |
| c4 (1 torpedo) | +0.27 ± 0.11 | +0.60 ± 0.13 | +0.011 ± 0.012 | +0.033 ± 0.011 |
| c5 (1 torpedo) | +0.00 ± 0.00 | +0.53 ± 0.13 | -0.014 ± 0.007 | +0.046 ± 0.011 |

## Regret

- primary (outcome): V_A = +0.27, V_B = +0.60,
  shared-action regret R = 0.000, stake = 0.600,
  **normalized = 0.000**,
  argmax differs = True,
  ranking confident = True
- secondary (damage): normalized = 0.350

## Why the public state cannot distinguish these situations

The allies' observation is hashed identical, so no snapshot-, history- or
belief-free representation that reads only the public state can tell world A
from world B. Yet the two worlds value the shared torpedo candidates
differently, because the enemy ships will be somewhere else when the torpedoes
arrive: the difference lives entirely in the axis sealed movement orders, which
the engine holds in `state.sealed_orders` and never exposes through
`observe()`.
