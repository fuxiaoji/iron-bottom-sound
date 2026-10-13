param([string]$ExePath, [string]$ProjectRoot, [string]$OutputDir)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Reflection.Assembly]::LoadFrom($ExePath) | Out-Null
$script:LauncherWindow = [IronBottomSoundLauncher.StartupWindow]::new($ProjectRoot, $true, $false)
$script:LauncherTick = 0
$script:CapturedFailure = $false
function Save-LauncherWindow([string]$Name) {
    $image = [Drawing.Bitmap]::new($script:LauncherWindow.Width, $script:LauncherWindow.Height)
    try {
        $script:LauncherWindow.DrawToBitmap($image, [Drawing.Rectangle]::new(0, 0, $image.Width, $image.Height))
        $image.Save((Join-Path $OutputDir $Name), [Drawing.Imaging.ImageFormat]::Png)
    } finally { $image.Dispose() }
}
$LauncherTimer = [Windows.Forms.Timer]::new()
$LauncherTimer.Interval = 100
$LauncherTimer.add_Tick({
    $script:LauncherTick++
    if ($script:LauncherTick -eq 1) { Save-LauncherWindow 'startup.png' }
    $close = @($script:LauncherWindow.Controls | Where-Object { $_ -is [Windows.Forms.Button] -and $_.Text -eq ([string][char]0x5173 + [char]0x95ed) })
    if ($close.Count -eq 1 -and $close[0].Visible) {
        Save-LauncherWindow 'failure.png'
        $script:CapturedFailure = $true
        $close[0].PerformClick()
    } elseif ($script:LauncherTick -gt 150) { $script:LauncherWindow.Dispose() }
})
$LauncherTimer.Start()
try { [Windows.Forms.Application]::Run($script:LauncherWindow) }
finally { $LauncherTimer.Stop(); $LauncherTimer.Dispose(); $script:LauncherWindow.Dispose() }
if (-not $script:CapturedFailure) { throw 'Launcher error window was not reached.' }
