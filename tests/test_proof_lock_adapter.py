import hashlib
import json
from pathlib import Path

from api.evidence_adapter import load_proof_lock


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_proof_lock_rehashes_current_files(tmp_path):
    repo = tmp_path
    evidence = repo / "evidence" / "live_aba_FINAL"
    evidence.mkdir(parents=True)
    target = evidence / "live_aba_summary.json"
    target.write_text('{"result":"PASS"}', encoding="utf-8")

    lock = {
        "proof": "REVERSA_GATE_0_5_LIVE_BLIND_ABA",
        "gate_result": "PASS",
        "locked_at_utc": "2026-11-06T00:00:00+00:00",
        "files": {
            "evidence/live_aba_FINAL/live_aba_summary.json": {
                "sha256": sha(target),
                "bytes": target.stat().st_size,
            }
        },
    }
    (evidence / "proof-lock.json").write_text(json.dumps(lock), encoding="utf-8")

    view = load_proof_lock(evidence)
    assert view is not None
    assert view.integrity_pass is True
    assert view.file_count == 1
    assert view.files[0].matches is True

    target.write_text('{"result":"FAIL"}', encoding="utf-8")
    changed = load_proof_lock(evidence)
    assert changed is not None
    assert changed.integrity_pass is False
    assert changed.files[0].matches is False
