from dataclasses import asdict
from app.schemas import Action
from app.world.oracle import WorldOracle
from app.tools.paypal import PayPalSimulator
from app.tools.merchant import MerchantSimulator
from app.safety.gate import SafetyGate
from app.verifier.outcome import IndependentVerifier
from app.agent.policy import BlindRecoveryPolicy

FORBIDDEN_MARKERS = [
    "lost_capture",
    "out_of_stock",
    "expected_action",
    "ground_truth",
    "scenario",
    "W1", "W2", "W3", "W4", "W5", "W6",
]

def build_tools(oracle):
    paypal = PayPalSimulator(oracle.state.paypal)
    merchant = MerchantSimulator(oracle.state.merchant)
    tools = {
        "inspect_paypal_payment": paypal.inspect,
        "inspect_merchant_order": merchant.inspect_order,
        "inspect_inventory": merchant.inspect_inventory,
        "inspect_fulfillment": merchant.inspect_fulfillment,
    }
    return paypal, merchant, tools

def execute_action(action: Action, paypal, merchant):
    if action == Action.RESTORE_ORDER:
        return merchant.restore_order()
    if action == Action.CAPTURE:
        return paypal.capture_payment()
    if action == Action.VOID:
        return paypal.void_authorization()
    if action == Action.REFUND:
        return paypal.refund_capture()
    if action in (Action.DO_NOTHING, Action.ABSTAIN):
        return {"status": "NO_EXTERNAL_EFFECT"}
    raise RuntimeError(f"Unsupported action {action}")

def visible_initial_context():
    return {
        "intent": {
            "product": "27-inch monitor",
            "quantity": 1,
            "amount": "249.00",
            "currency": "USD",
        },
        "visible_state": {
            "checkout": "TIMEOUT",
            "payment": "UNKNOWN",
            "merchant_order": "NOT_CONFIRMED",
        },
    }

def no_leak_audit(payloads: list[object]) -> dict:
    text = "\n".join(str(x) for x in payloads)
    found = [m for m in FORBIDDEN_MARKERS if m in text]
    return {
        "forbidden_markers_found": found,
        "pass": len(found) == 0,
    }

def run_world(world_id: str, policy=None, execute=True):
    oracle = WorldOracle.create(world_id)
    paypal, merchant, tools = build_tools(oracle)
    policy = policy or BlindRecoveryPolicy()

    initial = visible_initial_context()

    if isinstance(policy, BlindRecoveryPolicy):
        decision, observations = policy.run(tools, max_probes=3)
    else:
        decision, observations = policy.run(tools)

    safety = SafetyGate()
    allowed, safety_reason = safety.validate(decision, paypal, merchant)

    effect = None
    if execute and allowed:
        effect = execute_action(decision.action, paypal, merchant)

    verifier = IndependentVerifier()
    verification = verifier.verify(oracle, decision.action, paypal, merchant)

    leak = no_leak_audit([initial, [asdict(o) for o in observations], asdict(decision)])

    return {
        "initial": initial,
        "observations": [asdict(o) for o in observations],
        "decision": asdict(decision),
        "safety": {"allowed": allowed, "reason": safety_reason},
        "effect": effect,
        "verification": asdict(verification),
        "no_leak": leak,
        "ground_truth_reveal": oracle.reveal(),
    }
