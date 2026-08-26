"""UI 截图渲染器 + uvicorn 线程（runner 与战报重建共用）。

截图 = 真实 UI（报告视图深链 ?game=&side=&report=1），Playwright 驱动系统 Edge。
产物压缩：2x 原图每张约 1MB → 缩到地图自然尺寸 + 调色板 PNG（约 240KB），
否则 90+ 张 base64 内嵌的 markdown 会膨胀到 100MB+ 而无法阅读。
"""

from __future__ import annotations

import io
import threading
import time

from PIL import Image
from playwright.sync_api import sync_playwright

_EDGE = "c:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
_MAP_SIZE = (1280, 988)  # map-frame 自然 CSS 尺寸（视口 1280×1080 − 92px 头部）


class UIScreenshotRenderer:
    """真实 UI 截图：报告视图逐侧截图 → 压缩为地图自然尺寸的调色板 PNG。"""

    def __init__(self, base_url: str, executable_path: str = _EDGE) -> None:
        self._base = base_url
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            executable_path=executable_path,
            headless=True,
            args=["--disable-gpu", "--hide-scrollbars"],
        )
        self._context = self._browser.new_context(
            device_scale_factor=2, viewport={"width": 1280, "height": 1080}
        )
        self._pages: dict[str, object] = {}

    def _page_for(self, side):
        if side.value not in self._pages:
            self._pages[side.value] = self._context.new_page()
        return self._pages[side.value]

    def __call__(self, state, engine, side, save_path) -> None:
        page = self._page_for(side)
        page.goto(
            f"{self._base}/?game={state.game_id}&side={side.value}&report=1",
            wait_until="networkidle",
        )
        page.wait_for_selector(".map-frame svg .counter", timeout=20000)
        page.wait_for_timeout(500)
        page.locator(".map-frame").screenshot(path=str(save_path))
        with open(save_path, "rb") as f:
            raw = f.read()
        im = Image.open(io.BytesIO(raw))
        if im.size != _MAP_SIZE:
            im = im.resize(_MAP_SIZE, Image.LANCZOS)
        im.convert("P", palette=Image.ADAPTIVE, colors=256).save(
            save_path, format="PNG", optimize=True
        )

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()


def start_server(app, port: int, timeout: float = 20.0):
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError(f"uvicorn failed to start on port {port}")
