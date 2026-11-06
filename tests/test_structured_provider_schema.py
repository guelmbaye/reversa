import pytest
from pydantic import ValidationError

from app.agent.providers import ReasonerStepSchema


def test_probe_schema_valid():
    step = ReasonerStepSchema.model_validate({
        "kind": "probe",
        "tool": "inspect_paypal_payment",
        "action": None,
        "confidence": None,
        "hypothesis_event": {
            "status": "INITIAL",
            "hypothesis": "payment may already have completed",
            "previous_hypothesis": None,
            "evidence_ids": [],
            "reason": "timeout is ambiguous",
        },
        "rationale": "Inspect external payment truth first.",
        "evidence_ids": [],
        "remaining_uncertainty": [],
    })
    assert step.kind == "probe"
    assert step.tool == "inspect_paypal_payment"


def test_schema_rejects_unknown_tool():
    with pytest.raises(ValidationError):
        ReasonerStepSchema.model_validate({
            "kind": "probe",
            "tool": "read_world_oracle",
            "hypothesis_event": {
                "status": "INITIAL",
                "hypothesis": "x",
                "previous_hypothesis": None,
                "evidence_ids": [],
                "reason": "x",
            },
            "rationale": "x",
        })


def test_decision_schema_valid():
    step = ReasonerStepSchema.model_validate({
        "kind": "decide",
        "tool": None,
        "action": "VOID",
        "confidence": 0.97,
        "hypothesis_event": {
            "status": "REVISED",
            "hypothesis": "authorized but inventory unavailable",
            "previous_hypothesis": "authorized and uncaptured",
            "evidence_ids": ["obs_01", "obs_02"],
            "reason": "inventory unavailable",
        },
        "rationale": "Release the authorization.",
        "evidence_ids": ["obs_01", "obs_02"],
        "remaining_uncertainty": [],
    })
    assert step.action == "VOID"
