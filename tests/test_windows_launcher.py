"""Exercise the built PE against isolated stub projects, never the player DB."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows EXE launcher")


@pytest.fixture(scope="module")
def launcher_exe(tmp_path_factory):
    if not shutil.which("powershell.exe"):
        pytest.skip("Windows PowerShell is required")
    directory = tmp_path_factory.mktemp("launcher-build")
    executable = directory / "启动 游戏.exe"
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(ROOT / "scripts/build-launcher.ps1"), "-OutputPath", str(executable)],
        capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    data = executable.read_bytes()
    assert data[:2] == b"MZ"
    pe_offset = int.from_bytes(data[60:64], "little")
    assert data[pe_offset:pe_offset + 4] == b"PE\0\0"
    optional_header = pe_offset + 24
    assert int.from_bytes(data[optional_header + 68:optional_header + 70], "little") == 2  # Windows GUI
    return executable


def stub_project(tmp_path, executable, script):
    project = tmp_path / "测试 舰队项目"
    for directory in ("scripts", "frontend", "backend/src/iron_bottom_sound"):
        (project / directory).mkdir(parents=True, exist_ok=True)
    (project / "scripts/start-game.ps1").write_text(script, encoding="utf-8-sig")
    (project / "scripts/game-runtime.ps1").write_text("# isolated stub", encoding="utf-8")
    (project / "frontend/package.json").write_text("{}", encoding="utf-8")
    (project / "backend/src/iron_bottom_sound/api.py").write_text("# isolated stub", encoding="utf-8")
    copied = project / executable.name
    shutil.copy2(executable, copied)
    return project, copied


def run(executable, *arguments, cwd=None):
    return subprocess.run([str(executable), "--quiet", *arguments], cwd=cwd,
                          capture_output=True, encoding="utf-8", timeout=15)


def test_unicode_paths_working_directory_and_flags(tmp_path, launcher_exe):
    script = """param([switch]$NoBrowser,[switch]$RestartBackend)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Write-Output ((Get-Location).Path)
Write-Output ('NoBrowser=' + $NoBrowser + ';RestartBackend=' + $RestartBackend)
Write-Output '中文启动完成'
exit 0
"""
    project, executable = stub_project(tmp_path, launcher_exe, script)
    result = run(executable, "--no-browser", "--restart-backend", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "游戏已就绪" in result.stdout
    log = (project / "tmp/runtime/launcher.log").read_text(encoding="utf-8")
    assert str(project) in log and "中文启动完成" in log
    assert "NoBrowser=True;RestartBackend=True" in log


def test_default_passes_no_suppression_flags(tmp_path, launcher_exe):
    project, executable = stub_project(tmp_path, launcher_exe, """param([switch]$NoBrowser,[switch]$RestartBackend)
Write-Output ('NoBrowser=' + $NoBrowser + ';RestartBackend=' + $RestartBackend)
""")
    assert run(executable).returncode == 0
    assert "NoBrowser=False;RestartBackend=False" in (project / "tmp/runtime/launcher.log").read_text()


def test_error_exit_code_and_logs(tmp_path, launcher_exe):
    project, executable = stub_project(tmp_path, launcher_exe, "Write-Error 'stub startup failed'; exit 7")
    result = run(executable, "--no-browser")
    assert result.returncode == 7
    assert "游戏未能启动" in result.stderr
    assert "stub startup failed" in (project / "tmp/runtime/launcher.log").read_text(encoding="utf-8")


def test_foreign_port_error_is_actionable(tmp_path, launcher_exe):
    _, executable = stub_project(tmp_path, launcher_exe, "throw 'PID 123 is not recognized; left untouched.'")
    result = run(executable, "--no-browser")
    assert result.returncode != 0
    assert "端口被未确认归属的服务占用" in result.stderr
    assert "未被强行停止" in result.stderr


def test_moved_executable_does_not_run_any_script(tmp_path, launcher_exe):
    executable = tmp_path / "moved.exe"
    shutil.copy2(launcher_exe, executable)
    result = run(executable, "--no-browser")
    assert result.returncode == 2
    assert "项目根目录" in result.stderr and "不是独立游戏安装包" in result.stderr
    assert not (tmp_path / "tmp").exists()


def test_second_click_does_not_launch_a_second_script(tmp_path, launcher_exe):
    project, executable = stub_project(tmp_path, launcher_exe, """$ErrorActionPreference='Stop'
Add-Content -LiteralPath (Join-Path $PSScriptRoot 'invocations.txt') -Value 'started'
Start-Sleep -Seconds 2
""")
    first = subprocess.Popen([str(executable), "--quiet", "--no-browser"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    marker = project / "scripts/invocations.txt"
    try:
        deadline = time.monotonic() + 8
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "First launch did not start"
        second = run(executable, "--no-browser")
        assert second.returncode == 0 and "正在启动" in second.stdout
        stdout, stderr = first.communicate(timeout=10)
        assert first.returncode == 0, stderr
        assert marker.read_text().splitlines() == ["started"]
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=5)


def test_build_refuses_to_overwrite_existing_exe(tmp_path, launcher_exe):
    output = tmp_path / "preserve.exe"
    shutil.copy2(launcher_exe, output)
    before = output.read_bytes()
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(ROOT / "scripts/build-launcher.ps1"), "-OutputPath", str(output)],
                            capture_output=True, timeout=15)
    assert result.returncode != 0
    assert output.read_bytes() == before


def test_help_and_unknown_arguments_do_not_launch(tmp_path, launcher_exe):
    _, executable = stub_project(tmp_path, launcher_exe, "throw 'must not run'")
    assert run(executable, "--help").returncode == 0
    result = run(executable, "--unknown")
    assert result.returncode == 2 and "不支持的参数" in result.stderr


def test_gui_default_closes_on_success(tmp_path, launcher_exe):
    project, executable = stub_project(tmp_path, launcher_exe, "Write-Output 'GUI success'")
    result = subprocess.run([str(executable)], capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "GUI success" in (project / "tmp/runtime/launcher.log").read_text()


def test_gui_error_state_and_close_button(tmp_path, launcher_exe):
    project, executable = stub_project(tmp_path, launcher_exe, "Start-Sleep -Seconds 1; throw 'left untouched.'")
    preview = tmp_path / "screenshots"
    preview.mkdir()
    result = subprocess.run(
        ["powershell.exe", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(ROOT / "tests/check_launcher_window.ps1"), "-ExePath", str(executable),
         "-ProjectRoot", str(project), "-OutputDir", str(preview)],
        capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert (preview / "startup.png").read_bytes().startswith(b"\x89PNG")
    assert (preview / "failure.png").read_bytes().startswith(b"\x89PNG")
