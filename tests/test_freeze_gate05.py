import json
import subprocess
import sys
from pathlib import Path


def test_freeze_refuses_non_pass(tmp_path):
    evidence = tmp_path / "proof"
    evidence.mkdir()
    for name in ["live_aba_a1.json", "live_aba_b.json", "live_aba_a2.json"]:
        (evidence / name).write_text("{}", encoding="utf-8")
    (evidence / "live_aba_summary.json").write_text(json.dumps({"result": "FAIL"}), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/freeze_gate05.py", "--evidence-dir", str(evidence), "--manifest", str(manifest), "--output", str(evidence / "proof-lock.json")],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "not PASS" in (result.stdout + result.stderr)
