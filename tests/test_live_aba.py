from copy import deepcopy

from app.live_aba import ABASafetyGate, LiveIndependentVerifier, LiveMerchantState
from app.schemas import Action, Decision
from app.tools.merchant import MerchantSimulator
from app.tools.paypal_live import LivePayPalAdapter, payment_snapshot_from_order


class FakeClient:
    def __init__(self):
        self.order = {
            "id": "ORDER-X",
            "status": "COMPLETED",
            "purchase_units": [{
                "payments": {
                    "authorizations": [{
                        "id": "AUTH-X",
                        "status": "CREATED",
                        "amount": {"value": "249.00", "currency_code": "USD"},
                    }]
                }
            }],
        }

    def get_order(self, order_id):
        return deepcopy(self.order)

    def show_authorization(self, auth_id):
        auth = self.order["purchase_units"][0]["payments"]["authorizations"][0]
        return deepcopy(auth)

    def show_capture(self, capture_id):
        captures = self.order["purchase_units"][0]["payments"].get("captures", [])
        for cap in captures:
            if cap["id"] == capture_id:
                return deepcopy(cap)
        raise KeyError(capture_id)

    def capture_authorization(self, auth_id, request_id=None):
        payments = self.order["purchase_units"][0]["payments"]
        auth = payments["authorizations"][0]
        auth["status"] = "CAPTURED"
        cap = {
            "id": "CAP-X",
            "status": "COMPLETED",
            "amount": {"value": "249.00", "currency_code": "USD"},
        }
        payments["captures"] = [cap]
        return deepcopy(cap)

    def void_authorization(self, auth_id, request_id=None):
        auth = self.order["purchase_units"][0]["payments"]["authorizations"][0]
        auth["status"] = "VOIDED"
        return {}

    def refund_capture(self, capture_id, request_id=None):
        raise AssertionError("not used in Gate 0.5")


def test_created_normalizes_to_active():
    c = FakeClient()
    snap = payment_snapshot_from_order(c.get_order("ORDER-X"))
    assert snap["authorization_raw_status"] == "CREATED"
    assert snap["authorization"] == "ACTIVE"


def test_live_capture_independent_verifier():
    c = FakeClient()
    paypal = LivePayPalAdapter(c, "ORDER-X")
    merchant = MerchantSimulator(LiveMerchantState(inventory_available=True))
    d = Decision(Action.CAPTURE, 0.99)

    ok, _ = ABASafetyGate().validate(d, paypal, merchant)
    assert ok
    paypal.capture_payment()

    v = LiveIndependentVerifier(c).verify(
        order_id="ORDER-X",
        authorization_id="AUTH-X",
        expected_action=Action.CAPTURE,
        actual_action=Action.CAPTURE,
        expected_amount="249.00",
        expected_currency="USD",
    )
    assert v["result"] == "PASS"
    assert v["observed"]["capture_get_status"] == "COMPLETED"


def test_live_void_independent_verifier():
    c = FakeClient()
    paypal = LivePayPalAdapter(c, "ORDER-X")
    merchant = MerchantSimulator(
        LiveMerchantState(
            inventory_available=False,
            inventory_reserved=False,
            fulfillment_possible=False,
        )
    )
    d = Decision(Action.VOID, 0.99)

    ok, _ = ABASafetyGate().validate(d, paypal, merchant)
    assert ok
    paypal.void_authorization()

    v = LiveIndependentVerifier(c).verify(
        order_id="ORDER-X",
        authorization_id="AUTH-X",
        expected_action=Action.VOID,
        actual_action=Action.VOID,
        expected_amount="249.00",
        expected_currency="USD",
    )
    assert v["result"] == "PASS"
    assert v["observed"]["authorization_status"] == "VOIDED"


def test_wrong_capture_is_blocked_in_hidden_unavailable_world():
    c = FakeClient()
    paypal = LivePayPalAdapter(c, "ORDER-X")
    merchant = MerchantSimulator(
        LiveMerchantState(
            inventory_available=False,
            inventory_reserved=False,
            fulfillment_possible=False,
        )
    )
    ok, reason = ABASafetyGate().validate(
        Decision(Action.CAPTURE, 0.99), paypal, merchant
    )
    assert not ok
    assert "inventory unavailable" in reason.lower()


def test_wrong_void_is_blocked_in_hidden_available_world():
    c = FakeClient()
    paypal = LivePayPalAdapter(c, "ORDER-X")
    merchant = MerchantSimulator(LiveMerchantState(inventory_available=True))
    ok, reason = ABASafetyGate().validate(
        Decision(Action.VOID, 0.99), paypal, merchant
    )
    assert not ok
    assert "fulfillable" in reason.lower()
