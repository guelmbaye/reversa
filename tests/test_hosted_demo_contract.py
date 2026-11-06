from pathlib import Path
import json

WEB = Path("web")


def test_hosted_mode_falls_back_to_same_origin_route():
    source = (WEB / "lib/api.ts").read_text(encoding="utf-8")
    assert 'const configuredBase = process.env.NEXT_PUBLIC_REVERSA_API_URL?.trim()' in source
    assert '"/api/proof/final"' in source
    assert 'USES_EXTERNAL_PROOF_API' in source


def test_build_verifies_snapshot_before_next_build():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["proof:sync"] == "node scripts/export-proof.mjs"
    assert package["scripts"]["proof:verify"] == "node scripts/verify-proof.mjs"
    assert package["scripts"]["build"] == "npm run proof:verify && next build"


def test_hosted_route_serves_bundled_snapshot():
    route = (WEB / "app/api/proof/final/route.ts").read_text(encoding="utf-8")
    assert '@/data/locked-proof/final.json' in route
    assert 'LOCKED_PROOF_SNAPSHOT' in route
    assert 'X-Reversa-Snapshot-Sha256' in route


def test_export_guard_requires_final_gate_properties():
    source = (WEB / "scripts/export-proof.mjs").read_text(encoding="utf-8")
    for required in [
        'bundle.summary?.result !== "PASS"',
        'bundle.summary?.aba_flip_pass !== true',
        'bundle.summary?.all_independent_outcomes_pass !== true',
        'bundle.summary?.counterfactual_probe_paths_pass !== true',
        'bundle.summary?.unsafe_executions !== 0',
        'bundle.summary?.duplicate_financial_effects !== 0',
        'bundle.summary?.no_leak !== true',
        'bundle.proof_lock?.integrity_pass !== true',
    ]:
        assert required in source
