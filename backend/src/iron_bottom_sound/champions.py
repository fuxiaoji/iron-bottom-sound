"""遗传进化出的 AI 冠军注册表（自包含，服务端/本地端共用）。

与 `tactical.PROFILES`（手调内置风格）并列：`CHAMPIONS` 放**训练产物**——由
`rl/evolve.py` 遗传算法进化 + 冠军复评 + fresh-seed 验证选出的稳健 profile。
值是代码常量（不读 rl/ 文件），生产部署（无 rl/ 包）也能直接用。

现有产物（2026-08-26，`rl/results/ga-dual-med-v1/`）：
- `evolved` —— 全局进化冠军。基因全部偏离手调默认：热点集火（w_enemy_heat 2.51）、
  高撤退（w_retreat 3.0 封顶）、拒绝逼近（w_approach -0.45）、抢胜利点（w_vp 1.36）。
  新鲜 seed 验证：跨想定 combined +0.066，**Elo vs balanced 锚 = +36**（比手调均衡强）。
  风格画像：防守反击型——"看到有人冒火就集火，但绝不主动冲，打两下就跑，占点攒分"。
  注意：S-03 轴心目标达成率 0%（赢多靠默认兜底），盟军 55.6%（真击沉/减速德舰）。

接入点：`match.make_session`（本地引擎）与 `api.ai_opponent`（服务端）都以
`PROFILES | CHAMPIONS` 解析风格名；前端 `App.tsx` 的 `AI_PROFILES` 下拉负责展示。
"""

from .tactical import TacticalProfile

CHAMPIONS: dict[str, TacticalProfile] = {
    # 全局进化冠军（ga-dual-med-v1 冠军复评 + fresh-seed 验证的最优）
    "evolved": TacticalProfile(
        w_enemy_heat=2.509464960655835,
        w_fire_pressure=1.380057980651654,
        w_approach=-0.4487390183097291,
        approach_range=11,
        torpedo_max_range=11,
        torpedo_min_expected=0.2258682601942223,
        top_k_candidates=5,
        w_formation=0.726180459031607,
        formation_spacing=(2, 4),
        line_ahead=0.621274632916855,
        w_predict_opponent=0.3601720003856278,
        retreat_hull_threshold=0.3767145785616175,
        w_retreat=3.0,
        w_protect_own=0.2700538719299829,
        w_vp=1.3610779802829085,
        w_finish=0.6855483244137066,
        w_self_status=0.19255752417376845,
        temperature=0.3612610608405761,
        rng_seed_off=0,
    ),
}

# 冠军元数据（label/简介/胜率快照，供文档与前端标注；胜率取自 rl/style-tourney-final 双想定混战赛）。
# 胜率是**静态快照**：双想定 vs 全内置对手池的综合胜率差分（[-1,+1]，0=五五开）。引擎/阵容变更后会过时。
CHAMPION_INFO: dict[str, dict] = {
    "evolved": {
        "label": "进化冠军",
        "intro": "GA 进化·防守反击型：热点集火 + 高撤退 + 抢胜利点",
        "win": "-0.077",   # 双想定混战赛综合（对内置对手池）
        "source": "rl/results/style-tourney-final（2026-08-26，288 局/风格）",
    },
}
