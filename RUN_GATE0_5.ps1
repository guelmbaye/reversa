param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("prepare","arm","status","reverify","run","tests")]
    [string]$Stage,

    [ValidateSet("openai","replay")]
    [string]$Provider = "openai",

    [string]$Manifest = "evidence/live_aba_manifest.json",

    [string]$EvidenceDir = "evidence/live_aba",

    [ValidateSet("A1","B","A2")]
    [string]$Slot = "A1"
)

$ErrorActionPreference = "Stop"

Write-Host "REVERSA | GATE 0.5 | LIVE BLIND A->B->A" -ForegroundColor Cyan
Write-Host "Stage: $Stage"

if ($Stage -eq "tests") {
    python -m pytest -q
    exit $LASTEXITCODE
}

if (-not $env:PAYPAL_CLIENT_ID) {
    throw "PAYPAL_CLIENT_ID is not set."
}
if (-not $env:PAYPAL_CLIENT_SECRET) {
    throw "PAYPAL_CLIENT_SECRET is not set."
}
if (-not $env:PAYPAL_BASE_URL) {
    $env:PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"
}

if ($Stage -eq "prepare") {
    python -m app.live_aba prepare --manifest $Manifest
    exit $LASTEXITCODE
}

if ($Stage -eq "arm") {
    python -m app.live_aba arm --manifest $Manifest
    exit $LASTEXITCODE
}

if ($Stage -eq "status") {
    python -m app.live_aba status --manifest $Manifest
    exit $LASTEXITCODE
}

if ($Stage -eq "reverify") {
    python -m app.live_aba reverify `
        --manifest $Manifest `
        --slot $Slot `
        --evidence-dir $EvidenceDir
    exit $LASTEXITCODE
}

if ($Stage -eq "run") {
    if ($Provider -eq "openai") {
        if (-not $env:OPENAI_API_KEY) {
            throw "OPENAI_API_KEY is not set."
        }
        if (-not $env:REVERSA_MODEL) {
            throw "REVERSA_MODEL is not set."
        }
    }

    python -m app.live_aba run `
        --manifest $Manifest `
        --provider $Provider `
        --evidence-dir $EvidenceDir

    exit $LASTEXITCODE
}
