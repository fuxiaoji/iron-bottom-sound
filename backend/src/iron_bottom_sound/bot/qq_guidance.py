"""Chinese QQ command guidance built only from approved match metadata.

This module describes existing commands and phases. It does not select orders,
inspect observations or make any game-state changes.
"""
from __future__ import annotations

import re


_PHASES = {
    "formation_setup": ("编队部署", "为本方舰船确定初始编队与部署。"),
    "contact_setup": ("接触部署", "按当前想定完成本方接触部署。"),
    "reinforcement": ("增援", "检查本阶段的增援或确认要求。"),
    "movement_planning": ("机动规划", "安排本方本回合的移动方案。"),
    "torpedo_planning": ("鱼雷规划", "安排本方鱼雷方案；可用行动以引擎返回为准。"),
    "movement_resolution": ("机动结算", "引擎自动结算移动，无需发送行动。"),
    "gunnery": ("炮击", "安排本方炮击与本阶段可用行动。"),
    "torpedo_effects": ("鱼雷效果结算", "引擎自动结算鱼雷效果，无需发送行动。"),
    "fire_end": ("火灾与回合结束", "引擎自动结算火灾与回合结束，无需发送行动。"),
    # Aliases are presentation compatibility only, not additional engine phases.
    "torpedo_resolution": ("鱼雷效果结算", "引擎自动结算鱼雷效果，无需发送行动。"),
    "fire_spread": ("火灾与回合结束", "引擎自动结算火灾与回合结束，无需发送行动。"),
    "complete": ("对局结束", "本局已结束，可查看最终态势与公共战况。"),
}
_AUTOMATIC = {"movement_resolution", "torpedo_effects", "fire_end", "torpedo_resolution", "fire_spread"}
_SIDES = {"allies": "盟军", "axis": "日军"}


def _match(value: dict) -> str:
    identifier = value.get("match_id")
    return identifier if isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier) else ""


def _number(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _query(command: str, match: str) -> str:
    return "/" + command + (" " + match if match else "")


def help_text(scope: str, topic: str = "") -> str:
    """Return a short entry guide or one focused topic, without account data."""
    topic = topic.strip().lstrip("/").lower()
    sections = {
        "快速开始": """铁底湾｜快速开始
1. 群里真实 @机器人，发送：
/创建 编队pve
也可用预设 /编队人机、/普通人机；/编队对战、/普通对战用于PVP。PVE对手是离线状态机，不是LLM。
2. 按建局回复完成私聊绑定：私聊申请验证码，再由本人回群 @机器人确认。
3. 绑定后私聊发送 /下一步，查看当前阶段和可复制的推进命令。
4. 私聊 /态势 查看本方图；群里 @机器人 /战况 对局ID 查看公共图。
斜杠可以手打；群里仍须真正 @机器人。多局时用 /我的对局 查编号，再发 /下一步 对局ID。""",
        "推进": """铁底湾｜怎么推进
先私聊 /下一步，机器人会说明当前阶段、版本和下一条命令。
想让状态机代填本阶段方案：复制回复中的 /自动 版本号 对局ID。
例如当前显示“版本1”，只有一局时可发送 /自动 1；多局时必须加对局ID。成功后用新回复里的版本继续，不能一直重复旧版本。
“自动”只提交本方一个决策阶段；PVE会同时处理状态机对手，PVP要等双方都提交。
一个回合包含多个阶段：增援→机动规划→鱼雷规划→炮击，期间自动结算移动、鱼雷效果和回合结束；编队局开头还需部署。只推进一个阶段，回合数可能不变。
/态势、/下一步、/行动、/建议 都不会提交命令；不带版本号的 /自动 也只显示引导。
若提示版本过期，先 /态势；若提示已封存，等待对手并查询更新；没收到回复也先查态势，不盲目重复提交。""",
        "手动": """铁底湾｜自己下令
1. 私聊 /态势 看当前阶段、版本和本方图。
2. /行动 查看合法行动与订单结构；内容过长时用 /行动 对局ID 舰ID 缩小范围，或通过MCP读取完整结果。
3. /建议 只查看离线状态机建议，不会自动提交。
4. 编辑订单后发送 /提交 版本号 JSON对象；多局时用 /提交 版本号 对局ID JSON对象。字段以当前合法行动与schema为准。
5. /确认 版本号 表示提交空命令，只有当前引擎认可时才接受；不能把它当作所有阶段都可跳过。
普通模式逐舰下令，编队模式先部署，再按合法行动安排编队方案。版本过期或非法订单会拒绝，先刷新态势再改。
先发 /下一步 即可获得适用于当前阶段的简明提示。""",
        "pvp": """铁底湾｜双人PVP
第一人在群里 @机器人：/创建 编队pvp（或 /创建 普通pvp）。
预设 /编队对战、/普通对战也可以。
第二人在同一群里 @机器人：/加入 对局ID。
双方各自按回复完成私聊绑定，然后分别私聊 /下一步。
双方使用同一个阶段版本，各自提交本方命令；第一方提交后封存并等待，第二方提交后才统一推进。
不要在群里发送本方战术订单。群里的 /战况 对局ID 只给双方共同可见的信息，开局只有地形也正常。
另一方完成后，主动私聊 /态势 查看新阶段；当前没有异步推送保证。""",
        "绑定": """铁底湾｜私聊绑定
先在群里创建或加入对局，取得建局/加入回复中的群openid、对局ID和本方阵营。
私聊发送（替换占位文字，不含尖括号）：
铁底湾 群openid 对局ID 绑定 盟军
日军席位把末尾改成 日军。
拿到私聊验证码后，由该席位本人回对应群，真正 @机器人：
/绑定 验证码
成功后私聊 /我的对局 或 /下一步，后续通常不用反复输入长串群openid。
验证码会过期，过期就重新私聊申请；他人抢发不能代替席位本人确认。不要公开私聊截图或本方订单。""",
    }
    aliases = {"开始": "快速开始", "新手": "快速开始", "下一步": "推进", "自动": "推进", "手动命令": "手动", "双人": "pvp"}
    topic = aliases.get(topic, topic)
    if topic in sections:
        return sections[topic]
    location = "群里请真正 @机器人后发送指令。" if scope == "group" else "已绑定席位后可直接发送下面的短指令。"
    return """铁底湾｜先学会这三步
{location}

① 开一局：群里 @机器人 /创建 编队pve
也可直接选 /编队人机、/普通人机、/编队对战、/普通对战。
可选 普通/编队、pve/pvp；PVE对手为离线状态机，不是LLM。
② 按建局回复完成“私聊申请码→本人回群确认”的绑定。
③ 绑定后私聊 /下一步，按回复中带版本号的命令推进。

最常用指令
私聊 /态势：当前阶段、版本、本方截图，不推进。
私聊 /下一步：解释现在该做什么，并给出可复制命令。
私聊 /自动 版本号：状态机代填并提交本方一个决策阶段。
私聊 /行动、/建议：查看合法动作/方案，不提交。
群里 @机器人 /我的对局：查看自己的对局。
群里 @机器人 /战况 对局ID：公共图；开局仅有地形也正常。

一个回合有多个阶段，推进后回合数可能不变。PVP双方都提交才推进；已封存就等待并主动查态势。
群里发战术命令会提示转私聊，避免泄露本方信息。
多局时先 /我的对局，再用 /下一步 对局ID；复制引导里带对局ID的命令。

详细教程：/帮助 快速开始、/帮助 推进、/帮助 手动、/帮助 PVP、/帮助 绑定。
""".format(location=location).strip()


def status_text(value: dict, *, private: bool = False) -> str:
    """Render only approved match metadata, never a whole service response."""
    match = _match(value)
    phase = value.get("phase")
    name = _PHASES.get(phase, ("未知阶段", ""))[0]
    mode = {"classic": "普通", "formation": "编队"}.get(value.get("mode"), "模式待确认")
    opponent = {"pve": "PVE（状态机）", "pvp": "PVP（双人）"}.get(value.get("opponent"), "对手待确认")
    turn, revision = _number(value.get("turn")), _number(value.get("revision"))
    lines = ["对局 " + (match or "编号待确认") + " · " + mode + " · " + opponent,
             (f"第{turn}回合 · " if turn is not None else "") + name + (f" · 版本{revision}" if revision is not None else "")]
    if private and value.get("side") in _SIDES:
        lines.append("你执" + _SIDES[value["side"]])
    ready = value.get("ready")
    if isinstance(ready, (list, tuple, set)):
        submitted = [_SIDES[side] for side in ("allies", "axis") if side in ready]
        lines.append("已封存：" + ("、".join(submitted) if submitted else "双方均未提交"))
    if value.get("complete") is True or phase == "complete":
        lines.append("本局已结束。")
    elif value.get("started") is False:
        lines.append("等待另一位玩家加入。")
    elif value.get("advanced") is True:
        lines.append("上一阶段已结算，现在是新的待办阶段。")
    return "\n".join(lines)


def next_steps(value: dict, *, private: bool = False) -> str:
    """Explain safe next actions for this seat without executing or suggesting orders."""
    match = _match(value)
    phase = value.get("phase")
    situation, public_map = _query("态势", match), _query("战况", match)
    if value.get("complete") is True or phase == "complete":
        return f"本局已结束，无需继续提交。\n私聊查看最终本方图：{situation}\n群里 @机器人查看公共图：{public_map}"
    if value.get("started") is False:
        return "尚未凑齐双方，暂不能推进。\n请另一位玩家在同一群 @机器人发送：" + _query("加入", match) + "\n加入后各自完成私聊绑定，再查看 /下一步。"
    if not private:
        return f"群里只显示公共战况。\n请私聊机器人发送：{_query('下一步', match)}\n未绑定时先按建局/加入回复完成绑定；群里可查询：{public_map}"
    side, ready = value.get("side"), value.get("ready")
    if side in _SIDES and isinstance(ready, (list, tuple, set)) and side in ready:
        return f"你本阶段的命令已封存，等待对手提交。\n稍后私聊刷新：{situation}\n不要重复提交；双方都完成后才进入下一阶段。"
    explanation = _PHASES.get(phase)
    if explanation is None:
        return f"当前阶段尚无法识别，先刷新态势：{situation}\n请勿直接提交；持续异常时联系管理员。"
    if phase in _AUTOMATIC:
        return explanation[1] + f"\n刷新查看结算结果：{situation}"
    revision = _number(value.get("revision"))
    if revision is None:
        return f"缺少有效版本号，先查看：{situation}\n读取当前版本后再提交。"
    if not match:
        return "缺少有效对局编号，先查看 /我的对局，再发送 /下一步 对局ID。"
    return (f"现在是{explanation[0]}阶段：{explanation[1]}\n"
            f"想先让状态机代填本方方案并提交这一阶段，发送：\n/自动 {revision} {match}\n"
            f"想自己下令：先 /行动 {match} 查看合法动作，/建议 {match} 只看方案；再用 /提交 {revision} {match} JSON对象。\n"
            "只有一局时可省对局ID。提交后按新回复的版本继续；PVP先提交的一方需等对手。只想看图可发 " + situation + "。")
