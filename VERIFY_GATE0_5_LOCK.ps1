param(
    [string]$Lock = "evidence/live_aba_FINAL/proof-lock.json"
)
$ErrorActionPreference = "Stop"
python .\scripts\verify_gate05_lock.py --lock $Lock
exit $LASTEXITCODE
