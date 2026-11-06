import pytest
from app.agent.adaptive import AdaptiveReasonerError, AdaptiveRecoveryAgent, allowed_probe_tools_for_state
from app.schemas import Observation

def obs(i, tool, payload):
    return Observation(id=f"obs_{i:02d}", tool=tool, payload=payload)

def step(tool):
    return {
        "kind": "probe",
        "tool": tool,
        "action": None,
        "confidence": None,
        "hypothesis_event": {
            "status": "SUPPORTED",
            "hypothesis": "continue investigation",
            "previous_hypothesis": None,
            "evidence_ids": ["obs_01"],
            "reason": "need decisive evidence",
        },
        "rationale": "probe",
        "evidence_ids": ["obs_01"],
        "remaining_uncertainty": [],
    }

def test_start_allows_only_paypal_probe():
    assert allowed_probe_tools_for_state([]) == {"inspect_paypal_payment"}

def test_active_uncaptured_allows_only_inventory_probe():
    observations = [obs(1, "inspect_paypal_payment", {
        "available": True, "authorization": "ACTIVE", "capture": None
    })]
    assert allowed_probe_tools_for_state(observations) == {"inspect_inventory"}

def test_wrong_probe_rejected():
    observations = [obs(1, "inspect_paypal_payment", {
        "available": True, "authorization": "ACTIVE", "capture": None
    })]
    agent = AdaptiveRecoveryAgent(provider=None)
    with pytest.raises(AdaptiveReasonerError, match="inspect_inventory"):
        agent._validate_step(
            step("inspect_merchant_order"),
            observations,
            {"ABSTAIN"},
            {"inspect_inventory"},
            probe_budget_remaining=2,
        )

def test_required_probe_accepted():
    observations = [obs(1, "inspect_paypal_payment", {
        "available": True, "authorization": "ACTIVE", "capture": None
    })]
    agent = AdaptiveRecoveryAgent(provider=None)
    agent._validate_step(
        step("inspect_inventory"),
        observations,
        {"ABSTAIN"},
        {"inspect_inventory"},
        probe_budget_remaining=2,
    )
