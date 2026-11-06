from app.adaptive_runner import run_adaptive_world
from app.agent.providers import ReplayProvider

EXPECTED = {
    "W1": "RESTORE_ORDER",
    "W2": "CAPTURE",
    "W3": "VOID",
    "W4": "REFUND",
    "W5": "DO_NOTHING",
    "W6": "ABSTAIN",
}

def test_adaptive_reference_provider_all_worlds():
    for world, expected in EXPECTED.items():
        data = run_adaptive_world(world, ReplayProvider())
        assert data["decision"]["action"] == expected
        assert data["verification"]["result"] == "PASS"
        assert data["no_leak"]["pass"]
        assert data["trace"]["probe_count"] <= 3

def test_adaptive_counterfactual_same_initial_different_actions():
    w2 = run_adaptive_world("W2", ReplayProvider())
    w3 = run_adaptive_world("W3", ReplayProvider())
    assert w2["initial"] == w3["initial"]
    assert w2["decision"]["action"] == "CAPTURE"
    assert w3["decision"]["action"] == "VOID"

    w1 = run_adaptive_world("W1", ReplayProvider())
    w4 = run_adaptive_world("W4", ReplayProvider())
    assert w1["initial"] == w4["initial"]
    assert w1["decision"]["action"] == "RESTORE_ORDER"
    assert w4["decision"]["action"] == "REFUND"

def test_observation_paths_are_adaptive():
    w2 = run_adaptive_world("W2", ReplayProvider())
    w1 = run_adaptive_world("W1", ReplayProvider())

    tools_w2 = [o["tool"] for o in w2["observations"]]
    tools_w1 = [o["tool"] for o in w1["observations"]]

    assert tools_w2 == ["inspect_paypal_payment", "inspect_inventory"]
    assert tools_w1 == [
        "inspect_paypal_payment",
        "inspect_merchant_order",
        "inspect_fulfillment",
    ]
