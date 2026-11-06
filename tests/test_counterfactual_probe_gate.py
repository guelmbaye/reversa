from app.live_aba import _counterfactual_probe_path_ok


def test_counterfactual_probe_path_requires_paypal_then_inventory():
    good = {
        "observations": [
            {"tool": "inspect_paypal_payment"},
            {"tool": "inspect_inventory"},
        ]
    }
    assert _counterfactual_probe_path_ok(good)


def test_counterfactual_probe_path_rejects_missing_inventory():
    bad = {
        "observations": [
            {"tool": "inspect_paypal_payment"},
        ]
    }
    assert not _counterfactual_probe_path_ok(bad)


def test_counterfactual_probe_path_rejects_wrong_order():
    bad = {
        "observations": [
            {"tool": "inspect_inventory"},
            {"tool": "inspect_paypal_payment"},
        ]
    }
    assert not _counterfactual_probe_path_ok(bad)
