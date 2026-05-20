param(
    [string]$AddonName = "card_info_popup",
    [string]$AnkiAddonsRoot = "$env:APPDATA\Anki2\addons21"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $projectRoot "card_stats_popup"
$destinationDir = Join-Path $AnkiAddonsRoot $AddonName

if (-not (Test-Path $sourceDir)) {
    throw "Source directory not found: $sourceDir"
}

if (-not (Test-Path $destinationDir)) {
    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
}

# Copy addon runtime files from card_stats_popup into the actual Anki addon folder.
$null = robocopy $sourceDir $destinationDir /E /NFL /NDL /NJH /NJS /NC /NS /XD "__pycache__" /XF "*.pyc"
$exitCode = $LASTEXITCODE
if ($exitCode -ge 8) {
    throw "Robocopy failed with exit code $exitCode"
}

Write-Host "Synced addon files to $destinationDir"
