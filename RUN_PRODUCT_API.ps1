param(
    [string]$EvidenceDir = "evidence/live_aba_FINAL",
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$env:REVERSA_EVIDENCE_DIR = $EvidenceDir
python -m uvicorn api.server:app --host 127.0.0.1 --port $Port --reload
