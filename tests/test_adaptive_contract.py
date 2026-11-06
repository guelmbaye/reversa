import pytest

from app.agent.adaptive import AdaptiveRecoveryAgent, AdaptiveReasonerError


class BadProvider:
    def __init__(self, payload):
        self.payload = payload
    def next_step(self, **kwargs):
        return self.payload


def test_forbidden_tool_rejected():
    agent = AdaptiveRecoveryAgent(
        BadProvider({
            "kind": "probe",
            "tool": "read_world_oracle",
            "hypothesis": "cheat",
            "rationale": "cheat",
        })
    )
    with pytest.raises(AdaptiveReasonerError):
        agent.run({}, {"visible_state": "TIMEOUT"})


def test_forbidden_action_rejected():
    agent = AdaptiveRecoveryAgent(
        BadProvider({
            "kind": "decide",
            "action": "SEND_MONEY",
            "confidence": 1.0,
            "evidence_ids": [],
        })
    )
    with pytest.raises(AdaptiveReasonerError):
        agent.run({}, {"visible_state": "TIMEOUT"})
