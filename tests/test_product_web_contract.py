from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_recovery_console_files_exist():
    for rel in [
        "package.json",
        "app/page.tsx",
        "app/globals.css",
        "components/recovery-console.tsx",
        "lib/api.ts",
        "lib/types.ts",
    ]:
        assert (WEB / rel).exists(), rel


def test_winning_moment_copy_is_present():
    text = (WEB / "components/recovery-console.tsx").read_text(encoding="utf-8")
    for phrase in [
        "RECOVER SAFELY",
        "SAME VISIBLE FAILURE",
        "REVERSA did not know the world. It had to find out.",
        "CAPTURE",
        "VOID",
        "INDEPENDENT VERIFIER",
    ]:
        assert phrase in text


def test_ui_reads_only_proof_api():
    api_text = (WEB / "lib/api.ts").read_text(encoding="utf-8")
    assert "/api/proof/final" in api_text
    assert "POST" not in api_text
