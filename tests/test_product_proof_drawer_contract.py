from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_proof_drawer_contains_judge_audit_signals():
    text = (ROOT / "web/components/recovery-console.tsx").read_text(encoding="utf-8")
    for phrase in [
        "VIEW PROOF",
        "PAYPAL IDENTIFIERS",
        "INDEPENDENT VERIFIER",
        "RUN SAFETY",
        "SHA-256 PROOF LOCK",
        "INTEGRITY PASS",
        "OPEN TECHNICAL PROOF",
    ]:
        assert phrase in text


def test_final_bundle_type_exposes_proof_lock():
    text = (ROOT / "web/lib/types.ts").read_text(encoding="utf-8")
    assert "proof_lock?: ProofLock | null" in text
    assert "integrity_pass: boolean" in text
