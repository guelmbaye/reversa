class MerchantSimulator:
    def __init__(self, state):
        self.state = state

    def inspect_order(self) -> dict:
        return {
            "exists": self.state.order_exists,
            "status": self.state.order_status,
        }

    def inspect_inventory(self) -> dict:
        return {
            "available": self.state.inventory_available,
            "reserved": self.state.inventory_reserved,
        }

    def inspect_fulfillment(self) -> dict:
        return {"possible": self.state.fulfillment_possible}

    def restore_order(self) -> dict:
        if self.state.order_exists:
            return {"status": "ALREADY_EXISTS"}
        if not self.state.fulfillment_possible:
            raise RuntimeError("Cannot restore order when fulfillment is impossible")
        self.state.order_exists = True
        self.state.order_status = "CONFIRMED"
        return {"status": "CONFIRMED"}
