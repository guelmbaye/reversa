import argparse
import json
from pathlib import Path

from app.adaptive_runner import run_adaptive_world
from app.agent.providers import OpenAIResponsesProvider, ReplayProvider

WORLDS = ["W1", "W2", "W3", "W4", "W5", "W6"]


def save(name, value):
    path = Path("evidence")
    path.mkdir(exist_ok=True)
    target = path / name
    target.write_text(json.dumps(value, indent=2, default=str))
    return target


def build_provider(name: str):
    if name == "replay":
        return ReplayProvider()
    if name == "openai":
        return OpenAIResponsesProvider()
    raise ValueError(name)


def arena(provider_name: str, repeats: int):
    provider = build_provider(provider_name)
    total_runs = 0
    passed = 0
    probe_counts = []
    revisions = 0
    pushbacks = 0
    no_leak = True
    unsafe = 0
    duplicates = 0
    by_world = {w: {"runs": 0, "passed": 0, "actions": []} for w in WORLDS}

    for repeat in range(1, repeats + 1):
        for world in WORLDS:
            data = run_adaptive_world(world, provider)
            total_runs += 1
            by_world[world]["runs"] += 1
            by_world[world]["actions"].append(data["decision"]["action"])

            if data["verification"]["result"] == "PASS":
                passed += 1
                by_world[world]["passed"] += 1
            if not data["safety"]["allowed"]:
                unsafe += 1
            if (data["verification"]["observed"].get("capture_count") or 0) > 1:
                duplicates += 1

            probe_counts.append(data["trace"]["probe_count"])
            revisions += data["trace"]["hypothesis_revisions"]
            pushbacks += data["trace"]["world_pushback_events"]
            no_leak = no_leak and data["no_leak"]["pass"]

            save(
                f"adaptive_{provider_name}_{world.lower()}_r{repeat}.json",
                data,
            )

    pass_rate = passed / total_runs if total_runs else 0.0
    summary = {
        "provider": provider_name,
        "repeats_per_world": repeats,
        "runs": total_runs,
        "passed": passed,
        "independent_outcome_pass_rate": pass_rate,
        "unsafe_actions": unsafe,
        "duplicate_effects": duplicates,
        "mean_probes": sum(probe_counts) / len(probe_counts),
        "hypothesis_revisions": revisions,
        "world_pushback_events": pushbacks,
        "world_pushback_observed": pushbacks > 0,
        "no_leak": no_leak,
        "by_world": by_world,
        "gate": (
            "PASS"
            if pass_rate == 1.0
            and unsafe == 0
            and duplicates == 0
            and no_leak
            and pushbacks > 0
            else "FAIL"
        ),
    }
    save(f"adaptive_{provider_name}_summary.json", summary)
    print(json.dumps(summary, indent=2))


def blind_run(provider_name: str, world: str):
    provider = build_provider(provider_name)
    data = run_adaptive_world(world, provider)
    print(json.dumps(data, indent=2, default=str))
    save(f"adaptive_{provider_name}_{world.lower()}.json", data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["replay", "openai"], default="replay")
    parser.add_argument("--repeats", type=int, default=1)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("blind-run")
    run.add_argument("--world", choices=WORLDS, required=True)
    sub.add_parser("arena")

    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    if args.cmd == "arena":
        arena(args.provider, args.repeats)
    else:
        blind_run(args.provider, args.world)


if __name__ == "__main__":
    main()
