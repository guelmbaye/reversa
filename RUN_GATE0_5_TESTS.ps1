$ErrorActionPreference = "Stop"
Write-Host "REVERSA | GATE 0.5 | TEST SUITE" -ForegroundColor Cyan
python -m pytest -q
exit $LASTEXITCODE
