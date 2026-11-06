$ErrorActionPreference = "Stop"

Write-Host "REVERSA | Git repository initialization" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available in PATH."
}

if (Test-Path ".git") {
    Write-Host "Git repository already exists. No reinitialization performed." -ForegroundColor Yellow
} else {
    git init -b main
    if ($LASTEXITCODE -ne 0) {
        # Compatibility fallback for older Git versions.
        git init
        git branch -M main
    }
}

Write-Host ""
Write-Host "Checking ignored files..." -ForegroundColor Cyan
git status --short --ignored

Write-Host ""
Write-Host "Staging repository..." -ForegroundColor Cyan
git add .

Write-Host ""
Write-Host "STAGED FILES" -ForegroundColor Green
git diff --cached --name-status

Write-Host ""
Write-Host "IMPORTANT: inspect the staged file list above before committing." -ForegroundColor Yellow
Write-Host "The repository should NOT contain .env files, .venv, node_modules, .next, or non-FINAL evidence."
Write-Host ""
Write-Host "If clean, commit with:"
Write-Host '  git commit -m "feat: ship REVERSA verified recovery demo"'
