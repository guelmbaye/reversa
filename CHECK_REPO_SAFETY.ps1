$ErrorActionPreference = "Stop"

Write-Host "REVERSA | Repository safety check" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "This directory is not a Git repository."
}

$bad = @()

$tracked = git ls-files

$forbiddenPatterns = @(
    '(^|/)\.env($|\.)',
    '(^|/)\.venv/',
    '(^|/)node_modules/',
    '(^|/)\.next/',
    '(^|/)\.vercel/'
)

foreach ($file in $tracked) {
    foreach ($pattern in $forbiddenPatterns) {
        if ($file -match $pattern -and $file -notmatch '(^|/)\.env\.example$' -and $file -ne 'web/.env.local.example') {
            $bad += $file
        }
    }
}

# Only final evidence should be tracked under evidence/.
$unexpectedEvidence = $tracked | Where-Object {
    $_ -like 'evidence/*' -and
    $_ -ne 'evidence/live_aba_manifest_FINAL.json' -and
    $_ -notlike 'evidence/live_aba_FINAL/*'
}
$bad += $unexpectedEvidence

$bad = $bad | Sort-Object -Unique

if ($bad.Count -gt 0) {
    Write-Host "REPOSITORY SAFETY: FAIL" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  forbidden tracked file: $_" -ForegroundColor Red }
    exit 1
}

Write-Host "REPOSITORY SAFETY: PASS" -ForegroundColor Green
Write-Host "No local secrets/caches or non-FINAL evidence are tracked."
Write-Host ""
Write-Host "Tracked final evidence:"
git ls-files evidence/live_aba_FINAL evidence/live_aba_manifest_FINAL.json
