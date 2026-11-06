import argparse
import json

from app.tools.paypal_live import PayPalRestClient, payment_snapshot_from_order

def dump(value):
    print(json.dumps(value, indent=2, default=str))

def main():
    parser = argparse.ArgumentParser(description="REVERSA PayPal Sandbox utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create-order")
    create.add_argument("--amount", default="249.00")
    create.add_argument("--currency", default="USD")

    getp = sub.add_parser("get-order")
    getp.add_argument("--order-id", required=True)

    auth = sub.add_parser("authorize")
    auth.add_argument("--order-id", required=True)

    cap = sub.add_parser("capture")
    cap.add_argument("--authorization-id", required=True)

    void = sub.add_parser("void")
    void.add_argument("--authorization-id", required=True)

    refund = sub.add_parser("refund")
    refund.add_argument("--capture-id", required=True)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--order-id", required=True)

    args = parser.parse_args()
    client = PayPalRestClient()

    if args.cmd == "create-order":
        result = client.create_authorize_order(
            amount=args.amount,
            currency=args.currency,
        )
        dump(result)
        print("\nNEXT:")
        print("1. Open approve_url in a Sandbox buyer session and approve.")
        print("2. Run: python -m app.paypal_cli authorize --order-id <ORDER_ID>")

    elif args.cmd == "get-order":
        dump(client.get_order(args.order_id))

    elif args.cmd == "authorize":
        dump(client.authorize_order(args.order_id))

    elif args.cmd == "capture":
        dump(client.capture_authorization(args.authorization_id))

    elif args.cmd == "void":
        dump(client.void_authorization(args.authorization_id))

    elif args.cmd == "refund":
        dump(client.refund_capture(args.capture_id))

    elif args.cmd == "snapshot":
        dump(payment_snapshot_from_order(client.get_order(args.order_id)))

if __name__ == "__main__":
    main()
