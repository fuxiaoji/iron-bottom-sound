export const REALISTIC_AI_PROFILES = [
  { id: "rc_coordinated", label: "协同舰队", intro: "炮战抢 T 头、侧翼雷击与友军掩护", group: "真实模式 AI", win: "状态机" },
  { id: "rc_t_hunter", label: "T 头猎手", intro: "主力横切敌舰首，轻舰牵制与雷击", group: "真实模式 AI", win: "状态机" },
  { id: "rc_torpedo_wings", label: "雷击双翼", intro: "两翼交叉雷道，主力接应并让出发射通道", group: "真实模式 AI", win: "状态机" },
  { id: "rc_screen", label: "护航屏卫", intro: "保护主力与受损友舰，优先避雷与错峰航路", group: "真实模式 AI", win: "状态机" },
  { id: "rc_pincer", label: "分进合击", intro: "不同编队分占两侧阵位，炮火配合鱼雷切割", group: "真实模式 AI", win: "状态机" },
] as const;
