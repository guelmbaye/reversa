import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const proofPath = path.join(webRoot, "data", "locked-proof", "final.json");
const manifestPath = path.join(webRoot, "data", "locked-proof", "manifest.json");

function fail(message) {
  console.error(`REVERSA HOSTED PROOF VERIFY: FAIL\n${message}`);
  process.exit(1);
}

let proofText;
let manifest;
let bundle;

try {
  proofText = await readFile(proofPath, "utf8");
  manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  bundle = JSON.parse(proofText);
} catch (error) {
  fail(`Cannot read hosted proof snapshot: ${error instanceof Error ? error.message : String(error)}`);
}

if (manifest.generated !== true) fail("Snapshot has not been generated. Run `npm run proof:sync`.");

const current = createHash("sha256").update(proofText, "utf8").digest("hex");
if (current !== manifest.snapshot_sha256) {
  fail(`Snapshot hash mismatch. Expected ${manifest.snapshot_sha256}, got ${current}.`);
}

if (bundle.summary?.result !== "PASS") fail("Snapshot gate result is not PASS.");
if (bundle.summary?.aba_flip_pass !== true) fail("Snapshot A→B→A flip is not PASS.");
if (bundle.summary?.all_independent_outcomes_pass !== true) fail("Snapshot independent outcome gate is not PASS.");
if (bundle.summary?.counterfactual_probe_paths_pass !== true) fail("Snapshot causal probe gate is not PASS.");
if (bundle.summary?.unsafe_executions !== 0) fail("Snapshot unsafe executions must be 0.");
if (bundle.summary?.duplicate_financial_effects !== 0) fail("Snapshot duplicate financial effects must be 0.");
if (bundle.summary?.no_leak !== true) fail("Snapshot no-leak audit must be PASS.");
if (bundle.proof_lock?.integrity_pass !== true) fail("Snapshot source proof lock must be PASS.");

const expected = ["CAPTURE", "VOID", "CAPTURE"];
if (JSON.stringify(bundle.summary?.actions) !== JSON.stringify(expected)) {
  fail(`Unexpected action sequence: ${JSON.stringify(bundle.summary?.actions)}`);
}

console.log("REVERSA HOSTED PROOF VERIFY: PASS");
console.log(`SHA-256: ${current}`);
console.log(`Gate: ${bundle.summary.result}`);
console.log(`Actions: ${bundle.summary.actions.join(" → ")}`);
console.log(`Source proof lock: ${bundle.proof_lock.file_count}/5 files, integrity PASS`);
