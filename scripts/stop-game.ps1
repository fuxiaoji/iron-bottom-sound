$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "tmp\runtime\pids.txt"
if (-not (Test-Path $PidFile)) {
    Write-Host "没有找到正在运行的本项目服务。"
    exit 0
}

Get-Content $PidFile | ForEach-Object {
    $ProcessId = [int]$_
    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $PidFile -Force
Write-Host "铁底湾服务已停止。"
