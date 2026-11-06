import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const outputDir = path.join(webRoot, "data", "locked-proof");
const proofPath = path.join(outputDir, "final.json");
const manifestPath = path.join(outputDir, "manifest.json");

const source =
  process.env.REVERSA_PROOF_SOURCE_URL?.trim() ||
  "http://127.0.0.1:8000/api/proof/final";

function fail(message) {
  console.error(`REVERSA HOSTED PROOF EXPORT: FAIL\n${message}`);
  process.exit(1);
}

function validate(bundle) {
  if (!bundle || typeof bundle !== "object") fail("Proof response is not an object.");
  if (bundle.summary?.result !== "PASS") fail("Gate summary is not PASS.");
  if (bundle.summary?.aba_flip_pass !== true) fail("A→B→A causal flip is not PASS.");
  if (bundle.summary?.all_independent_outcomes_pass !== true) {
    fail("Independent outcomes are not all PASS.");
  }
  if (bundle.summary?.counterfactual_probe_paths_pass !== true) {
    fail("Counterfactual probe paths are not PASS.");
  }
  if (bundle.summary?.unsafe_executions !== 0) fail("Unsafe executions must equal 0.");
  if (bundle.summary?.duplicate_financial_effects !== 0) {
    fail("Duplicate financial effects must equal 0.");
  }
  if (bundle.summary?.no_leak !== true) fail("Blind-world leak audit is not PASS.");

  const actions = bundle.summary?.actions || [];
  if (JSON.stringify(actions) !== JSON.stringify(["CAPTURE", "VOID", "CAPTURE"])) {
    fail(`Unexpected action sequence: ${JSON.stringify(actions)}`);
  }

  if (!Array.isArray(bundle.scenarios) || bundle.scenarios.length !== 3) {
    fail("Expected exactly 3 proof scenarios.");
  }

  for (const id of ["A1", "B", "A2"]) {
    const scenario = bundle.scenarios.find((item) => item?.scenario === id);
    if (!scenario) fail(`Missing scenario ${id}.`);
    if (scenario.verified !== true || scenario.verification?.result !== "PASS") {
      fail(`Scenario ${id} is not independently verified PASS.`);
    }
  }

  if (bundle.proof_lock?.integrity_pass !== true) {
    fail("SHA-256 source proof lock is not currently intact.");
  }
  if (bundle.proof_lock?.file_count !== 5) {
    fail(`Expected 5 locked source files, got ${bundle.proof_lock?.file_count ?? "unknown"}.`);
  }
}

const response = await fetch(source, {
  headers: { Accept: "application/json" },
});

if (!response.ok) {
  fail(`GET ${source} returned HTTP ${response.status}. Is RUN_PRODUCT_API.ps1 running?`);
}

const bundle = await response.json();
validate(bundle);

const proofText = `${JSON.stringify(bundle, null, 2)}\n`;
const sha256 = createHash("sha256").update(proofText, "utf8").digest("hex");

const manifest = {
  schema: 1,
  generated: true,
  exported_at_utc: new Date().toISOString(),
  source,
  snapshot_sha256: sha256,
  gate_result: bundle.summary.result,
  actions: bundle.summary.actions,
  source_lock_locked_at_utc: bundle.proof_lock?.locked_at_utc ?? null,
  source_lock_file_count: bundle.proof_lock?.file_count ?? 0,
};

await mkdir(outputDir, { recursive: true });
await writeFile(proofPath, proofText, "utf8");
await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log("REVERSA HOSTED PROOF EXPORT: PASS");
console.log(`Source: ${source}`);
console.log(`Snapshot: ${proofPath}`);
console.log(`SHA-256: ${sha256}`);
console.log(`Gate: ${bundle.summary.result}`);
console.log(`Actions: ${bundle.summary.actions.join(" → ")}`);
console.log(`Locked source files: ${bundle.proof_lock.file_count}`);
