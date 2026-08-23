param(
    [string]$DestinationRoot = (Join-Path $env:USERPROFILE '.codex\skills')
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$destination = Join-Path $DestinationRoot 'iron-bottom-sound-rules'
New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $DestinationRoot -Recurse -Force
Write-Output "Installed project skill at $destination"
