"""CD-5: the LLM local-agent adapter.

An LLM commands a formation through the *same* protocol as the deterministic
agent: it selects an ``action_id`` from the engine's enumerated list, may name a
contingency branch, may publish **bounded** target-priority adjustments, and may
ask for reports.  It cannot invent a movement program and cannot emit a gunnery
order — not because the prompt asks it not to, but because there is no field for
either and the parser refuses anything that does not match the enumerated set.

What the model is shown
-----------------------
Exactly the v2.2 plan §12 list and nothing else: the formation's local state, its
local map, **its own** local contacts, the active mission order, received
messages, the communication state, stale external reports, the legal action ids,
the legal priority options and the allowed report actions.  No side-global truth
is placed in the prompt, and the prompt is assembled from the observation object
rather than from engine state, so the boundary is enforced by construction.  No
rule formula is included: the model sees options and weight bounds, never a hit
table, a modifier or a mount.

Audit, retry and legality
-------------------------
Every attempt is recorded with the raw response, the parse errors and the final
outcome.  A response is rejected when the action id is not in the legal mask, when
a weight is out of bounds, when a report action is not in the menu, or when it
carries any gunnery key.  Rejection triggers a retry whose prompt states what was
wrong; after the retry budget the adapter falls back to the deterministic agent
and records the fallback, so a game can never stall on a bad model response.

Replay
------
The policy is an injected callable.  A replay passes a recorder/player that
returns the responses captured in the original game, so a whole LLM game is
reproducible without calling a model again — which is what acceptance criterion
10 requires and what keeps the cost at zero.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from . import formation_agents
from .command_observation import (
    LOCAL_PRIORITY_WEIGHT_LIMIT,
    REPORT_ACTIONS,
    FormationObservation,
)
from .formation_agents import (
    DeterministicFormationAgent,
    FormationDecision,
    TargetPriorityAdjustment,
)
from .models import ContingencyBranch, MissionOrder, Phase

# The exact JSON shape the model must produce.  It is published to the model as
# part of the prompt so the contract is explicit rather than inferred.
RESPONSE_SCHEMA: dict[str, Any] = {
    "selected_movement_action_id": "one id from legal_formation_actions, or null to hold",
    "selected_contingency_branch": "one of the active contingency branches, or null",
    "target_priority_adjustments": [
        {"target_id": "a locally sighted contact", "weight": "-0.5..0.5", "reason": "short text"}
    ],
    "report_actions": "subset of the allowed report actions",
    "acknowledgement": "true to acknowledge the mission order",
    "rationale_summary": "one sentence, audit only",
}

INSTRUCTION = (
    "你是编队指挥官。只依据给出的本地情报决策。"
    "机动只能从 legal_formation_actions 里选一个 action_id，不得自创航路。"
    "火力只能通过 target_priority_adjustments 给可见目标附加 -0.5..0.5 的优先级权重；"
    "炮位分配、射界、修正与命中由引擎选择器完成，你不得输出任何炮击命令、炮位、射击解或命中计算。"
    "输出必须是严格的 JSON，字段见 response_schema。"
)


class FormationPolicyCallable(Protocol):
    """A model call: prompt in, raw text out.  Injected, so it is never paid for here."""

    def __call__(self, prompt: dict[str, Any]) -> str:
        ...


class LLMAttempt(BaseModel):
    """One model round trip, kept whether or not it parsed."""

    formation_id: str
    turn: int
    phase: Phase
    attempt: int
    prompt: dict[str, Any]
    raw_response: str = ""
    errors: list[str] = Field(default_factory=list)
    accepted: bool = False
    fallback: bool = False


def build_prompt(
    observation: FormationObservation,
    mission_order: MissionOrder | None = None,
    *,
    contract_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the plan §12 input list.  Nothing from engine state enters here."""
    payload = observation.model_dump(mode="json")
    return {
        "role": "formation_commander",
        # Identity first: it is what an audit log keys on and what a recorded
        # replay uses to serve the right response back.
        "formation_id": observation.formation_id,
        "side": observation.side.value,
        "turn": observation.turn,
        "phase": observation.phase.value,
        "instruction": INSTRUCTION,
        "response_schema": RESPONSE_SCHEMA,
        "formation_state": payload["formation_state"],
        "local_map": payload["local_map"],
        "local_contacts": payload["local_contacts"],
        "active_mission_order": (
            mission_order.model_dump(mode="json") if mission_order is not None else None
        ),
        "received_messages": payload["received_messages"],
        "comm_state": payload["comm_state"],
        "stale_external_reports": payload["stale_external_reports"],
        "legal_formation_actions": payload["legal_formation_actions"],
        "legal_target_priority_options": payload["legal_target_priority_options"],
        "report_actions": payload["report_actions"],
        "priority_weight_limit": payload["local_priority_weight_limit"],
        "contract_state": contract_state or {},
    }


def parse_response(
    response: Any, observation: FormationObservation,
) -> tuple[FormationDecision | None, list[str]]:
    """Strict parse of one model response against the legal masks."""
    errors: list[str] = []
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except ValueError as error:
            return None, [f"response is not valid JSON: {error}"]
    else:
        data = response
    if not isinstance(data, dict):
        return None, ["response must be a JSON object"]
    forbidden = {
        "gunnery", "gunnery_orders", "mounts", "mount_ids", "mount_allocation",
        "firing_solution", "hit_modifier", "expected_hits", "movement_commands",
        "movement_plan",
    }
    present = sorted(forbidden & set(data))
    if present:
        errors.append(
            "the response carries fields a formation commander may not decide: "
            + ", ".join(present)
        )
        return None, errors

    legal_actions = {action["action_id"]: action for action in observation.legal_formation_actions}
    action_id = data.get("selected_movement_action_id")
    plan: str | None = None
    if action_id not in (None, ""):
        if action_id not in legal_actions:
            errors.append(
                f"action id {action_id!r} is not in the legal action list "
                f"({len(legal_actions)} options)"
            )
        else:
            plan = legal_actions[action_id]["plan"]

    branch = data.get("selected_contingency_branch")
    if branch not in (None, "") and branch not in {item.value for item in ContingencyBranch}:
        errors.append(f"unknown contingency branch {branch!r}")

    adjustments: list[TargetPriorityAdjustment] = []
    allowed_targets = {item["target_id"] for item in observation.legal_target_priority_options}
    for raw in data.get("target_priority_adjustments") or []:
        if not isinstance(raw, dict):
            errors.append("each target priority adjustment must be an object")
            continue
        if {"mount_ids", "mounts", "firing_solution", "hit_modifier"} & set(raw):
            errors.append("a priority adjustment may not name mounts or a firing solution")
            continue
        target_id = raw.get("target_id")
        if target_id is not None and target_id not in allowed_targets:
            errors.append(f"target {target_id!r} is not a locally visible contact")
            continue
        try:
            weight = float(raw.get("weight", 0.0))
        except (TypeError, ValueError):
            errors.append(f"weight {raw.get('weight')!r} is not a number")
            continue
        if not -LOCAL_PRIORITY_WEIGHT_LIMIT <= weight <= LOCAL_PRIORITY_WEIGHT_LIMIT:
            errors.append(
                f"weight {weight} exceeds the local limit {LOCAL_PRIORITY_WEIGHT_LIMIT}"
            )
            continue
        adjustments.append(TargetPriorityAdjustment(
            target_id=target_id,
            target_class=raw.get("target_class"),
            weight=round(weight, 3),
            reason=str(raw.get("reason") or "model adjustment")[:200],
        ))

    reports = data.get("report_actions") or []
    if not isinstance(reports, list):
        errors.append("report_actions must be a list")
        reports = []
    unknown_reports = sorted(set(reports) - set(REPORT_ACTIONS))
    if unknown_reports:
        errors.append("unknown report actions: " + ", ".join(unknown_reports))
    if errors:
        return None, errors
    return FormationDecision(
        formation_id=observation.formation_id,
        turn=observation.turn,
        phase=observation.phase,
        selected_movement_action_id=action_id or None,
        selected_movement_plan=plan,
        selected_contingency_branch=branch or None,
        target_priority_adjustments=adjustments,
        report_actions=sorted(set(reports)),
        acknowledgement=bool(data.get("acknowledgement")),
        rationale_summary=str(data.get("rationale_summary") or "")[:500],
        audit={"parsed": True, "legal_actions": len(legal_actions)},
    ), []


class FormationLLMAgent:
    """``FormationPolicy`` implemented by a model call, with audit and fallback."""

    def __init__(
        self,
        policy: FormationPolicyCallable,
        *,
        name: str = "formation-llm-v1",
        max_retries: int = 2,
        fallback: DeterministicFormationAgent | None = None,
    ) -> None:
        self.policy = policy
        self.name = name
        self.max_retries = max_retries
        self.fallback = fallback or DeterministicFormationAgent()
        self.attempts: list[LLMAttempt] = []

    def act(
        self,
        local_observation: FormationObservation,
        mission_order: MissionOrder | None = None,
        comm_state: dict[str, Any] | None = None,
        legal_action_mask: list[dict[str, Any]] | None = None,
        target_priority_space: list[dict[str, Any]] | None = None,
        contract_state: dict[str, Any] | None = None,
    ) -> FormationDecision:
        del comm_state, legal_action_mask, target_priority_space  # carried by the observation
        prompt = build_prompt(local_observation, mission_order, contract_state=contract_state)
        last_errors: list[str] = []
        for attempt in range(1, self.max_retries + 2):
            retry_prompt = prompt
            if last_errors:
                retry_prompt = {
                    **prompt,
                    "previous_response_rejected": last_errors,
                    "instruction": INSTRUCTION + " 上一次回复被拒绝：" + "；".join(last_errors),
                }
            raw = self.policy(retry_prompt)
            decision, errors = parse_response(raw, local_observation)
            self.attempts.append(LLMAttempt(
                formation_id=local_observation.formation_id,
                turn=local_observation.turn,
                phase=local_observation.phase,
                attempt=attempt,
                prompt=retry_prompt,
                raw_response=raw if isinstance(raw, str) else repr(raw),
                errors=list(errors),
                accepted=decision is not None,
            ))
            if decision is not None:
                return decision
            last_errors = errors
        fallback_decision = self.fallback.act(local_observation, mission_order)
        self.attempts[-1] = self.attempts[-1].model_copy(
            update={"fallback": True}
        )
        fallback_decision.audit = {
            **fallback_decision.audit,
            "llm_fallback": True,
            "llm_errors": last_errors,
            "llm_attempts": self.max_retries + 1,
        }
        fallback_decision.rationale_summary = (
            "model responses rejected; deterministic doctrine applied. "
            + fallback_decision.rationale_summary
        )
        return fallback_decision


# --------------------------------------------------------------------------- replay

class RecordedPolicy:
    """Replays captured model responses, keyed by formation and turn.

    A recorded game is therefore re-runnable at zero cost and bit-identically,
    which is the only way an LLM decision can be audited after the fact.
    """

    def __init__(self, records: dict[tuple[str, int], str]) -> None:
        self.records = dict(records)
        self.served: list[tuple[str, int]] = []

    def __call__(self, prompt: dict[str, Any]) -> str:
        key = (str(prompt.get("formation_id")), int(prompt.get("turn") or 0))
        if key not in self.records:
            raise KeyError(f"no recorded response for {key}")
        self.served.append(key)
        return self.records[key]


def record_response(
    records: dict[tuple[str, int], str], decision: FormationDecision, raw: str,
) -> dict[tuple[str, int], str]:
    records[(decision.formation_id, decision.turn)] = raw
    return records
