param([string]$OutputPath)
$ErrorActionPreference = 'Stop'
$LauncherRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
if (-not $OutputPath) { $OutputPath = Join-Path $LauncherRoot '一键启动游戏.exe' }
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $OutputPath) { throw "Output already exists; choose a new -OutputPath. Left untouched: $OutputPath" }
$Compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $Compiler)) { $Compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path -LiteralPath $Compiler)) { throw '.NET Framework 4 C# compiler was not found.' }
$Source = Join-Path $PSScriptRoot 'launcher\GameLauncher.cs'
& $Compiler /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 /reference:System.Windows.Forms.dll /reference:System.Drawing.dll ('/out:' + $OutputPath) $Source
if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed: $LASTEXITCODE" }
Get-Item -LiteralPath $OutputPath | Select-Object FullName, Length
$LauncherHash = [Security.Cryptography.SHA256]::Create()
$LauncherStream = [IO.File]::OpenRead($OutputPath)
try { [BitConverter]::ToString($LauncherHash.ComputeHash($LauncherStream)).Replace('-', '') }
finally { $LauncherStream.Dispose(); $LauncherHash.Dispose() }
