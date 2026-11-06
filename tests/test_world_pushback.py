from app.adaptive_runner import run_adaptive_world
from app.agent.providers import ReplayProvider


def test_authorized_world_rejects_initial_captured_hypothesis():
    data = run_adaptive_world("W2", ReplayProvider())
    rejected = [
        e for e in data["trace"]["hypothesis_events"]
        if e["status"] == "REJECTED"
    ]
    assert len(rejected) >= 1
    assert rejected[0]["evidence_ids"] == ["obs_01"]
    assert data["decision"]["action"] == "CAPTURE"


def test_captured_world_does_not_fake_rejection():
    data = run_adaptive_world("W1", ReplayProvider())
    assert data["trace"]["world_pushback_events"] == 0
    assert data["decision"]["action"] == "RESTORE_ORDER"
