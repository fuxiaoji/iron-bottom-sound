@echo off
setlocal

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-game.ps1"
set "game_exit_code=%ERRORLEVEL%"

if not "%game_exit_code%"=="0" (
    echo.
    echo Game startup failed.
    echo Check tmp\runtime\backend-error.log and frontend-error.log.
    pause
)

exit /b %game_exit_code%
