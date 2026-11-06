import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_verify_lock_detects_tamper(tmp_path):
    evidence = tmp_path / "proof.json"
    evidence.write_text('{"result":"PASS"}', encoding="utf-8")
    lock = tmp_path / "proof-lock.json"
    lock.write_text(json.dumps({
        "files": {
            str(evidence.as_posix()): {"sha256": _hash(evidence), "bytes": evidence.stat().st_size}
        }
    }), encoding="utf-8")

    ok = subprocess.run(
        [sys.executable, "scripts/verify_gate05_lock.py", "--lock", str(lock)],
        capture_output=True, text=True,
    )
    assert ok.returncode == 0
    assert "PROOF LOCK: PASS" in ok.stdout

    evidence.write_text('{"result":"CHANGED"}', encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, "scripts/verify_gate05_lock.py", "--lock", str(lock)],
        capture_output=True, text=True,
    )
    assert bad.returncode != 0
    assert "HASH_MISMATCH" in bad.stdout
