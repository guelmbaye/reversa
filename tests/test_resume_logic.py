import json

from app.live_aba import _load_prior_pass


def test_prior_pass_is_reusable(tmp_path):
    d = tmp_path
    payload = {
        "decision": {"action": "CAPTURE"},
        "independent_verification": {"result": "PASS"},
        "model_visibility_audit": {"pass": True},
    }
    (d / "live_aba_a1.json").write_text(json.dumps(payload), encoding="utf-8")
    assert _load_prior_pass(d, "A1") is not None


def test_failed_prior_run_is_not_reused(tmp_path):
    d = tmp_path
    payload = {
        "decision": {"action": "ABSTAIN"},
        "independent_verification": {"result": "FAIL"},
        "model_visibility_audit": {"pass": True},
    }
    (d / "live_aba_a1.json").write_text(json.dumps(payload), encoding="utf-8")
    assert _load_prior_pass(d, "A1") is None
