from app.schemas import Action
from app.world.models import PayPalState, MerchantState, WorldState

def build_world(world_id: str) -> tuple[WorldState, Action]:
    worlds = {
        "W1": (
            WorldState(
                paypal=PayPalState(authorization="CAPTURED", capture="COMPLETED", capture_count=1),
                merchant=MerchantState(
                    order_exists=False,
                    inventory_available=True,
                    inventory_reserved=True,
                    fulfillment_possible=True,
                ),
            ),
            Action.RESTORE_ORDER,
        ),
        "W2": (
            WorldState(
                paypal=PayPalState(authorization="ACTIVE", capture=None, capture_count=0),
                merchant=MerchantState(
                    order_exists=False,
                    inventory_available=True,
                    inventory_reserved=True,
                    fulfillment_possible=True,
                ),
            ),
            Action.CAPTURE,
        ),
        "W3": (
            WorldState(
                paypal=PayPalState(authorization="ACTIVE", capture=None, capture_count=0),
                merchant=MerchantState(
                    order_exists=False,
                    inventory_available=False,
                    inventory_reserved=False,
                    fulfillment_possible=False,
                ),
            ),
            Action.VOID,
        ),
        "W4": (
            WorldState(
                paypal=PayPalState(authorization="CAPTURED", capture="COMPLETED", capture_count=1),
                merchant=MerchantState(
                    order_exists=False,
                    inventory_available=False,
                    inventory_reserved=False,
                    fulfillment_possible=False,
                ),
            ),
            Action.REFUND,
        ),
        "W5": (
            WorldState(
                paypal=PayPalState(authorization="CAPTURED", capture="COMPLETED", capture_count=1),
                merchant=MerchantState(
                    order_exists=True,
                    order_status="CONFIRMED",
                    inventory_available=True,
                    inventory_reserved=True,
                    fulfillment_possible=True,
                ),
            ),
            Action.DO_NOTHING,
        ),
        "W6": (
            WorldState(
                paypal=PayPalState(
                    authorization=None, capture=None, capture_count=0, lookup_available=False
                ),
                merchant=MerchantState(
                    order_exists=False,
                    inventory_available=True,
                    inventory_reserved=False,
                    fulfillment_possible=True,
                ),
                webhook_complete=False,
            ),
            Action.ABSTAIN,
        ),
    }
    if world_id not in worlds:
        raise ValueError(f"Unknown world: {world_id}")
    return worlds[world_id]
