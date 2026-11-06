from app.schemas import Action, Decision
from app.world.oracle import WorldOracle
from app.runner import build_tools
from app.safety.gate import SafetyGate

def test_cannot_capture_when_inventory_unavailable():
    oracle = WorldOracle.create("W3")
    paypal, merchant, _ = build_tools(oracle)
    ok, _ = SafetyGate().validate(
        Decision(Action.CAPTURE, 1.0), paypal, merchant
    )
    assert ok is False

def test_cannot_void_after_capture():
    oracle = WorldOracle.create("W1")
    paypal, merchant, _ = build_tools(oracle)
    ok, _ = SafetyGate().validate(
        Decision(Action.VOID, 1.0), paypal, merchant
    )
    assert ok is False

def test_cannot_restore_when_fulfillment_impossible():
    oracle = WorldOracle.create("W4")
    paypal, merchant, _ = build_tools(oracle)
    ok, _ = SafetyGate().validate(
        Decision(Action.RESTORE_ORDER, 1.0), paypal, merchant
    )
    assert ok is False
