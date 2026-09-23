"""The fleet commander's own agent (IBS-R-CD-09).

Why this is a separate level and not a bigger formation agent
------------------------------------------------------------
A formation commander decides for the ships it can see.  The fleet commander decides
for formations it mostly *cannot* see: its own picture is its embarked formation's
contacts plus whatever reports have actually been delivered to it - and those arrive
late.  That is a different job with a different input shape, so it gets its own prompt,
its own parser and its own memory key rather than a widened formation prompt.

What the commander may do
-------------------------
* issue a natural-language order to any of its formations (``orders``);
* acknowledge a delivered report by name (``acknowledged_formations``), which sends a
  short acknowledgement back down the same slow channel;
* or explicitly decline to issue anything this turn (``no_order``) - a commander that
  must speak every turn is a commander that micromanages.

What it may not do is unchanged from the formation level: no mounts, no firing
solutions, no per-ship movement.  Priorities only travel as bounded weights.

An order to the formation the commander is embarked in is handed over in person and
therefore carries no signal delay; every other order is a message and is routed,
queued and delayed like any other traffic (see ``command_delay.draft_natural_order``).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .formation_llm import chat_completion, _strip_fence
from .models import Phase

FLEET_RESPONSE_SCHEMA: dict[str, Any] = {
    "orders": [
        {
            "formation_id": "one of addressable_formations",
            "text": "自然语言命令（≤1000 字）",
            "priority_classes": ["可选：目标类型优先级，如 CA/CL/DD"],
            "deadline_turn": "可选：整数回合数",
        }
    ],
    "acknowledged_formations": ["可选：本回合要回复确认的编队 id"],
    "no_order": "true 表示本回合不下新命令（保持现状）",
    "rationale_summary": "你的判断依据，一句话",
    "memory_note": "可选：写给自己下一回合的备忘",
}

FLEET_INSTRUCTION = (
    "你是舰队总指挥。你只能看到自己所在编队的目视接触，其他编队的情况全部来自它们经电报发回的"
    "报告，而报告会因距离与转译延迟——所以你手里的态势是陈旧的，必须在命令里给下级留出判断余地。"
    "你用自然语言给编队下令，命令会经电报投递；给本队（你自己所在编队）的命令是当面下达、即刻生效，"
    "给其他编队的命令需要时间。你可以本回合不下令。"
    "你不得指定炮位、射界、射击解或具体命中计算，只能指定目标类型优先级；也不得直接指挥单舰机动。"
    "你给任何编队下令都可以：给自己所在的编队下令是当面交办、本回合即生效；给其他编队下令要经电报，"
    "会晚到，因此命令要留给下级判断余地，别把话写死。"
    "输出必须是严格 JSON，字段见 response_schema。"
)


class FleetOrder(BaseModel):
    """One natural-language order from the fleet commander to one formation."""

    formation_id: str
    text: str
    priority_classes: list[str] = Field(default_factory=list)
    deadline_turn: int | None = None


class FleetDecision(BaseModel):
    """What the fleet commander decided this turn, with its own reasoning kept."""

    side: str
    turn: int
    phase: Phase
    orders: list[FleetOrder] = Field(default_factory=list)
    acknowledged_formations: list[str] = Field(default_factory=list)
    no_order: bool = False
    rationale_summary: str = ""
    memory_note: str = ""
    audit: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class FleetPolicy(Protocol):
    """A callable that turns a fleet prompt into the model's raw reply."""

    def __call__(self, prompt: dict[str, Any]) -> str: ...


class FleetProviderPolicy:
    """A real model call for the fleet level, OpenAI-compatible.

    Deliberately *not* ``ProviderPolicy``: that one whitelists formation prompt keys,
    so it would silently drop exactly the fields the fleet prompt consists of
    (``reports_on_your_formations``, ``your_embarked_formation``, ``addressable_formations``)
    and hand the model a formation-shaped null prompt.
    """

    def __init__(
        self, *, endpoint: str, model: str, api_key: str, timeout: float = 90.0,
        max_tokens: int = 2000, supports_thinking: bool = False,
        thinking_enabled: bool = False, client: Any = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.supports_thinking = supports_thinking
        self.thinking_enabled = thinking_enabled
        self.client = client
        self.label = f"llm-fleet:{model}"
        self.last_meta: dict[str, Any] = {}

    def _payload(self, prompt: dict[str, Any]) -> dict[str, Any]:
        import json

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": FLEET_INSTRUCTION},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False,
                                                      default=str)},
            ],
        }
        if self.supports_thinking:
            payload["thinking"] = {
                "type": "enabled" if self.thinking_enabled else "disabled"
            }
        return payload

    def __call__(self, prompt: dict[str, Any]) -> str:
        content, self.last_meta = chat_completion(
            endpoint=self.endpoint, api_key=self.api_key, model=self.model,
            payload=self._payload(prompt), timeout=self.timeout, client=self.client,
        )
        if not content and self.last_meta.get("reasoning_content"):
            raise ValueError(
                "fleet provider returned reasoning only (finish_reason="
                f"{self.last_meta['finish_reason']}); no order to parse"
            )
        return _strip_fence(content)


def make_fleet_policy(
    *, provider: str, model: str | None = None, api_key: str | None = None,
    timeout: float = 90.0, max_tokens: int = 2000, client: Any = None,
    thinking: bool = False,
) -> tuple[FleetProviderPolicy | None, str]:
    """Same bargain as ``formation_llm.make_policy``: a policy, or the reason there is none."""
    import os

    from .llm_providers import provider_runtime

    runtime = provider_runtime(provider, model)  # type: ignore[arg-type]
    key = api_key or os.environ.get(runtime.api_key_env, "")
    if not key:
        return None, f"no API key for {runtime.provider} (env {runtime.api_key_env})"
    return FleetProviderPolicy(
        endpoint=runtime.endpoint, model=runtime.model, api_key=key, timeout=timeout,
        max_tokens=max_tokens, supports_thinking=runtime.supports_thinking,
        thinking_enabled=thinking, client=client,
    ), f"llm-fleet:{runtime.provider}/{runtime.model}"


def build_fleet_prompt(
    state, side, *, view, memory_text: str, addressable: list[dict[str, Any]],
    task: str | None = None,
) -> dict[str, Any]:
    """The material the fleet commander is entitled to, and nothing else.

    Everything except its own embarked formation's contacts arrives as a *report with
    an age*, because that is exactly what the commander has: no side plot, no live
    positions of formations it has not heard from.
    """
    return {
        "instruction": FLEET_INSTRUCTION,
        "response_schema": FLEET_RESPONSE_SCHEMA,
        "role": "fleet_commander",
        "side": side.value,
        "turn": state.turn,
        "phase": state.phase.value,
        # Dumped to plain JSON here: the transport is `json.dumps`, and a pydantic
        # model in the tree would fail at request time rather than at build time.
        "your_embarked_formation": view.embarked,
        "reports_on_your_formations": [
            row.model_dump(mode="json") for row in view.reports
        ],
        "contacts_seen_by_your_embarked_formation": view.contacts,
        "addressable_formations": addressable,
        "your_memory": memory_text,
        "task": task or (
            "给需要新命令的编队下达自然语言命令（addressable_formations 里每个编队都标了送达方式）；"
            "没有必要时可 no_order=true。只能指派目标类型优先级，不得指定炮位或射击解。"
        ),
    }


def parse_fleet_response(
    raw: str, *, side, turn: int, phase: Phase, addressable_ids: set[str],
) -> tuple[FleetDecision | None, list[str]]:
    """Strict validation, same discipline as the formation parser: reject, don't repair."""
    import json

    errors: list[str] = []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as error:
        return None, [f"response is not valid JSON: {error}"]
    if not isinstance(data, dict):
        return None, ["response is not a JSON object"]

    forbidden = sorted(
        {"gunnery", "gunnery_orders", "mounts", "mount_ids", "mount_allocation",
         "firing_solution", "hit_modifier", "expected_hits", "movement_commands",
         "ship_movements", "movement_plan"} & set(data)
    )
    if forbidden:
        errors.append("forbidden fields: " + ", ".join(forbidden))

    raw_orders = data.get("orders") or []
    if not isinstance(raw_orders, list):
        errors.append("orders must be a list")
        raw_orders = []
    orders: list[FleetOrder] = []
    for item in raw_orders:
        if not isinstance(item, dict):
            errors.append("each order must be an object")
            continue
        formation_id = str(item.get("formation_id") or "")
        text = " ".join(str(item.get("text") or "").split())
        if formation_id not in addressable_ids:
            errors.append(f"{formation_id!r} is not an addressable formation")
            continue
        if not text:
            errors.append(f"order to {formation_id} has no text")
            continue
        classes = item.get("priority_classes") or []
        if not isinstance(classes, list):
            errors.append("priority_classes must be a list")
            classes = []
        deadline = item.get("deadline_turn")
        if deadline is not None and not isinstance(deadline, int):
            errors.append("deadline_turn must be an integer")
            deadline = None
        orders.append(FleetOrder(
            formation_id=formation_id, text=text[:1000],
            priority_classes=[str(name)[:8] for name in classes][:6],
            deadline_turn=deadline,
        ))
    seen: set[str] = set()
    duplicates = [order.formation_id for order in orders if
                  (order.formation_id in seen or seen.add(order.formation_id))]
    if duplicates:
        errors.append("more than one order to: " + ", ".join(sorted(set(duplicates))))

    acked = data.get("acknowledged_formations") or []
    if not isinstance(acked, list):
        errors.append("acknowledged_formations must be a list")
        acked = []
    unknown_acks = sorted(str(item) for item in acked if str(item) not in addressable_ids)
    if unknown_acks:
        errors.append("cannot acknowledge unknown formations: " + ", ".join(unknown_acks))

    note = data.get("memory_note")
    if note is not None and not isinstance(note, str):
        errors.append("memory_note must be a string")
        note = None

    no_order = bool(data.get("no_order"))
    if errors:
        return None, errors
    return FleetDecision(
        side=side.value if hasattr(side, "value") else str(side),
        turn=turn, phase=phase, orders=orders,
        acknowledged_formations=sorted({str(item) for item in acked}),
        no_order=no_order,
        rationale_summary=str(data.get("rationale_summary") or "")[:600],
        memory_note=str(note or "")[:400],
        audit={"parsed": True, "addressable": len(addressable_ids)},
    ), []


class FleetLLMAgent:
    """A fleet policy with retries, honest fallback and the reasoning kept."""

    def __init__(self, policy: FleetPolicy, *, name: str = "fleet-llm-v1",
                 max_retries: int = 2) -> None:
        self.policy = policy
        self.name = name
        self.max_retries = max_retries
        self.attempts: list[dict[str, Any]] = []

    def act(self, prompt: dict[str, Any], *, side, turn: int, phase: Phase,
            addressable_ids: set[str]) -> FleetDecision:
        last_errors: list[str] = []
        for attempt in range(1, self.max_retries + 2):
            retry_prompt = prompt
            if last_errors:
                retry_prompt = {
                    **prompt,
                    "previous_response_rejected": last_errors,
                    "instruction": FLEET_INSTRUCTION + " 上一次回复被拒绝：" + "；".join(last_errors),
                }
            raw = self.policy(retry_prompt)
            meta = getattr(self.policy, "last_meta", None) or {}
            decision, errors = parse_fleet_response(
                raw, side=side, turn=turn, phase=phase, addressable_ids=addressable_ids,
            )
            self.attempts.append({
                "attempt": attempt, "prompt": retry_prompt, "raw_response": raw,
                "thinking": str(meta.get("reasoning_content") or ""),
                "usage": meta.get("usage") or {}, "request_id": meta.get("request_id"),
                "finish_reason": meta.get("finish_reason"),
                "errors": list(errors), "accepted": decision is not None,
            })
            if decision is not None:
                return decision
            last_errors = errors
        # Standing down is the honest fallback: no order was issued, and the record says so.
        self.attempts[-1]["fallback"] = True
        return FleetDecision(
            side=side.value if hasattr(side, "value") else str(side),
            turn=turn, phase=phase, orders=[], acknowledged_formations=[],
            no_order=True,
            rationale_summary="模型回复全部被拒绝，本回合不下令（保持现状）。",
            audit={"parsed": False, "llm_fallback": True, "llm_errors": last_errors,
                   "llm_attempts": self.max_retries + 1},
        )
