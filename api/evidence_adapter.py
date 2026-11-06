from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from api.models import (
    FinalProofBundle,
    GateSummary,
    IncidentState,
    PolicyResult,
    ProofIdentifiers,
    ProofObservation,
    ProofScenario,
    ProofLockFile,
    ProofLockView,
    VerificationView,
)

SLOTS = ("A1", "B", "A2")
FILE_BY_SLOT = {
    "A1": "live_aba_a1.json",
    "B": "live_aba_b.json",
    "A2": "live_aba_a2.json",
}


class EvidenceError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise EvidenceError(f"Evidence file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise EvidenceError(f"Evidence root must be an object: {path}")
    return payload


def _observation_result(tool: str, payload: dict[str, Any]) -> tuple[str, str]:
    if tool == "inspect_paypal_payment":
        auth = payload.get("authorization")
        capture = payload.get("capture")
        if capture:
            return "PayPal", f"CAPTURE {capture}"
        if auth:
            return "PayPal", f"AUTHORIZATION {auth}"
        if payload.get("available") is False:
            return "PayPal", "UNAVAILABLE"
        return "PayPal", "UNKNOWN"

    if tool == "inspect_inventory":
        available = payload.get("available")
        if available is True:
            return "Inventory", "AVAILABLE"
        if available is False:
            return "Inventory", "UNAVAILABLE"
        return "Inventory", "UNKNOWN"

    if tool == "inspect_merchant_order":
        exists = payload.get("exists")
        status = payload.get("status")
        if exists is True:
            return "Merchant", f"ORDER {status or 'EXISTS'}"
        if exists is False:
            return "Merchant", "ORDER MISSING"
        return "Merchant", "ORDER UNKNOWN"

    if tool == "inspect_fulfillment":
        possible = payload.get("possible")
        if possible is True:
            return "Fulfillment", "POSSIBLE"
        if possible is False:
            return "Fulfillment", "IMPOSSIBLE"
        return "Fulfillment", "UNKNOWN"

    return tool, "OBSERVED"


def _paypal_effect(data: dict[str, Any]) -> str:
    decision = str((data.get("decision") or {}).get("action", "UNKNOWN"))
    observed = ((data.get("independent_verification") or {}).get("observed") or {})
    effect = data.get("effect") or {}

    if decision == "CAPTURE":
        return str(
            observed.get("capture_get_status")
            or observed.get("capture")
            or effect.get("status")
            or "UNKNOWN"
        )
    if decision == "VOID":
        return str(observed.get("authorization_status") or effect.get("status") or "VOIDED")
    return str(effect.get("status") or "NO_EXTERNAL_EFFECT")


def adapt_scenario(slot: str, data: dict[str, Any]) -> ProofScenario:
    if slot not in SLOTS:
        raise EvidenceError(f"Unknown proof slot: {slot}")

    initial = data.get("initial_context") or {}
    intent = initial.get("intent") or {}
    visible = initial.get("visible_state") or {}
    decision = data.get("decision") or {}
    safety = data.get("safety") or {}
    verification = data.get("independent_verification") or {}
    observed = verification.get("observed") or {}
    visibility = data.get("model_visibility_audit") or {}
    trace = data.get("trace") or {}

    observations: list[ProofObservation] = []
    for raw in data.get("observations") or []:
        tool = str(raw.get("tool", "unknown"))
        payload = raw.get("payload") or {}
        source, result = _observation_result(tool, payload)
        observations.append(
            ProofObservation(
                id=str(raw.get("id", f"obs_{len(observations)+1:02d}")),
                tool=tool,
                source=source,
                result=result,
                details=payload,
            )
        )

    identifiers = ProofIdentifiers(
        order_id=observed.get("order_id") or ((data.get("preflight") or {}).get("snapshot") or {}).get("order_id"),
        authorization_id=observed.get("authorization_id") or ((data.get("preflight") or {}).get("snapshot") or {}).get("authorization_id"),
        capture_id=observed.get("capture_id") or observed.get("order_capture_id"),
    )

    return ProofScenario(
        scenario=slot,
        product=str(intent.get("product", "Unknown product")),
        quantity=int(intent.get("quantity", 1)),
        amount=str(intent.get("amount", "0.00")),
        currency=str(intent.get("currency", "USD")),
        initial_state=IncidentState(
            checkout=str(visible.get("checkout", "UNKNOWN")),
            payment=str(visible.get("payment", "UNKNOWN")),
            merchant_order=str(visible.get("merchant_order", "UNKNOWN")),
        ),
        observations=observations,
        decision=str(decision.get("action", "UNKNOWN")),
        confidence=float(decision.get("confidence", 0.0)),
        policy=PolicyResult(
            allowed=bool(safety.get("allowed", False)),
            reason=str(safety.get("reason", "")),
        ),
        paypal_effect=_paypal_effect(data),
        verification=VerificationView(
            result="PASS" if verification.get("result") == "PASS" else "FAIL",
            invariants={str(k): bool(v) for k, v in (verification.get("invariants") or {}).items()},
        ),
        verified=verification.get("result") == "PASS",
        no_leak=bool(visibility.get("pass", False)),
        probe_count=int(trace.get("probe_count", len(observations))),
        identifiers=identifiers,
    )


def load_scenario(evidence_dir: Path, slot: str) -> ProofScenario:
    if slot not in FILE_BY_SLOT:
        raise EvidenceError(f"Unknown proof slot: {slot}")
    return adapt_scenario(slot, _load_json(evidence_dir / FILE_BY_SLOT[slot]))


def load_summary(evidence_dir: Path) -> GateSummary:
    data = _load_json(evidence_dir / "live_aba_summary.json")
    try:
        return GateSummary.model_validate(data)
    except Exception as exc:
        raise EvidenceError("Final summary does not match the expected Gate 0.5 schema") from exc



def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_proof_lock(evidence_dir: Path) -> ProofLockView | None:
    lock_path = evidence_dir / "proof-lock.json"
    if not lock_path.exists():
        return None

    lock = _load_json(lock_path)
    files_raw = lock.get("files") or {}
    if not isinstance(files_raw, dict):
        raise EvidenceError("proof-lock.json files must be an object")

    repo_root = evidence_dir.resolve().parent.parent
    files: list[ProofLockFile] = []

    for raw_path, raw_meta in files_raw.items():
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        stored_sha = str(meta.get("sha256", ""))
        stored_bytes = int(meta.get("bytes", 0))
        candidate = Path(str(raw_path))
        resolved = candidate if candidate.is_absolute() else repo_root / candidate

        if resolved.exists() and resolved.is_file():
            current_sha = _sha256(resolved)
            matches = current_sha == stored_sha and resolved.stat().st_size == stored_bytes
        else:
            current_sha = "MISSING"
            matches = False

        files.append(
            ProofLockFile(
                path=str(raw_path),
                sha256=stored_sha,
                bytes=stored_bytes,
                current_sha256=current_sha,
                matches=matches,
            )
        )

    return ProofLockView(
        proof=str(lock.get("proof", "UNKNOWN")),
        gate_result=str(lock.get("gate_result", "UNKNOWN")),
        locked_at_utc=str(lock.get("locked_at_utc", "")),
        integrity_pass=bool(files) and all(item.matches for item in files),
        file_count=len(files),
        files=files,
    )

def load_final_bundle(evidence_dir: Path) -> FinalProofBundle:
    summary = load_summary(evidence_dir)
    scenarios = [load_scenario(evidence_dir, slot) for slot in SLOTS]
    return FinalProofBundle(
        summary=summary,
        scenarios=scenarios,
        proof_lock=load_proof_lock(evidence_dir),
    )
