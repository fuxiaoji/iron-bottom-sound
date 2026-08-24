$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "tmp\runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$env:IBS_DB_PATH = Join-Path $ProjectRoot "backend\iron-bottom-sound.sqlite3"

$Backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "iron_bottom_sound.api:app", "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput (Join-Path $RuntimeDir "backend.log") `
    -RedirectStandardError (Join-Path $RuntimeDir "backend-error.log") `
    -WindowStyle Hidden -PassThru

$Node = Get-Command "node" -ErrorAction SilentlyContinue
if ($null -eq $Node) {
    $BundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (-not (Test-Path $BundledNode)) {
        throw "未找到 Node.js。请先安装 Node.js 20+ 和 pnpm。"
    }
    $NodePath = $BundledNode
} else {
    $NodePath = $Node.Source
}
$Frontend = Start-Process -FilePath $NodePath `
    -ArgumentList "node_modules/vite/bin/vite.js", "--host", "127.0.0.1" `
    -WorkingDirectory (Join-Path $ProjectRoot "frontend") `
    -RedirectStandardOutput (Join-Path $RuntimeDir "frontend.log") `
    -RedirectStandardError (Join-Path $RuntimeDir "frontend-error.log") `
    -WindowStyle Hidden -PassThru

@($Backend.Id, $Frontend.Id) | Set-Content -Path (Join-Path $RuntimeDir "pids.txt")
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5173"
Write-Host "铁底湾已启动：http://127.0.0.1:5173"
Write-Host "停止服务：powershell -ExecutionPolicy Bypass -File scripts/stop-game.ps1"
