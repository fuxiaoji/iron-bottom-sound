$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "tmp\runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$env:IBS_DB_PATH = Join-Path $ProjectRoot "backend\iron-bottom-sound.sqlite3"

$Backend = Start-Process -FilePath "python" -ArgumentList @(
    "-m", "uvicorn", "iron_bottom_sound.api:app", "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", "8000"
) -WorkingDirectory $ProjectRoot -RedirectStandardOutput (Join-Path $RuntimeDir "backend.log") -RedirectStandardError (Join-Path $RuntimeDir "backend-error.log") -WindowStyle Hidden -PassThru

$Node = Get-Command "node" -ErrorAction SilentlyContinue
if ($null -eq $Node) {
    $BundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (-not (Test-Path $BundledNode)) {
        throw "Node.js not found. Install Node.js 20+ and pnpm."
    }
    $NodePath = $BundledNode
} else {
    $NodePath = $Node.Source
}
$Frontend = Start-Process -FilePath $NodePath -ArgumentList @(
    "node_modules/vite/bin/vite.js", "--host", "127.0.0.1"
) -WorkingDirectory (Join-Path $ProjectRoot "frontend") -RedirectStandardOutput (Join-Path $RuntimeDir "frontend.log") -RedirectStandardError (Join-Path $RuntimeDir "frontend-error.log") -WindowStyle Hidden -PassThru

@($Backend.Id, $Frontend.Id) | Set-Content -Path (Join-Path $RuntimeDir "pids.txt")
$BackendReady = $false
for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
    try {
        $Health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/scenarios" -UseBasicParsing -TimeoutSec 1
        if ($Health.StatusCode -eq 200) { $BackendReady = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $BackendReady) {
    Write-Error "Backend did not start within 15 seconds. See $RuntimeDir\backend-error.log"
    exit 1
}
$FrontendReady = $false
for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
    try {
        $Page = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 1
        if ($Page.StatusCode -eq 200) { $FrontendReady = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $FrontendReady) {
    Write-Error "Frontend did not start within 15 seconds. See $RuntimeDir\frontend-error.log"
    exit 1
}
Start-Process "http://127.0.0.1:5173"
Write-Host "Iron Bottom Sound started: http://127.0.0.1:5173"
Write-Host "Stop: powershell -ExecutionPolicy Bypass -File scripts/stop-game.ps1"
