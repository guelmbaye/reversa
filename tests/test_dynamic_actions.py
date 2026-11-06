from app.agent.adaptive import derive_legal_final_actions
from app.schemas import Observation


def obs(i, tool, payload):
    return Observation(id=f"obs_{i:02d}", tool=tool, payload=payload)


def test_active_auth_requires_inventory_before_money_action():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        })
    ]
    assert derive_legal_final_actions(observations) == {"ABSTAIN"}


def test_active_auth_available_allows_capture_not_restore():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        }),
        obs(2, "inspect_inventory", {"available": True, "reserved": True}),
    ]
    actions = derive_legal_final_actions(observations)
    assert actions == {"CAPTURE"}


def test_active_auth_unavailable_allows_void():
    observations = [
        obs(1, "inspect_paypal_payment", {
            "available": True,
            "authorization": "ACTIVE",
            "capture": None,
        }),
        obs(2, "inspect_inventory", {"available": False, "reserved": False}),
    ]
    actions = derive_legal_final_actions(observations)
    assert actions == {"VOID"}
