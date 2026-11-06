class PayPalSimulator:
    def __init__(self, state):
        self.state = state

    def inspect(self) -> dict:
        if not self.state.lookup_available:
            return {"available": False}
        return {
            "available": True,
            "authorization": self.state.authorization,
            "capture": self.state.capture,
            "capture_count": self.state.capture_count,
            "refund_count": self.state.refund_count,
        }

    def capture_payment(self) -> dict:
        if self.state.authorization != "ACTIVE":
            raise RuntimeError("No active authorization to capture")
        if self.state.capture == "COMPLETED":
            raise RuntimeError("Capture already completed")
        self.state.authorization = "CAPTURED"
        self.state.capture = "COMPLETED"
        self.state.capture_count += 1
        return {"status": "COMPLETED"}

    def void_authorization(self) -> dict:
        if self.state.authorization != "ACTIVE":
            raise RuntimeError("No active authorization to void")
        if self.state.capture == "COMPLETED":
            raise RuntimeError("Cannot void after capture")
        self.state.authorization = "VOIDED"
        return {"status": "VOIDED"}

    def refund_capture(self) -> dict:
        if self.state.capture != "COMPLETED":
            raise RuntimeError("No completed capture to refund")
        if self.state.refund_count > 0:
            return {"status": "ALREADY_REFUNDED"}
        self.state.capture = "REFUNDED"
        self.state.refund_count += 1
        return {"status": "REFUNDED"}
