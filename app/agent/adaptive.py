from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.agent.prompts import SYSTEM_PROMPT
from app.schemas import Action, Decision, Observation


ALLOWED_PROBES = {
    "inspect_paypal_payment",
    "inspect_merchant_order",
    "inspect_inventory",
    "inspect_fulfillment",
}

ALL_ACTIONS = {a.value for a in Action}
HYPOTHESIS_STATUSES = {"INITIAL", "SUPPORTED", "REVISED", "REJECTED"}


class AdaptiveReasonerError(RuntimeError):
    pass


def _obs_map(observations: list[Observation]) -> dict[str, dict[str, Any]]:
    return {o.tool: o.payload for o in observations}


def required_decisive_probe(observations: list[Observation]) -> str | None:
    """
    Return the next probe that is logically required before a safe final action.

    This is a protocol dependency graph, not a hidden-world oracle:
    - first establish PayPal truth;
    - for an ACTIVE uncaptured authorization, establish inventory;
    - for a completed capture, establish merchant order;
    - if the order is missing after capture, establish fulfillment viability.

    None means either:
    - the observed state is already decisive, or
    - the observed external system itself is unavailable/ambiguous and ABSTAIN
      is therefore legitimate.
    """
    by_tool = _obs_map(observations)

    p = by_tool.get("inspect_paypal_payment")
    if p is None:
        return "inspect_paypal_payment"

    if not p.get("available", False):
        return None

    capture = p.get("capture")
    authorization = p.get("authorization")

    if capture == "COMPLETED":
        order = by_tool.get("inspect_merchant_order")
        if order is None:
            return "inspect_merchant_order"

        # If merchant-order observation itself says unavailable/unknown, stop.
        if order.get("available") is False:
            return None

        if order.get("exists"):
            return None

        fulfillment = by_tool.get("inspect_fulfillment")
        if fulfillment is None:
            return "inspect_fulfillment"

        if fulfillment.get("available") is False:
            return None

        return None

    if authorization == "ACTIVE" and capture is None:
        inventory = by_tool.get("inspect_inventory")
        if inventory is None:
            return "inspect_inventory"

        if inventory.get("available") is None:
            return None

        return None

    # Unknown/unsupported payment state: abstention is legitimate.
    return None


def derive_legal_final_actions(observations: list[Observation]) -> set[str]:
    """
    State-legality filter only. It never reads hidden scenario labels or expected
    actions. ABSTAIN is legal only when external evidence is unavailable or the
    state is not safely resolvable from supported transitions.
    """
    by_tool = _obs_map(observations)

    p = by_tool.get("inspect_paypal_payment")
    if p is None:
        return {"ABSTAIN"}

    if not p.get("available", False):
        return {"ABSTAIN"}

    capture = p.get("capture")
    authorization = p.get("authorization")

    if capture == "COMPLETED":
        order = by_tool.get("inspect_merchant_order")
        if order is None:
            return {"ABSTAIN"}
        if order.get("available") is False:
            return {"ABSTAIN"}
        if order.get("exists"):
            return {"DO_NOTHING"}

        fulfillment = by_tool.get("inspect_fulfillment")
        if fulfillment is None:
            return {"ABSTAIN"}
        if fulfillment.get("available") is False:
            return {"ABSTAIN"}
        if fulfillment.get("possible"):
            return {"RESTORE_ORDER"}
        if fulfillment.get("possible") is False:
            return {"REFUND"}
        return {"ABSTAIN"}

    if authorization == "ACTIVE" and capture is None:
        inventory = by_tool.get("inspect_inventory")
        if inventory is None:
            return {"ABSTAIN"}
        if inventory.get("available") is True:
            return {"CAPTURE"}
        if inventory.get("available") is False:
            return {"VOID"}
        return {"ABSTAIN"}

    return {"ABSTAIN"}


def allowed_probe_tools_for_state(observations: list[Observation]) -> set[str]:
    required = required_decisive_probe(observations)
    if required is not None:
        return {required}
    return set(ALLOWED_PROBES)

class AdaptiveRecoveryAgent:
    """
    Auditable active-observation loop.

    The provider can request an allowed observation or propose a final decision.
    It cannot execute financial effects and cannot access the oracle.

    v0.5.6 adds:
    - dynamically derived legal final actions from observed state;
    - up to 2 semantic repair turns if the model proposes an illegal category.
    """
    def __init__(self, provider, max_probes: int = 3, max_protocol_repairs: int = 2):
        self.provider = provider
        self.max_probes = max_probes
        self.max_protocol_repairs = max_protocol_repairs

    def run(self, tools, initial_context: dict[str, Any]) -> tuple[Decision, list[Observation], dict]:
        observations: list[Observation] = []
        hypothesis_events: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []
        protocol_feedback: list[dict[str, Any]] = []
        repairs = 0
        turn = 0

        # Probe turns + final decision + bounded semantic repair turns.
        hard_turn_limit = self.max_probes + 1 + self.max_protocol_repairs

        while turn < hard_turn_limit:
            turn += 1
            legal_actions = derive_legal_final_actions(observations)
            legal_probes = allowed_probe_tools_for_state(observations)

            state = {
                "initial_context": initial_context,
                "observation_budget": {
                    "max": self.max_probes,
                    "used": len(observations),
                    "remaining": self.max_probes - len(observations),
                },
                "allowed_probe_tools": sorted(legal_probes),
                "allowed_final_actions": sorted(legal_actions),
                "observations": [asdict(o) for o in observations],
                "hypothesis_events": hypothesis_events,
                "protocol_feedback": protocol_feedback,
            }

            step = self.provider.next_step(
                system_prompt=SYSTEM_PROMPT,
                state=state,
            )

            try:
                self._validate_step(
                    step,
                    observations,
                    legal_actions,
                    legal_probes,
                    probe_budget_remaining=(self.max_probes - len(observations)),
                )
            except AdaptiveReasonerError as exc:
                if repairs >= self.max_protocol_repairs:
                    raise
                repairs += 1
                protocol_feedback.append({
                    "turn": turn,
                    "error": str(exc),
                    "instruction": (
                        "Your proposed step violated the deterministic recovery protocol. "
                        f"Currently allowed probes: {sorted(legal_probes)}. "
                        f"Currently allowed final actions: {sorted(legal_actions)}. "
                        "Use only those values. If a decisive probe is required, request "
                        "that exact probe instead of another probe or ABSTAIN."
                    ),
                })
                continue

            event = step["hypothesis_event"]
            hypothesis_events.append({"turn": turn, **event})

            steps.append({
                "turn": turn,
                "kind": step["kind"],
                "tool": step.get("tool"),
                "action": step.get("action"),
                "legal_final_actions": sorted(legal_actions),
                "hypothesis_event": event,
                "rationale": step.get("rationale", ""),
            })

            if step["kind"] == "probe":
                if len(observations) >= self.max_probes:
                    raise AdaptiveReasonerError("Observation budget exhausted.")

                tool_name = step["tool"]
                if tool_name not in tools:
                    raise AdaptiveReasonerError(f"Tool is not available: {tool_name}")

                payload = tools[tool_name]()
                observations.append(
                    Observation(
                        id=f"obs_{len(observations)+1:02d}",
                        tool=tool_name,
                        payload=payload,
                    )
                )
                continue

            decision = Decision(
                action=Action(step["action"]),
                confidence=float(step.get("confidence", 0.0)),
                evidence=list(step.get("evidence_ids", [])),
                remaining_uncertainty=list(step.get("remaining_uncertainty", [])),
                rationale=str(step.get("rationale", "")),
            )
            trace = {
                "steps": steps,
                "hypothesis_events": hypothesis_events,
                "probe_count": len(observations),
                "protocol_repairs": repairs,
                "protocol_feedback": protocol_feedback,
                "world_pushback_events": sum(
                    1 for h in hypothesis_events if h["status"] == "REJECTED"
                ),
                "hypothesis_revisions": sum(
                    1 for h in hypothesis_events if h["status"] in {"REVISED", "REJECTED"}
                ),
            }
            return decision, observations, trace

        raise AdaptiveReasonerError("Agent did not reach a valid final decision.")

    def _validate_step(
        self,
        step: dict[str, Any],
        observations: list[Observation],
        legal_actions: set[str],
        legal_probes: set[str],
        probe_budget_remaining: int,
    ) -> None:
        if not isinstance(step, dict):
            raise AdaptiveReasonerError("Provider step must be an object.")

        kind = step.get("kind")
        if kind not in {"probe", "decide"}:
            raise AdaptiveReasonerError("kind must be 'probe' or 'decide'.")

        event = step.get("hypothesis_event")
        if not isinstance(event, dict):
            raise AdaptiveReasonerError("Every step requires hypothesis_event.")

        status = event.get("status")
        if status not in HYPOTHESIS_STATUSES:
            raise AdaptiveReasonerError(f"Invalid hypothesis status: {status}")

        if not str(event.get("hypothesis", "")).strip():
            raise AdaptiveReasonerError("hypothesis_event.hypothesis is required.")

        known_ids = {o.id for o in observations}
        cited = set(event.get("evidence_ids", []))
        if not cited.issubset(known_ids):
            raise AdaptiveReasonerError(
                f"Hypothesis event cites unknown observations: {sorted(cited - known_ids)}"
            )

        if status == "REJECTED" and not cited:
            raise AdaptiveReasonerError(
                "REJECTED requires at least one real observation as contradiction evidence."
            )

        if kind == "probe":
            tool = step.get("tool")
            if tool not in ALLOWED_PROBES:
                raise AdaptiveReasonerError(f"Forbidden probe tool: {tool}")
            if tool not in legal_probes:
                required = required_decisive_probe(observations)
                raise AdaptiveReasonerError(
                    f"Probe {tool} is not legal from current observed state. "
                    f"Required next probe: {required}. "
                    f"Allowed probes: {sorted(legal_probes)}"
                )
            if step.get("action") is not None:
                raise AdaptiveReasonerError("Probe step must not include a final action.")
            if event["status"] == "INITIAL" and event.get("evidence_ids"):
                raise AdaptiveReasonerError(
                    "INITIAL hypothesis cannot cite observations that do not exist yet."
                )
            return

        if step.get("tool") is not None:
            raise AdaptiveReasonerError("Decision step must not request a probe tool.")

        action = step.get("action")
        if action not in ALL_ACTIONS:
            raise AdaptiveReasonerError(f"Forbidden final action: {action}")

        required_probe = required_decisive_probe(observations)
        if (
            action == "ABSTAIN"
            and required_probe is not None
            and probe_budget_remaining > 0
        ):
            raise AdaptiveReasonerError(
                "Premature ABSTAIN: decisive evidence is still obtainable. "
                f"Required next probe: {required_probe}"
            )

        if action not in legal_actions:
            raise AdaptiveReasonerError(
                f"Final action {action} is not legal from current observed state. "
                f"Allowed now: {sorted(legal_actions)}"
            )

        confidence = step.get("confidence")
        if confidence is None or not 0 <= float(confidence) <= 1:
            raise AdaptiveReasonerError("confidence must be in [0, 1].")

        evidence = step.get("evidence_ids", [])
        if not isinstance(evidence, list):
            raise AdaptiveReasonerError("evidence_ids must be a list.")
        if not set(evidence).issubset(known_ids):
            raise AdaptiveReasonerError("Final decision cites unknown evidence IDs.")
