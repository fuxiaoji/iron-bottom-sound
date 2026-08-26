"""共享测试夹具：隔离战报系统的外部副作用。

- autouse 删 `DEEPSEEK_API_KEY`：防任何意外真实 LLM 调用（叙事/指挥官都只在
  该环境变量存在时才真正联网）。
- autouse 把 `api.reports_root` 指向 pytest 临时目录：战报 PNG 只落 tmp，
  绝不清空/污染仓库的 backend/reports。
"""
from __future__ import annotations

import os

import pytest

from iron_bottom_sound import api


@pytest.fixture(autouse=True)
def _guard_llm_and_reports(tmp_path):
    saved_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    old_root = getattr(api, "reports_root", None)
    api.reports_root = tmp_path / "reports"
    try:
        yield
    finally:
        if saved_key is not None:
            os.environ["DEEPSEEK_API_KEY"] = saved_key
        if old_root is not None:
            api.reports_root = old_root
        else:
            delattr(api, "reports_root")
