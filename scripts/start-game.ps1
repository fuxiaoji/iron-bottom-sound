param([switch]$RestartBackend, [switch]$NoBrowser)
if ($env:IBS_LAUNCHER_UTF8 -eq '1') { [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false) }
. (Join-Path $PSScriptRoot 'game-runtime.ps1')
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$Backend = $null
$Frontend = $null
foreach ($entry in @(@(8000, 'backend'), @(5173, 'frontend'))) {
    $owners = @(Get-NetTCPConnection -LocalPort $entry[0] -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -gt 1) { throw "Port $($entry[0]) has multiple owners; left untouched." }
    if ($owners.Count -eq 1) {
        $owned = Get-GameListener $owners[0] $entry[1]
        if ($entry[1] -eq 'backend') { $Backend = $owned } else { $Frontend = $owned }
    }
}
Save-GameProcesses $Backend $Frontend
if ($null -ne $Backend) {
    $Fresh = $false
    try { $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2; $Fresh = $health.status -eq 'ready' } catch { }
    if ($RestartBackend -or -not $Fresh) {
        Stop-GameProcess $Backend
        $Backend = $null
        for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
            if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Milliseconds 250
        }
    }
}
if ($null -eq $Backend) {
    $env:IBS_DB_PATH = Join-Path $ProjectRoot 'backend\iron-bottom-sound.sqlite3'
    $env:IBS_REPORTS_DIR = Join-Path $ProjectRoot 'backend\reports'
    $SourceDir = Join-Path $ProjectRoot 'backend\src'
    $Process = Start-Process -FilePath 'python' -ArgumentList @(
        '-m', 'uvicorn', 'iron_bottom_sound.api:app', '--app-dir', ('"' + $SourceDir + '"'),
        '--host', '127.0.0.1', '--port', '8000', '--reload', '--reload-dir', ('"' + $SourceDir + '"')
    ) -WorkingDirectory $ProjectRoot -RedirectStandardOutput (Join-Path $RuntimeDir 'backend.log') -RedirectStandardError (Join-Path $RuntimeDir 'backend-error.log') -WindowStyle Hidden -PassThru
    $Backend = Get-CimInstance Win32_Process -Filter "ProcessId=$($Process.Id)"
    Save-GameProcesses $Backend $Frontend
}
if ($null -eq $Frontend) {
    $Node = Get-Command 'node' -ErrorAction SilentlyContinue
    $NodePath = if ($Node) { $Node.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
    if (-not (Test-Path -LiteralPath $NodePath)) { throw 'Node.js not found. Install Node.js 20+.' }
    $Process = Start-Process -FilePath $NodePath -ArgumentList @(
        'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'
    ) -WorkingDirectory (Join-Path $ProjectRoot 'frontend') -RedirectStandardOutput (Join-Path $RuntimeDir 'frontend.log') -RedirectStandardError (Join-Path $RuntimeDir 'frontend-error.log') -WindowStyle Hidden -PassThru
    $Frontend = Get-CimInstance Win32_Process -Filter "ProcessId=$($Process.Id)"
    Save-GameProcesses $Backend $Frontend
}
$Ready = $false
for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
    if (-not (Get-Process -Id $Backend.ProcessId -ErrorAction SilentlyContinue) -or
        -not (Get-Process -Id $Frontend.ProcessId -ErrorAction SilentlyContinue)) {
        throw "A launched process exited. See logs in $RuntimeDir."
    }
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 1
        $page = Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 1
        if ($health.status -eq 'ready' -and $page.StatusCode -eq 200) { $Ready = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $Ready) { throw "Game did not become ready. See logs in $RuntimeDir." }
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' }
Write-Host 'Iron Bottom Sound ready: http://127.0.0.1:5173'
Write-Host 'Python source changes reload automatically. Saved games are preserved.'
