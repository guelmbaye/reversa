from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the locked REVERSA Gate 0.5 proof files.")
    parser.add_argument("--lock", default="evidence/live_aba_FINAL/proof-lock.json")
    args = parser.parse_args()

    lock_path = Path(args.lock)
    if not lock_path.exists():
        raise SystemExit(f"Proof lock not found: {lock_path}")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for raw_path, expected in (lock.get("files") or {}).items():
        path = Path(raw_path)
        if not path.exists():
            failures.append(f"MISSING {path}")
            continue
        actual = sha256(path)
        if actual != expected.get("sha256"):
            failures.append(f"HASH_MISMATCH {path}: expected {expected.get('sha256')} got {actual}")

    if failures:
        print("PROOF LOCK: FAIL")
        for failure in failures:
            print(failure)
        raise SystemExit(1)

    print("PROOF LOCK: PASS")
    print(f"Verified {len(lock.get('files') or {})} locked files.")


if __name__ == "__main__":
    main()
