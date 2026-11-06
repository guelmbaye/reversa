param(
    [string]$EvidenceDir = "evidence/live_aba_FINAL",
    [string]$Manifest = "evidence/live_aba_manifest_FINAL.json",
    [string]$Output = "evidence/live_aba_FINAL/proof-lock.json"
)

$ErrorActionPreference = "Stop"
python .\scripts\freeze_gate05.py `
  --evidence-dir $EvidenceDir `
  --manifest $Manifest `
  --output $Output
exit $LASTEXITCODE
