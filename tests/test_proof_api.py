import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.server import create_app


def _make_evidence(d: Path):
    d.mkdir(parents=True)
    for slot, inventory, action in [("A1", True, "CAPTURE"), ("B", False, "VOID"), ("A2", True, "CAPTURE")]:
        payload = {
            "initial_context": {
                "intent": {"product": "monitor", "quantity": 1, "amount": "249.00", "currency": "USD"},
                "visible_state": {"checkout": "TIMEOUT", "payment": "UNKNOWN", "merchant_order": "NOT_CONFIRMED"},
            },
            "preflight": {"snapshot": {"order_id": f"O-{slot}", "authorization_id": f"A-{slot}"}},
            "observations": [
                {"id": "obs_01", "tool": "inspect_paypal_payment", "payload": {"available": True, "authorization": "ACTIVE", "capture": None}},
                {"id": "obs_02", "tool": "inspect_inventory", "payload": {"available": inventory}},
            ],
            "decision": {"action": action, "confidence": 1.0},
            "trace": {"probe_count": 2},
            "safety": {"allowed": True, "reason": "safe"},
            "effect": {"status": "COMPLETED" if action == "CAPTURE" else "VOIDED"},
            "independent_verification": {
                "result": "PASS",
                "invariants": {"action_match": True},
                "observed": {
                    "order_id": f"O-{slot}", "authorization_id": f"A-{slot}",
                    "authorization_status": "CAPTURED" if action == "CAPTURE" else "VOIDED",
                    "capture_get_status": "COMPLETED" if action == "CAPTURE" else None,
                },
            },
            "model_visibility_audit": {"pass": True},
        }
        (d / f"live_aba_{slot.lower()}.json").write_text(json.dumps(payload), encoding="utf-8")

    summary = {
        "gate": "LIVE_BLIND_COUNTERFACTUAL_ABA", "provider": "openai",
        "actions": ["CAPTURE", "VOID", "CAPTURE"], "expected_actions": ["CAPTURE", "VOID", "CAPTURE"],
        "aba_flip_pass": True, "all_independent_outcomes_pass": True,
        "unsafe_proposals_blocked": 0, "unsafe_executions": 0,
        "duplicate_financial_effects": 0, "world_pushback_events": 0,
        "counterfactual_probe_paths_pass": True, "no_leak": True, "result": "PASS",
    }
    (d / "live_aba_summary.json").write_text(json.dumps(summary), encoding="utf-8")


def test_api_serves_locked_proof(tmp_path):
    d = tmp_path / "evidence"
    _make_evidence(d)
    client = TestClient(create_app(d))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "VERIFIED_PROOF"

    final = client.get("/api/proof/final")
    assert final.status_code == 200
    body = final.json()
    assert body["summary"]["result"] == "PASS"
    assert [s["decision"] for s in body["scenarios"]] == ["CAPTURE", "VOID", "CAPTURE"]


def test_api_rejects_unknown_slot(tmp_path):
    d = tmp_path / "evidence"
    _make_evidence(d)
    client = TestClient(create_app(d))
    assert client.get("/api/proof/Z9").status_code == 404
