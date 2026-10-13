$ProjectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'game-runtime.ps1')
if (-not (Test-Path -LiteralPath $PidFile)) { Write-Host 'No recorded game processes.'; exit 0 }
$Ids = @(Get-Content -LiteralPath $PidFile)
$Backend = if ($Ids.Count -gt 0 -and [int]$Ids[0] -gt 0) { Get-GameProcess ([int]$Ids[0]) 'backend' }
$Frontend = if ($Ids.Count -gt 1 -and [int]$Ids[1] -gt 0) { Get-GameProcess ([int]$Ids[1]) 'frontend' }
Stop-GameProcess $Backend
Stop-GameProcess $Frontend
Save-GameProcesses $null $null
Write-Host 'Game services stopped. Saved games and reports are unchanged.'
