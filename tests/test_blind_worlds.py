from app.runner import run_world

EXPECTED = {
    "W1": "RESTORE_ORDER",
    "W2": "CAPTURE",
    "W3": "VOID",
    "W4": "REFUND",
    "W5": "DO_NOTHING",
    "W6": "ABSTAIN",
}

def test_all_worlds_pass():
    for world, action in EXPECTED.items():
        data = run_world(world)
        assert data["decision"]["action"] == action
        assert data["verification"]["result"] == "PASS"
        assert data["no_leak"]["pass"] is True

def test_counterfactual_pairs_diverge():
    w2 = run_world("W2")
    w3 = run_world("W3")
    assert w2["initial"] == w3["initial"]
    assert w2["decision"]["action"] == "CAPTURE"
    assert w3["decision"]["action"] == "VOID"

    w1 = run_world("W1")
    w4 = run_world("W4")
    assert w1["initial"] == w4["initial"]
    assert w1["decision"]["action"] == "RESTORE_ORDER"
    assert w4["decision"]["action"] == "REFUND"
