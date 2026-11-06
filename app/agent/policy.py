from app.schemas import Action, Observation, Decision

class BlindRecoveryPolicy:
    """
    Deterministic reference policy for Gate 0 environment validation.

    This is intentionally NOT the final AI reasoner.
    It proves the environment can support:
      - hidden-state discovery
      - adaptive observations
      - counterfactual action changes
      - abstention
      - independent verification

    The LLM/agent is connected only after this harness passes.
    """

    def run(self, tools, max_probes: int = 3) -> tuple[Decision, list[Observation]]:
        obs: list[Observation] = []
        counter = 0

        def probe(name, fn):
            nonlocal counter
            if counter >= max_probes:
                raise RuntimeError("Observation budget exhausted")
            counter += 1
            payload = fn()
            ob = Observation(id=f"obs_{counter:02d}", tool=name, payload=payload)
            obs.append(ob)
            return ob

        p = probe("inspect_paypal_payment", tools["inspect_paypal_payment"])

        if not p.payload.get("available", False):
            return Decision(
                action=Action.ABSTAIN,
                confidence=0.99,
                evidence=[p.id],
                remaining_uncertainty=["paypal_state_unavailable"],
                rationale="Financial state cannot be established safely.",
            ), obs

        capture = p.payload.get("capture")
        authorization = p.payload.get("authorization")

        if capture == "COMPLETED":
            order = probe("inspect_merchant_order", tools["inspect_merchant_order"])
            if order.payload["exists"]:
                return Decision(
                    action=Action.DO_NOTHING,
                    confidence=0.99,
                    evidence=[p.id, order.id],
                    rationale="Payment and merchant order are already consistent.",
                ), obs

            fulfillment = probe("inspect_fulfillment", tools["inspect_fulfillment"])
            if fulfillment.payload["possible"]:
                return Decision(
                    action=Action.RESTORE_ORDER,
                    confidence=0.99,
                    evidence=[p.id, order.id, fulfillment.id],
                    rationale="Payment completed but order is missing and fulfillment remains possible.",
                ), obs

            return Decision(
                action=Action.REFUND,
                confidence=0.99,
                evidence=[p.id, order.id, fulfillment.id],
                rationale="Payment completed but fulfillment is impossible.",
            ), obs

        if authorization == "ACTIVE" and capture is None:
            inventory = probe("inspect_inventory", tools["inspect_inventory"])
            if inventory.payload["available"]:
                return Decision(
                    action=Action.CAPTURE,
                    confidence=0.99,
                    evidence=[p.id, inventory.id],
                    rationale="Authorization exists and inventory remains available.",
                ), obs

            return Decision(
                action=Action.VOID,
                confidence=0.99,
                evidence=[p.id, inventory.id],
                rationale="Authorization exists but inventory is unavailable.",
            ), obs

        return Decision(
            action=Action.ABSTAIN,
            confidence=0.8,
            evidence=[p.id],
            remaining_uncertainty=["unsupported_payment_state"],
            rationale="No safe recovery can be inferred from the observed state.",
        ), obs
