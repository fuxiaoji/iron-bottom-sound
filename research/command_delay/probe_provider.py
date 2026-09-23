"""Probe an OpenAI-compatible provider before a battle, and record the answer.

The command-delay mode can hand every formation to a real model, but "the key works"
is not the same as "this model can play".  Three things have to be true, and each has
bitten this project or its neighbours before:

* the model answers at all on this key (``glm-4.6`` answers 429 "no quota");
* it does not spend the whole budget on hidden reasoning (``glm-4.5-flash`` returns an
  empty ``content`` with ``finish_reason=length`` when the budget is small, which the
  formation adapter correctly refuses to parse);
* it returns **strict JSON**, because the decision parser rejects anything else - a
  ```json fence would make every decision illegal and silently hand the battle to the
  doctrine fallback.

So this probe sends the same payload shape ``ProviderPolicy`` sends, with a real
formation-shaped request, and records status / finish_reason / usage / whether the
content is strict JSON / whether it arrived fenced / latency.  The key is read from
``ZHIPU_API_KEY`` and never written to the output.

    ZHIPU_API_KEY=... .venv/bin/python research/command_delay/probe_provider.py \
        [--provider zhipu] [--models glm-4-flash,glm-4.5-flash]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

OUT = Path(__file__).resolve().parent / "provider_probe.json"

SYSTEM = (
    "你是二战海战兵棋中的编队指挥官，只输出严格 JSON："
    '{"selected_movement_action_id": "<string>", "selected_contingency_branch": null, '
    '"target_priority_adjustments": [], "report_actions": ["NONE"], '
    '"rationale_summary": "<one sentence>", "memory_note": "<one sentence>"}'
)
USER = json.dumps({
    "instruction": "只依据给出的本地情报决策；机动只能从 legal_formation_actions 里选一个 action_id。",
    "response_schema": {
        "selected_movement_action_id": "action_id from legal_formation_actions",
        "report_actions": ["NONE", "SITREP"],
        "rationale_summary": "one sentence",
        "memory_note": "one sentence",
    },
    "formation": "IBS-S-EM-01-axis-1",
    "turn": 3,
    "phase": "movement_planning",
    "order_text": "第1战队：向东南接敌，优先压制敌巡洋舰。",
    "your_memory": "【当前生效命令（第 2 回合收到）】向东南接敌。",
    "formation_state": {"heading": 2, "speed": 4, "geometry_kind": "column", "ship_count": 4},
    "local_contacts": [{"name": "旧金山", "ship_type": "CA", "range": 7, "position": "V14"}],
    "legal_formation_actions": [
        {"action_id": "MOVE:2S2", "cost": 4, "label": "R16"},
        {"action_id": "MOVE:1P1", "cost": 2, "label": "Q15"},
    ],
    "legal_target_priority_options": [{"target_id": "IBS-U-USN-SAN-FRANCISCO", "weight_max": 0.5,
                                       "weight_min": -0.5}],
    "report_actions": ["NONE", "SITREP", "CONTACT_REPORT"],
    "priority_weight_limit": 0.5,
}, ensure_ascii=False)


def probe(endpoint: str, api_key: str, model: str, *, timeout: float = 90.0,
          max_tokens: int = 700, supports_thinking: bool = True,
          attempts: int = 4, backoff: float = 6.0) -> dict:
    """One model, retried.  The sandbox's transparent proxy answers 503/TLS-reset in
    bursts (``open.bigmodel.cn`` resolves into 198.18.0.0/15 here), so a single
    failure is not evidence that a model is unusable - only a failure across all
    attempts is."""
    import httpx

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": USER}],
    }
    if supports_thinking:
        payload["thinking"] = {"type": "disabled"}

    started = time.monotonic()
    record: dict = {"model": model, "max_tokens": max_tokens,
                    "thinking_field": bool(supports_thinking), "attempts": []}
    response = None
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(
                f"{endpoint.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload, timeout=timeout, trust_env=False,
            )
            record["attempts"].append({"attempt": attempt, "http_status": response.status_code})
            if response.status_code < 500:
                break
            error = None
        except Exception as failure:  # noqa: BLE001 - the point is to record any failure
            response = None
            error = failure
            record["attempts"].append(
                {"attempt": attempt, "transport_error": f"{type(failure).__name__}"}
            )
        if attempt < attempts:
            time.sleep(backoff * attempt)

    if response is None or response.status_code >= 500:
        detail = (f"{type(error).__name__}: {error}" if error is not None
                  else f"HTTP {response.status_code}")
        record.update({"http_status": None, "transport_error": detail})
        record["latency_s"] = round(time.monotonic() - started, 2)
        record["playable"] = False
        return record

    record["http_status"] = response.status_code
    record["latency_s"] = round(time.monotonic() - started, 2)
    if response.status_code != 200:
        record["error_body"] = response.text[:300]
        record["playable"] = False
        return record

    body = response.json()
    choice = body["choices"][0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    record.update({
        "finish_reason": choice.get("finish_reason"),
        "usage": body.get("usage") or {},
        "request_id": body.get("id"),
        "content_chars": len(content),
        "reasoning_chars": len(reasoning),
    })
    stripped = content.strip()
    fenced = stripped.startswith("```")
    if fenced:
        # same unwrapping the project's bridge does for fleet replies
        inner = stripped.split("```")
        stripped = (inner[1] if len(inner) > 1 else stripped)
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped
        stripped = stripped.rsplit("```", 1)[0].strip()
    record["markdown_fenced"] = fenced
    try:
        parsed = json.loads(stripped)
        record["strict_json"] = True
        record["parsed_keys"] = sorted(parsed)[:8] if isinstance(parsed, dict) else None
    except Exception as error:  # noqa: BLE001
        record["strict_json"] = False
        record["parse_error"] = str(error)[:120]
        record["content_head"] = content[:160]

    record["playable"] = bool(
        record.get("strict_json")
        and record.get("content_chars")
        and record.get("finish_reason") != "length"
        and not reasoning
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="zhipu")
    parser.add_argument("--models", default="glm-4-flash,glm-4.5-flash,glm-4.6")
    parser.add_argument("--api-key-env", default="ZHIPU_API_KEY")
    args = parser.parse_args()

    from iron_bottom_sound.llm_providers import provider_runtime

    key = os.environ.get(args.api_key_env, "")
    if not key:
        print(f"no key in ${args.api_key_env}", file=sys.stderr)
        return 2

    results = []
    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        runtime = provider_runtime(args.provider, model)  # type: ignore[arg-type]
        print(f"--- {model} ---", flush=True)
        record = probe(runtime.endpoint, key, model,
                       supports_thinking=runtime.supports_thinking)
        record["provider"] = args.provider
        record["endpoint"] = runtime.endpoint
        print(json.dumps(record, ensure_ascii=False, indent=1)[:600], flush=True)
        results.append(record)

    playable = [item["model"] for item in results if item.get("playable")]
    payload = {"provider": args.provider, "results": results, "playable": playable}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nplayable: {playable or 'NONE'}  -> {OUT}", flush=True)
    return 0 if playable else 1


if __name__ == "__main__":
    raise SystemExit(main())
