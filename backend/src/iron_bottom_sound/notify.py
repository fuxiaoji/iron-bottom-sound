"""科研同意通知（可插拔渠道，当前为 Server酱 / 微信推送）。

env（服务器 /etc/tiedi.env 注入，绝不落仓库）：
    IBS_NOTIFY_CHANNEL          = serverchan | none（默认 none，仅落库不推送）
    IBS_NOTIFY_SERVERCHAN_KEY   = Server酱 SendKey（sctapi.ftqq.com/<key>.send）

纪律：
    - 通知失败绝不影响对局/建局：所有异常吞掉、返回 False。
    - 内容只含公开元数据（局号/想定/是否同意/称呼），绝不携带订单、损伤或密钥。
    - 加新渠道：仿 _serverchan 实现一个 sender，再在 notify_research_consent 按
      IBS_NOTIFY_CHANNEL 分发即可。
"""
from __future__ import annotations

import os

import httpx

_SERVERCHAN_ENDPOINT = "https://sctapi.ftqq.com/{key}.send"
_DEFAULT_TITLE = "铁底湾：新的科研用途同意"


def notify_research_consent(
    game_id: str,
    allow: bool,
    handle: str | None,
    scenario: str,
) -> bool:
    """按配置渠道推送一条科研同意消息；未配置/失败都返回 False，绝不抛异常。"""
    channel = os.environ.get("IBS_NOTIFY_CHANNEL", "none").strip().lower()
    if channel == "serverchan":
        key = os.environ.get("IBS_NOTIFY_SERVERCHAN_KEY", "").strip()
        if key:
            return _serverchan(key, game_id, allow, handle, scenario)
    return False


def _serverchan(key: str, game_id: str, allow: bool, handle: str | None, scenario: str) -> bool:
    consent = "已同意（可留档用于科研）" if allow else "未同意"
    lines = [
        f"想定：{scenario}",
        f"对局：{game_id}",
        f"科研同意：{consent}",
    ]
    if handle:
        lines.append(f"称呼：{handle}")
    desp = "  \n".join(lines)
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                _SERVERCHAN_ENDPOINT.format(key=key),
                data={"title": _DEFAULT_TITLE, "desp": desp, "short": desp[:32]},
            )
            response.raise_for_status()
            body = response.json()
            return bool(body.get("code") == 0)
    except Exception:
        return False
