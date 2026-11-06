from app.schemas import Action, Decision

class BlindRetryBaseline:
    def run(self, tools):
        return Decision(Action.CAPTURE, 1.0, rationale="Timeout => retry"), []

class NeverRetryBaseline:
    def run(self, tools):
        return Decision(Action.DO_NOTHING, 1.0, rationale="Timeout => never retry"), []

class PayPalStatusSwitchBaseline:
    def run(self, tools):
        p = tools["inspect_paypal_payment"]()
        if not p.get("available"):
            return Decision(Action.ABSTAIN, 1.0), []
        if p.get("capture") == "COMPLETED":
            return Decision(Action.RESTORE_ORDER, 1.0), []
        if p.get("authorization") == "ACTIVE":
            return Decision(Action.CAPTURE, 1.0), []
        return Decision(Action.ABSTAIN, 1.0), []
