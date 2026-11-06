from dataclasses import asdict

from app.agent.adaptive import AdaptiveRecoveryAgent
from app.runner import (
    WorldOracle,
    build_tools,
    execute_action,
    visible_initial_context,
    no_leak_audit,
)
from app.safety.gate import SafetyGate
from app.verifier.outcome import IndependentVerifier


def run_adaptive_world(world_id: str, provider, execute: bool = True):
    oracle = WorldOracle.create(world_id)
    paypal, merchant, tools = build_tools(oracle)
    initial = visible_initial_context()

    agent = AdaptiveRecoveryAgent(provider=provider, max_probes=3)
    decision, observations, trace = agent.run(tools, initial)

    gate = SafetyGate()
    allowed, reason = gate.validate(decision, paypal, merchant)

    effect = None
    if execute and allowed:
        effect = execute_action(decision.action, paypal, merchant)

    verification = IndependentVerifier().verify(
        oracle, decision.action, paypal, merchant
    )

    leak = no_leak_audit([
        initial,
        [asdict(o) for o in observations],
        asdict(decision),
        trace,
    ])

    return {
        "initial": initial,
        "observations": [asdict(o) for o in observations],
        "decision": asdict(decision),
        "trace": trace,
        "safety": {"allowed": allowed, "reason": reason},
        "effect": effect,
        "verification": asdict(verification),
        "no_leak": leak,
        "ground_truth_reveal": oracle.reveal(),
    }
