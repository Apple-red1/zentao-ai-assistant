param(
    [Parameter(Mandatory = $false)]
    [string]$StatePath = "$env:USERPROFILE\.codex\.codex-global-state.json",

    [Parameter(Mandatory = $false)]
    [string]$ProjectPath = "F:\每日工作",

    [Parameter(Mandatory = $false)]
    [switch]$WaitForCodexExit,

    [Parameter(Mandatory = $false)]
    [ValidateRange(100, 10000)]
    [int]$PollMilliseconds = 500,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 604800)]
    [int]$TimeoutSeconds = 86400
)

$ErrorActionPreference = "Stop"

function Wait-CodexExit {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $emptyChecks = 0

    while ([DateTime]::UtcNow -lt $deadline) {
        $codexProcesses = @(Get-Process -Name "Codex" -ErrorAction SilentlyContinue)
        if ($codexProcesses.Count -eq 0) {
            $emptyChecks += 1
            if ($emptyChecks -ge 2) {
                return
            }
        }
        else {
            $emptyChecks = 0
        }

        Start-Sleep -Milliseconds $PollMilliseconds
    }

    throw "Timed out waiting for Codex to exit."
}

function Add-ProjectFirst {
    param([object[]]$Items)

    $updated = New-Object System.Collections.Generic.List[string]
    $updated.Add($ProjectPath)

    foreach ($item in @($Items)) {
        $value = [string]$item
        if (-not [string]::IsNullOrWhiteSpace($value) -and
            -not [string]::Equals($value, $ProjectPath, [StringComparison]::OrdinalIgnoreCase)) {
            $updated.Add($value)
        }
    }

    return $updated.ToArray()
}

if ($WaitForCodexExit) {
    Wait-CodexExit
}

if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
    throw "Codex state file does not exist: $StatePath"
}

$state = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($propertyName in @("electron-saved-workspace-roots", "project-order")) {
    $property = $state.PSObject.Properties[$propertyName]
    $current = if ($null -eq $property) { @() } else { @($property.Value) }
    $updated = @(Add-ProjectFirst -Items $current)

    if ($null -eq $property) {
        $state | Add-Member -MemberType NoteProperty -Name $propertyName -Value $updated
    }
    else {
        $property.Value = $updated
    }
}

$stateDirectory = Split-Path -Parent $StatePath
$temporaryPath = Join-Path $stateDirectory (".{0}.{1}.tmp" -f [IO.Path]::GetFileName($StatePath), [Guid]::NewGuid().ToString("N"))
$json = $state | ConvertTo-Json -Depth 100
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)

try {
    [IO.File]::WriteAllText($temporaryPath, $json, $utf8WithoutBom)
    Move-Item -LiteralPath $temporaryPath -Destination $StatePath -Force
}
finally {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Force
    }
}

[ordered]@{
    registered = $true
    firstProject = $ProjectPath
    statePath = $StatePath
} | ConvertTo-Json -Compress
