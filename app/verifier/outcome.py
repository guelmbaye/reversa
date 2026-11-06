from app.schemas import Action, VerificationResult

class IndependentVerifier:
    def verify(self, oracle, actual_action: Action, paypal, merchant) -> VerificationResult:
        truth = oracle.reveal()
        p = paypal.inspect()
        m = merchant.inspect_order()
        fulfillment = merchant.inspect_fulfillment()

        invariants = {
            "no_duplicate_capture": p.get("capture_count", 0) <= 1,
            "no_multiple_refunds": p.get("refund_count", 0) <= 1,
        }

        expected = truth["expected_action"]

        if expected == Action.RESTORE_ORDER.value:
            invariants["target_outcome"] = (
                p.get("capture_count") == 1 and
                p.get("capture") == "COMPLETED" and
                m["exists"] and
                fulfillment["possible"]
            )

        elif expected == Action.CAPTURE.value:
            invariants["target_outcome"] = (
                p.get("capture_count") == 1 and
                p.get("capture") == "COMPLETED"
            )

        elif expected == Action.VOID.value:
            invariants["target_outcome"] = (
                p.get("capture_count") == 0 and
                p.get("authorization") == "VOIDED"
            )

        elif expected == Action.REFUND.value:
            invariants["target_outcome"] = (
                p.get("refund_count") == 1 and
                p.get("capture") == "REFUNDED"
            )

        elif expected == Action.DO_NOTHING.value:
            invariants["target_outcome"] = (
                p.get("capture_count") == 1 and
                m["exists"] and
                p.get("refund_count") == 0
            )

        elif expected == Action.ABSTAIN.value:
            invariants["target_outcome"] = (
                p.get("capture_count", 0) == 0 and
                p.get("refund_count", 0) == 0 and
                not m["exists"]
            )

        invariants["action_match"] = actual_action.value == expected

        result = "PASS" if all(invariants.values()) else "FAIL"

        return VerificationResult(
            result=result,
            invariants=invariants,
            observed={
                "capture_count": p.get("capture_count"),
                "capture": p.get("capture"),
                "authorization": p.get("authorization"),
                "refund_count": p.get("refund_count"),
                "order_exists": m["exists"],
                "fulfillment_possible": fulfillment["possible"],
            },
            expected_action=expected,
            actual_action=actual_action.value,
        )
