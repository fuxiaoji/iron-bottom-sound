$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$RuntimeDir = Join-Path $ProjectRoot 'tmp\runtime'
$PidFile = Join-Path $RuntimeDir 'pids.txt'
$MetadataFile = Join-Path $RuntimeDir 'processes.json'

function Get-GameProcess([int]$ProcessId, [string]$Kind) {
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $candidate) { return $null }
    $command = [string]$candidate.CommandLine
    $signature = if ($Kind -eq 'backend') { 'uvicorn iron_bottom_sound.api:app' } else { 'node_modules[/\\]vite[/\\]bin[/\\]vite.js' }
    if ($command -notmatch $signature) { throw "PID $ProcessId is not a recognized $Kind process; left untouched." }
    if (Test-Path -LiteralPath $MetadataFile) {
        $record = (Get-Content -LiteralPath $MetadataFile -Raw | ConvertFrom-Json).$Kind
        if ($null -eq $record -or $record.id -ne $ProcessId -or
            $candidate.CreationDate.ToUniversalTime().Ticks -ne ([datetime]$record.created).ToUniversalTime().Ticks) {
            throw "PID $ProcessId does not match this project's recorded start time; left untouched."
        }
    } else {
        if (-not (Test-Path -LiteralPath $PidFile)) { throw 'No project process record; left untouched.' }
        $legacy = @(Get-Content -LiteralPath $PidFile)
        $index = if ($Kind -eq 'backend') { 0 } else { 1 }
        $stamp = (Get-Item -LiteralPath $PidFile).LastWriteTimeUtc
        if ($legacy.Count -le $index -or [int]$legacy[$index] -ne $ProcessId -or
            [Math]::Abs(($candidate.CreationDate.ToUniversalTime() - $stamp).TotalSeconds) -gt 10) {
            throw 'Legacy process ownership could not be verified; left untouched.'
        }
    }
    return $candidate
}

function Get-GameListener([int]$ProcessId, [string]$Kind) {
    if ($Kind -eq 'backend' -and (Test-Path -LiteralPath $MetadataFile)) {
        $record = (Get-Content -LiteralPath $MetadataFile -Raw | ConvertFrom-Json).backend
        if ($record -and $record.id -ne $ProcessId) {
            $root = Get-GameProcess ([int]$record.id) 'backend'
            if ($null -eq $root) { throw 'The recorded backend parent is gone; left untouched.' }
            $cursor = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId"
            for ($Depth = 0; $Depth -lt 10 -and $cursor; $Depth++) {
                if ($cursor.CreationDate -lt $root.CreationDate) { break }
                if ($cursor.ParentProcessId -eq $root.ProcessId) { return $root }
                $cursor = Get-CimInstance Win32_Process -Filter "ProcessId=$($cursor.ParentProcessId)" -ErrorAction SilentlyContinue
            }
            throw 'The listening process is not a child of this backend; left untouched.'
        }
    }
    return Get-GameProcess $ProcessId $Kind
}

function Stop-GameProcess($Candidate) {
    if ($null -eq $Candidate) { return }
    $snapshot = @(Get-CimInstance Win32_Process)
    $descendants = [Collections.Generic.List[object]]::new()
    $parents = @([int]$Candidate.ProcessId)
    while ($parents.Count -gt 0) {
        $children = @($snapshot | Where-Object {
            $parents -contains [int]$_.ParentProcessId -and $_.CreationDate -ge $Candidate.CreationDate
        })
        foreach ($child in $children) { $descendants.Add($child) }
        $parents = @($children | ForEach-Object { [int]$_.ProcessId })
    }
    Stop-Process -Id $Candidate.ProcessId -ErrorAction SilentlyContinue
    foreach ($child in $descendants) {
        $live = Get-CimInstance Win32_Process -Filter "ProcessId=$($child.ProcessId)" -ErrorAction SilentlyContinue
        if ($null -ne $live -and $live.CreationDate -eq $child.CreationDate) {
            Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
        }
    }
}

function Save-GameProcesses($Backend, $Frontend) {
    $records = @{}
    foreach ($entry in @(@('backend', $Backend), @('frontend', $Frontend))) {
        if ($null -ne $entry[1]) {
            $records[$entry[0]] = @{ id = [int]$entry[1].ProcessId; created = $entry[1].CreationDate.ToUniversalTime().ToString('o') }
        }
    }
    $records | ConvertTo-Json | Set-Content -LiteralPath $MetadataFile -Encoding UTF8
    @($(if ($Backend) { $Backend.ProcessId } else { 0 }), $(if ($Frontend) { $Frontend.ProcessId } else { 0 })) |
        Set-Content -LiteralPath $PidFile -Encoding ASCII
}
