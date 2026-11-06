from app.schemas import Action, Decision

class SafetyGate:
    def validate(self, decision: Decision, paypal, merchant) -> tuple[bool, str]:
        p = paypal.inspect()
        m = merchant.inspect_order()
        action = decision.action

        if action == Action.ABSTAIN:
            return True, "Abstention is always safe"

        if action == Action.DO_NOTHING:
            return True, "No external effect"

        if action == Action.CAPTURE:
            if not p.get("available"):
                return False, "PayPal state unavailable"
            if p.get("authorization") != "ACTIVE" or p.get("capture") is not None:
                return False, "Capture not legal from current state"
            inv = merchant.inspect_inventory()
            if not inv["available"]:
                return False, "Inventory unavailable"
            return True, "Capture permitted"

        if action == Action.VOID:
            if not p.get("available"):
                return False, "PayPal state unavailable"
            if p.get("authorization") != "ACTIVE" or p.get("capture") is not None:
                return False, "Void not legal from current state"
            return True, "Void permitted"

        if action == Action.REFUND:
            if not p.get("available"):
                return False, "PayPal state unavailable"
            if p.get("capture") != "COMPLETED":
                return False, "Refund requires completed capture"
            if p.get("refund_count", 0) > 0:
                return False, "Already refunded"
            return True, "Refund permitted"

        if action == Action.RESTORE_ORDER:
            if not p.get("available"):
                return False, "PayPal state unavailable"
            if p.get("capture") != "COMPLETED":
                return False, "Restore requires completed capture"
            if m["exists"]:
                return False, "Order already exists"
            if not merchant.inspect_fulfillment()["possible"]:
                return False, "Cannot restore when fulfillment impossible"
            return True, "Restore permitted"

        return False, "Unknown action"
