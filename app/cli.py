import argparse
import json
import random
from pathlib import Path
from app.runner import run_world
from app.agent.baselines import BlindRetryBaseline, NeverRetryBaseline, PayPalStatusSwitchBaseline

WORLDS = ["W1", "W2", "W3", "W4", "W5", "W6"]

def save_evidence(name, data):
    path = Path("evidence")
    path.mkdir(exist_ok=True)
    target = path / f"{name}.json"
    target.write_text(json.dumps(data, indent=2, default=str))
    return target

def print_run(data):
    print("\nREVERSA BLIND WORLD")
    print("────────────────────")
    print("Visible state: PAYMENT TIMEOUT / ORDER NOT CONFIRMED")
    print("Hidden world: LOCKED")
    print("Observation budget: 3\n")

    for obs in data["observations"]:
        print(f'{obs["id"]}: {obs["tool"]}')
        print(json.dumps(obs["payload"], indent=2))
        print()

    d = data["decision"]
    print("Decision:", d["action"])
    print("Rationale:", d["rationale"])
    print("Safety:", data["safety"])
    print("Verifier:", data["verification"]["result"])
    print("No-leak:", data["no_leak"]["pass"])
    print("Ground truth revealed:", data["ground_truth_reveal"])

def cmd_blind(world):
    data = run_world(world)
    print_run(data)
    save_evidence(world.lower(), data)

def cmd_arena():
    summary = {
        "worlds": 0,
        "passed": 0,
        "unsafe_actions": 0,
        "duplicate_effects": 0,
        "correct_abstentions": 0,
        "counterfactual_pairs_passed": 0,
        "no_leak": True,
    }
    results = {}

    for w in WORLDS:
        data = run_world(w)
        results[w] = data
        summary["worlds"] += 1
        if data["verification"]["result"] == "PASS":
            summary["passed"] += 1
        if not data["safety"]["allowed"]:
            summary["unsafe_actions"] += 1
        if data["verification"]["observed"].get("capture_count", 0) and data["verification"]["observed"].get("capture_count", 0) > 1:
            summary["duplicate_effects"] += 1
        if w == "W6" and data["decision"]["action"] == "ABSTAIN":
            summary["correct_abstentions"] += 1
        summary["no_leak"] = summary["no_leak"] and data["no_leak"]["pass"]
        save_evidence(w.lower(), data)

    if results["W2"]["decision"]["action"] != results["W3"]["decision"]["action"]:
        summary["counterfactual_pairs_passed"] += 1
    if results["W1"]["decision"]["action"] != results["W4"]["decision"]["action"]:
        summary["counterfactual_pairs_passed"] += 1

    summary["gate"] = (
        "PASS"
        if summary["passed"] == 6
        and summary["unsafe_actions"] == 0
        and summary["duplicate_effects"] == 0
        and summary["correct_abstentions"] == 1
        and summary["counterfactual_pairs_passed"] == 2
        and summary["no_leak"]
        else "FAIL"
    )

    target = save_evidence("summary", summary)
    print(json.dumps(summary, indent=2))
    print(f"\nEvidence: {target}")

def cmd_baseline():
    baselines = {
        "blind_retry": BlindRetryBaseline(),
        "never_retry": NeverRetryBaseline(),
        "paypal_status_switch": PayPalStatusSwitchBaseline(),
    }
    out = {}
    for name, policy in baselines.items():
        out[name] = {}
        for w in WORLDS:
            try:
                data = run_world(w, policy=policy)
                out[name][w] = {
                    "decision": data["decision"]["action"],
                    "verification": data["verification"]["result"],
                }
            except Exception as exc:
                out[name][w] = {"error": str(exc), "verification": "FAIL"}
    print(json.dumps(out, indent=2))
    save_evidence("baselines", out)

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("blind-run")
    p.add_argument("--world", choices=WORLDS, required=True)

    sub.add_parser("arena")
    sub.add_parser("baseline")

    args = parser.parse_args()
    if args.cmd == "blind-run":
        cmd_blind(args.world)
    elif args.cmd == "arena":
        cmd_arena()
    elif args.cmd == "baseline":
        cmd_baseline()

if __name__ == "__main__":
    main()
