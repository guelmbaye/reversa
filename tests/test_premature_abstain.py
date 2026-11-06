import pytest

from app.agent.adaptive import (
    AdaptiveReasonerError,
    AdaptiveRecoveryAgent,
    derive_legal_final_actions,
    required_decisive_probe,
)
from app.schemas import Observation


def obs(i, tool, payload):
    return Observation(id=f"obs_{i:02d}", tool=tool, payload=payload)


def make_abstain_step():
    return {
        "kind": "decide",
        "tool": None,
        "action": "ABSTAIN",
        "confidence": 0.8,
        "hypothesis_event": {
            "status": "SUPPORTED",
            "hypothesis": "Need more evidence before moving money.",
            "previous_hypothesis": None,
            "evidence_ids": ["obs_01"],
            "reason": "Authorization exists but inventory is not yet known.",
        },
        "rationale": "Abstain.",
        "evidence_ids": ["obs_01"],
        "remaining_uncertainty": ["inventory"],
    }


def test_required_probe_is_paypal_first():
    assert required_decisive_probe([]) == "inspect_paypal_payment"


def test_active_uncaptured_requires_inventory():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        })
    ]
    assert required_decisive_probe(observations) == "inspect_inventory"
    assert derive_legal_final_actions(observations) == {"ABSTAIN"}


def test_premature_abstain_rejected_when_probe_budget_remains():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        })
    ]
    agent = AdaptiveRecoveryAgent(provider=None)
    with pytest.raises(AdaptiveReasonerError, match="Premature ABSTAIN"):
        agent._validate_step(
            make_abstain_step(),
            observations,
            {"ABSTAIN"},
            {"inspect_inventory"},
            probe_budget_remaining=2,
        )


def test_abstain_allowed_when_budget_exhausted():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        })
    ]
    agent = AdaptiveRecoveryAgent(provider=None)
    agent._validate_step(
        make_abstain_step(),
        observations,
        {"ABSTAIN"},
        {"inspect_inventory"},
        probe_budget_remaining=0,
    )


def test_inventory_available_resolves_to_capture_only():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        }),
        obs(2, "inspect_inventory", {"available": True}),
    ]
    assert required_decisive_probe(observations) is None
    assert derive_legal_final_actions(observations) == {"CAPTURE"}


def test_inventory_unavailable_resolves_to_void_only():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        }),
        obs(2, "inspect_inventory", {"available": False}),
    ]
    assert required_decisive_probe(observations) is None
    assert derive_legal_final_actions(observations) == {"VOID"}
