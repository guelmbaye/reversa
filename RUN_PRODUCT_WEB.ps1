param(
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$env:NEXT_PUBLIC_REVERSA_API_URL = $ApiUrl

Push-Location "$PSScriptRoot\web"
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing web dependencies..." -ForegroundColor Cyan
        npm install
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "REVERSA Recovery Console" -ForegroundColor Green
    Write-Host "API: $ApiUrl"
    Write-Host "WEB: http://127.0.0.1:3000"
    npm run dev -- --hostname 127.0.0.1
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
