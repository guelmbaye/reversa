from app.tools.paypal_live import PayPalRestClient

class FakeClient(PayPalRestClient):
    def __init__(self):
        self.client_id = "x"
        self.client_secret = "y"
        self.base_url = "https://api-m.sandbox.paypal.com"
        self.timeout = 1
        self._token = None
        self.last = None

    def _request(self, method, path, *, json_body=None, request_id=None, expected=(200,201,204)):
        self.last = {
            "method": method,
            "path": path,
            "json_body": json_body,
            "request_id": request_id,
        }
        return {
            "id": "ORDER123",
            "status": "PAYER_ACTION_REQUIRED",
            "links": [
                {
                    "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER123",
                    "rel": "payer-action",
                    "method": "GET",
                }
            ],
        }

def test_create_order_uses_pay_now_and_return_url():
    c = FakeClient()
    result = c.create_authorize_order()
    body = c.last["json_body"]
    ctx = body["payment_source"]["paypal"]["experience_context"]

    assert body["intent"] == "AUTHORIZE"
    assert ctx["user_action"] == "PAY_NOW"
    assert ctx["payment_method_preference"] == "IMMEDIATE_PAYMENT_REQUIRED"
    assert ctx["return_url"].startswith("https://")
    assert ctx["cancel_url"].startswith("https://")
    assert result["approve_url"].startswith("https://www.sandbox.paypal.com/")
