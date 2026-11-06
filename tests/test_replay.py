from app.world.oracle import WorldOracle
from app.runner import build_tools, execute_action
from app.agent.policy import BlindRecoveryPolicy
from app.safety.gate import SafetyGate

def test_replay_becomes_noop_for_restore_case():
    oracle = WorldOracle.create("W1")
    paypal, merchant, tools = build_tools(oracle)
    policy = BlindRecoveryPolicy()

    d1, _ = policy.run(tools)
    assert d1.action.value == "RESTORE_ORDER"
    ok, _ = SafetyGate().validate(d1, paypal, merchant)
    assert ok
    execute_action(d1.action, paypal, merchant)

    d2, _ = policy.run(tools)
    assert d2.action.value == "DO_NOTHING"
    assert paypal.inspect()["capture_count"] == 1
