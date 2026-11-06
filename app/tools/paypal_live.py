from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx


class PayPalAPIError(RuntimeError):
    pass


@dataclass
class Token:
    value: str
    expires_at: float


def _first_link(payload: dict, rel: str) -> str | None:
    for link in payload.get("links", []):
        if link.get("rel") == rel:
            return link.get("href")
    return None



def normalize_authorization_status(status: str | None) -> str | None:
    # Payments v2 exposes a fresh authorization as CREATED.
    # REVERSA's internal policy calls that decision-state ACTIVE.
    if status == "CREATED":
        return "ACTIVE"
    return status


def payment_snapshot_from_order(order: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize the pieces Gate 0 needs from Orders v2.
    The agent sees facts, never a precomputed recovery diagnosis.
    """
    authorizations: list[dict] = []
    captures: list[dict] = []
    refunds: list[dict] = []

    for unit in order.get("purchase_units", []):
        payments = unit.get("payments", {}) or {}
        authorizations.extend(payments.get("authorizations", []) or [])
        captures.extend(payments.get("captures", []) or [])
        refunds.extend(payments.get("refunds", []) or [])

    # Prefer the newest/last resource when more than one exists.
    auth = authorizations[-1] if authorizations else None
    capture = captures[-1] if captures else None
    refund = refunds[-1] if refunds else None

    return {
        "available": True,
        "order_id": order.get("id"),
        "order_status": order.get("status"),
        "authorization_id": auth.get("id") if auth else None,
        "authorization": normalize_authorization_status(auth.get("status")) if auth else None,
        "authorization_raw_status": auth.get("status") if auth else None,
        "capture_id": capture.get("id") if capture else None,
        "capture": capture.get("status") if capture else None,
        "capture_status_reason": (
            (capture.get("status_details") or {}).get("reason")
            if capture else None
        ),
        "refund_id": refund.get("id") if refund else None,
        "refund": refund.get("status") if refund else None,
        "capture_count": len(captures),
        "refund_count": len(refunds),
    }


class PayPalRestClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        timeout: float = 20.0,
    ):
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET")
        self.base_url = (base_url or os.getenv(
            "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
        )).rstrip("/")
        self.timeout = timeout
        self._token: Token | None = None

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET"
            )

    def _access_token(self) -> str:
        if self._token and self._token.expires_at > time.time() + 30:
            return self._token.value

        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials"},
            )
        if r.status_code >= 400:
            raise PayPalAPIError(f"OAuth {r.status_code}: {r.text}")

        data = r.json()
        self._token = Token(
            value=data["access_token"],
            expires_at=time.time() + int(data.get("expires_in", 300)),
        )
        return self._token.value

    def _headers(self, *, request_id: str | None = None) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }
        if request_id:
            h["PayPal-Request-Id"] = request_id
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        request_id: str | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
    ) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(request_id=request_id),
                json=json_body,
            )
        if r.status_code not in expected:
            raise PayPalAPIError(
                f"{method} {path} -> {r.status_code}: {r.text}"
            )
        if not r.content:
            return {}
        return r.json()

    def create_authorize_order(
        self,
        *,
        amount: str = "249.00",
        currency: str = "USD",
        reference_id: str = "REVERSA-GATE0",
    ) -> dict:
        payload = self._request(
            "POST",
            "/v2/checkout/orders",
            request_id=f"create-{uuid.uuid4()}",
            json_body={
                "intent": "AUTHORIZE",
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "brand_name": "REVERSA",
                            "shipping_preference": "NO_SHIPPING",
                            "user_action": "PAY_NOW",
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                            "return_url": "https://example.com/?reversa=approved",
                            "cancel_url": "https://example.com/?reversa=cancelled",
                        }
                    }
                },
                "purchase_units": [
                    {
                        "reference_id": reference_id,
                        "amount": {
                            "currency_code": currency,
                            "value": amount,
                        },
                    }
                ],
            },
        )
        return {
            "order_id": payload.get("id"),
            "status": payload.get("status"),
            "approve_url": (
                _first_link(payload, "payer-action")
                or _first_link(payload, "approve")
            ),
            "raw": payload,
        }

    def get_order(self, order_id: str) -> dict:
        return self._request(
            "GET",
            f"/v2/checkout/orders/{order_id}",
            expected=(200,),
        )

    def authorize_order(self, order_id: str) -> dict:
        return self._request(
            "POST",
            f"/v2/checkout/orders/{order_id}/authorize",
            request_id=f"authorize-{order_id}",
            json_body={},
            expected=(200, 201),
        )

    def capture_authorization(
        self,
        authorization_id: str,
        *,
        request_id: str | None = None,
    ) -> dict:
        return self._request(
            "POST",
            f"/v2/payments/authorizations/{authorization_id}/capture",
            request_id=request_id or f"capture-{authorization_id}",
            json_body={},
            expected=(200, 201),
        )

    def void_authorization(
        self,
        authorization_id: str,
        *,
        request_id: str | None = None,
    ) -> dict:
        return self._request(
            "POST",
            f"/v2/payments/authorizations/{authorization_id}/void",
            request_id=request_id or f"void-{authorization_id}",
            json_body={},
            expected=(200, 204),
        )

    def refund_capture(
        self,
        capture_id: str,
        *,
        request_id: str | None = None,
    ) -> dict:
        return self._request(
            "POST",
            f"/v2/payments/captures/{capture_id}/refund",
            request_id=request_id or f"refund-{capture_id}",
            json_body={},
            expected=(200, 201),
        )

    def show_authorization(self, authorization_id: str) -> dict:
        return self._request(
            "GET",
            f"/v2/payments/authorizations/{authorization_id}",
            expected=(200,),
        )

    def show_capture(self, capture_id: str) -> dict:
        return self._request(
            "GET",
            f"/v2/payments/captures/{capture_id}",
            expected=(200,),
        )


class LivePayPalAdapter:
    """
    Gate-0 tool adapter backed by a real PayPal Sandbox order.

    Important:
    - order_id is legitimate transaction context, not hidden-world metadata.
    - inspect() re-reads Orders v2 instead of trusting a previous local response.
    - mutation IDs are discovered from the live order state.
    """
    def __init__(self, client: PayPalRestClient, order_id: str):
        self.client = client
        self.order_id = order_id

    def inspect(self) -> dict:
        try:
            order = self.client.get_order(self.order_id)
            return payment_snapshot_from_order(order)
        except PayPalAPIError as exc:
            return {
                "available": False,
                "error": str(exc),
                "capture_count": 0,
                "refund_count": 0,
            }

    def capture_payment(self) -> dict:
        state = self.inspect()
        auth_id = state.get("authorization_id")
        if not auth_id:
            raise RuntimeError("No live authorization ID available")
        return self.client.capture_authorization(
            auth_id,
            request_id=f"reversa-aba-capture-{self.order_id}",
        )

    def void_authorization(self) -> dict:
        state = self.inspect()
        auth_id = state.get("authorization_id")
        if not auth_id:
            raise RuntimeError("No live authorization ID available")
        return self.client.void_authorization(
            auth_id,
            request_id=f"reversa-aba-void-{self.order_id}",
        )

    def refund_capture(self) -> dict:
        state = self.inspect()
        capture_id = state.get("capture_id")
        if not capture_id:
            raise RuntimeError("No live capture ID available")
        return self.client.refund_capture(capture_id)
