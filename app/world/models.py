from dataclasses import dataclass

@dataclass
class PayPalState:
    authorization: str | None = None   # ACTIVE, VOIDED, CAPTURED
    capture: str | None = None         # COMPLETED, REFUNDED
    capture_count: int = 0
    refund_count: int = 0
    lookup_available: bool = True

@dataclass
class MerchantState:
    order_exists: bool = False
    order_status: str | None = None
    inventory_available: bool = True
    inventory_reserved: bool = False
    fulfillment_possible: bool = True

@dataclass
class WorldState:
    paypal: PayPalState
    merchant: MerchantState
    webhook_complete: bool = True
