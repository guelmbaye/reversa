from copy import deepcopy

from app.agent.providers import ReplayProvider
from app.live_aba import (
    LiveIndependentVerifier,
    LiveMerchantState,
    ABASafetyGate,
    RecordingProvider,
)
from app.agent.adaptive import AdaptiveRecoveryAgent
from app.schemas import Action
from app.tools.merchant import MerchantSimulator
from app.tools.paypal_live import LivePayPalAdapter


class MultiOrderFakeClient:
    def __init__(self):
        self.orders = {}
        for slot in ("A1", "B", "A2"):
            self.orders[slot] = {
                "id": slot,
                "status": "COMPLETED",
                "purchase_units": [{
                    "payments": {
                        "authorizations": [{
                            "id": f"AUTH-{slot}",
                            "status": "CREATED",
                            "amount": {"value": "249.00", "currency_code": "USD"},
                        }]
                    }
                }],
            }

    def get_order(self, order_id):
        return deepcopy(self.orders[order_id])

    def show_authorization(self, auth_id):
        order_id = auth_id.replace("AUTH-", "")
        return deepcopy(
            self.orders[order_id]["purchase_units"][0]["payments"]["authorizations"][0]
        )

    def show_capture(self, capture_id):
        order_id = capture_id.replace("CAP-", "")
        captures = self.orders[order_id]["purchase_units"][0]["payments"]["captures"]
        return deepcopy(captures[0])

    def capture_authorization(self, auth_id, request_id=None):
        order_id = auth_id.replace("AUTH-", "")
        payments = self.orders[order_id]["purchase_units"][0]["payments"]
        payments["authorizations"][0]["status"] = "CAPTURED"
        cap = {
            "id": f"CAP-{order_id}",
            "status": "COMPLETED",
            "amount": {"value": "249.00", "currency_code": "USD"},
        }
        payments["captures"] = [cap]
        return deepcopy(cap)

    def void_authorization(self, auth_id, request_id=None):
        order_id = auth_id.replace("AUTH-", "")
        self.orders[order_id]["purchase_units"][0]["payments"]["authorizations"][0]["status"] = "VOIDED"
        return {}

    def refund_capture(self, capture_id, request_id=None):
        raise AssertionError("not used")


def _run(client, slot, inventory_available):
    paypal = LivePayPalAdapter(client, slot)
    merchant = MerchantSimulator(
        LiveMerchantState(
            inventory_available=inventory_available,
            inventory_reserved=inventory_available,
            fulfillment_possible=inventory_available,
        )
    )
    tools = {
        "inspect_paypal_payment": paypal.inspect,
        "inspect_merchant_order": merchant.inspect_order,
        "inspect_inventory": merchant.inspect_inventory,
        "inspect_fulfillment": merchant.inspect_fulfillment,
    }

    provider = RecordingProvider(ReplayProvider())
    agent = AdaptiveRecoveryAgent(provider, max_probes=3)
    decision, observations, trace = agent.run(
        tools,
        {
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
        },
    )

    allowed, _ = ABASafetyGate().validate(decision, paypal, merchant)
    assert allowed

    if decision.action == Action.CAPTURE:
        paypal.capture_payment()
    elif decision.action == Action.VOID:
        paypal.void_authorization()
    else:
        raise AssertionError(decision.action)

    expected = Action.CAPTURE if inventory_available else Action.VOID
    verification = LiveIndependentVerifier(client).verify(
        order_id=slot,
        authorization_id=f"AUTH-{slot}",
        expected_action=expected,
        actual_action=decision.action,
        expected_amount="249.00",
        expected_currency="USD",
    )
    return decision.action.value, verification, trace


def test_full_live_style_aba_integration():
    client = MultiOrderFakeClient()

    a1, va1, ta1 = _run(client, "A1", True)
    b, vb, tb = _run(client, "B", False)
    a2, va2, ta2 = _run(client, "A2", True)

    assert [a1, b, a2] == ["CAPTURE", "VOID", "CAPTURE"]
    assert [va1["result"], vb["result"], va2["result"]] == ["PASS", "PASS", "PASS"]
    assert ta1["world_pushback_events"] >= 1
    assert tb["world_pushback_events"] >= 1
    assert ta2["world_pushback_events"] >= 1
