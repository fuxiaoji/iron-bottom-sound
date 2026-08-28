"""Provider/model capability profiles shared by the API and match runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LLMProvider = Literal["deepseek", "zhipu"]

DEFAULT_MODELS: dict[LLMProvider, str] = {
    "deepseek": "deepseek-v4-flash",
    "zhipu": "glm-5.2",
}


@dataclass(frozen=True)
class ProviderRuntime:
    provider: LLMProvider
    model: str
    endpoint: str
    api_key_env: str
    supports_thinking: bool
    thinking_required: bool
    supports_vision: bool
    plan_max_tokens: int


def _zhipu_vision_model(model: str) -> bool:
    return model.lower().startswith(("glm-5v", "glm-4.6v", "glm-4.5v", "glm-4v"))


def provider_runtime(
    provider: LLMProvider, model: str | None = None, *, vision_enabled: bool = False
) -> ProviderRuntime:
    selected = (model or DEFAULT_MODELS[provider]).strip()
    if provider == "zhipu":
        runtime = ProviderRuntime(
            provider=provider,
            model=selected,
            endpoint="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPU_API_KEY",
            supports_thinking=True,
            thinking_required=selected.lower().startswith("glm-5.3"),
            supports_vision=_zhipu_vision_model(selected),
            plan_max_tokens=6000,
        )
    else:
        runtime = ProviderRuntime(
            provider=provider,
            model=selected,
            endpoint="https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            supports_thinking=True,
            thinking_required=False,
            supports_vision=False,
            plan_max_tokens=2400,
        )
    if vision_enabled and not runtime.supports_vision:
        if provider == "zhipu":
            raise ValueError(
                f"模型 {selected} 是文本模型，不能接收地图图片；请关闭地图视觉，"
                "或改用 glm-5v-turbo 等视觉模型"
            )
        raise ValueError(f"模型 {selected} 不支持地图图片，请关闭地图视觉")
    return runtime
