from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "live_aba_a1.json",
    "live_aba_b.json",
    "live_aba_a2.json",
    "live_aba_summary.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Lock the verified REVERSA Gate 0.5 evidence.")
    parser.add_argument("--evidence-dir", default="evidence/live_aba_FINAL")
    parser.add_argument("--manifest", default="evidence/live_aba_manifest_FINAL.json")
    parser.add_argument("--output", default="evidence/live_aba_FINAL/proof-lock.json")
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    manifest = Path(args.manifest)
    output = Path(args.output)

    files = [evidence_dir / name for name in REQUIRED] + [manifest]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise SystemExit("Missing proof files:\n- " + "\n- ".join(missing))

    summary = json.loads((evidence_dir / "live_aba_summary.json").read_text(encoding="utf-8"))
    if summary.get("result") != "PASS":
        raise SystemExit("Refusing to lock evidence: live_aba_summary.json result is not PASS.")

    lock = {
        "proof": "REVERSA_GATE_0_5_LIVE_BLIND_ABA",
        "gate_result": "PASS",
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {
            str(path.as_posix()): {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in files
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(f"PROOF LOCKED: {output}")
    for path, meta in lock["files"].items():
        print(f"{meta['sha256']}  {path}")


if __name__ == "__main__":
    main()
