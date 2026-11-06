from app.tools.paypal_live import payment_snapshot_from_order

def test_authorized_order_snapshot():
    payload = {
        "id": "ORDER1",
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "authorizations": [{
                    "id": "AUTH1",
                    "status": "CREATED"
                }]
            }
        }]
    }
    s = payment_snapshot_from_order(payload)
    assert s["order_id"] == "ORDER1"
    assert s["authorization_id"] == "AUTH1"
    assert s["authorization"] == "ACTIVE"
    assert s["authorization_raw_status"] == "CREATED"
    assert s["capture_id"] is None
    assert s["capture_count"] == 0

def test_captured_order_snapshot():
    payload = {
        "id": "ORDER2",
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "authorizations": [{
                    "id": "AUTH2",
                    "status": "CAPTURED"
                }],
                "captures": [{
                    "id": "CAP2",
                    "status": "COMPLETED"
                }]
            }
        }]
    }
    s = payment_snapshot_from_order(payload)
    assert s["authorization"] == "CAPTURED"
    assert s["capture"] == "COMPLETED"
    assert s["capture_id"] == "CAP2"
    assert s["capture_count"] == 1


def test_pending_capture_exposes_status_reason():
    payload = {
        "id": "ORDER-P",
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "authorizations": [{
                    "id": "AUTH-P",
                    "status": "CAPTURED"
                }],
                "captures": [{
                    "id": "CAP-P",
                    "status": "PENDING",
                    "status_details": {"reason": "PENDING_REVIEW"}
                }]
            }
        }]
    }
    s = payment_snapshot_from_order(payload)
    assert s["capture"] == "PENDING"
    assert s["capture_status_reason"] == "PENDING_REVIEW"
