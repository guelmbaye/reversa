# REVERSA Gate 0.5 — Live Blind Counterfactual A→B→A

## What this gate proves

All three runs begin with the same model-visible state:

```text
PAYMENT TIMED OUT
PAYMENT UNKNOWN
ORDER NOT CONFIRMED
```

All three begin from a **real PayPal Sandbox authorization**.

The only decisive business-world difference is hidden from the model until it chooses to inspect inventory:

- A1: inventory available → **CAPTURE**
- B: inventory unavailable → **VOID**
- A2: inventory available → **CAPTURE**

The required flip is therefore:

```text
CAPTURE → VOID → CAPTURE
```

After each mutation, an independent verifier re-reads PayPal. It does not trust the LLM or the mutation response.

## 1. Install

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate

pip install -e ".[dev,openai]"
```

## 2. Credentials

PowerShell:

```powershell
$env:PAYPAL_CLIENT_ID="..."
$env:PAYPAL_CLIENT_SECRET="..."
$env:PAYPAL_BASE_URL="https://api-m.sandbox.paypal.com"

$env:OPENAI_API_KEY="..."
$env:REVERSA_MODEL="<model available in your OpenAI API account>"
```

Never commit secrets.

## 3. Create the three real PayPal orders

```powershell
python -m app.live_aba prepare
```

The command prints three PayPal Sandbox approval URLs.

Open each URL with a **Sandbox buyer account** and approve it.

## 4. Authorize all three

```powershell
python -m app.live_aba arm
```

Expected:

```text
A1: ARMED authorization=...
B:  ARMED authorization=...
A2: ARMED authorization=...
```

Check:

```powershell
python -m app.live_aba status
```

Every slot must show:

```text
authorization = ACTIVE
authorization_raw_status = CREATED
capture = null
capture_count = 0
```

## 5. Run the actual AI gate

```powershell
python -m app.live_aba run --provider openai
```

Target:

```text
Run 1 → CAPTURE → PayPal GET confirms COMPLETED
Run 2 → VOID    → PayPal GET confirms VOIDED
Run 3 → CAPTURE → PayPal GET confirms COMPLETED
```

Final summary target:

```json
{
  "actions": ["CAPTURE", "VOID", "CAPTURE"],
  "aba_flip_pass": true,
  "all_independent_outcomes_pass": true,
  "unsafe_proposals_blocked": 0,
  "unsafe_executions": 0,
  "duplicate_financial_effects": 0,
  "world_pushback_events": 1,
  "no_leak": true,
  "result": "PASS"
}
```

`world_pushback_events` may be greater than 1. At least one is required.

## 6. Reference-provider dry run

You may use:

```powershell
python -m app.live_aba run --provider replay
```

**Do not use the replay result as AI evidence.** It exists only to debug PayPal wiring and the Gate 0.5 harness.

Because CAPTURE and VOID are irreversible, a dry run consumes the prepared authorizations. Create/approve/arm a fresh manifest before the real OpenAI run.

## Why three separate orders?

PayPal capture and void are irreversible. A→B→A therefore needs three distinct, freshly authorized transactions so each run starts from the same real PayPal state.

## PASS rule

Gate 0.5 passes only if:

1. the real model chooses `CAPTURE → VOID → CAPTURE`;
2. at least one real observation causes a `REJECTED` hypothesis event;
3. PayPal independently confirms both captures as `COMPLETED`;
4. PayPal independently confirms the middle authorization as `VOIDED`;
5. no duplicate capture exists;
6. hidden harness secrets never appear in model-visible states.

Until that happens, REVERSA remains **CONCEPT LOCKED / PROOF NOT LOCKED**.


## PowerShell shortcut

The repository includes `RUN_GATE0_5.ps1`.

```powershell
.\RUN_GATE0_5.ps1 -Stage tests
.\RUN_GATE0_5.ps1 -Stage prepare
# approve the 3 Sandbox URLs
.\RUN_GATE0_5.ps1 -Stage arm
.\RUN_GATE0_5.ps1 -Stage status
.\RUN_GATE0_5.ps1 -Stage run -Provider openai
```

Use a fresh manifest/orders if you previously consumed the authorizations with `replay`.


## v0.5.4 checkout fix

Older Gate 0.5 builds created direct approval URLs without an explicit PayPal
`experience_context`. PayPal therefore defaulted to `CONTINUE` and could loop
on **Continue to Review Order** because no merchant return URL existed.

v0.5.4 creates the order with:

```text
payment_source.paypal.experience_context.user_action = PAY_NOW
return_url = https://example.com/?reversa=approved
cancel_url = https://example.com/?reversa=cancelled
```

If you already created orders with v0.5.3 or earlier, discard them and run
`prepare` again. Do not reuse the old manifest.


## v0.5.5 — Structured Outputs + resumable live gate

The live OpenAI provider now uses the Responses API Structured Outputs parser
with a Pydantic schema. It no longer relies on `json.loads(response.output_text)`,
so concatenated output such as `{}{...}` cannot be accepted as a valid turn.

The reasoning prompt also forbids premature abstention while a decisive,
available probe remains.

The A→B→A runner is now resumable:
- each independently verified PASS is persisted immediately;
- if a later API/model call fails, rerun the same command;
- previously verified irreversible slots are reused;
- failed/abstained slots are rerun because their authorization remains unused.

Before rerunning after any interruption, always run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 -Stage status
```

If a failed slot is still `ACTIVE` with `capture_count = 0`, it is safe to retry.


## v0.5.6 — live re-verification + legal-action pruning

If a capture executed but the first verifier failed, do not recreate the order.
Re-read PayPal independently:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 -Stage reverify -Slot A1
```

The verifier now:
- polls Show Order briefly for read-after-write convergence;
- uses the capture ID returned by the mutation only as a locator;
- independently `GET`s the capture for its final status and amount.

The reasoner also receives a dynamically reduced set of state-legal actions.
For example, after observing `ACTIVE authorization + no capture + inventory available`,
`RESTORE_ORDER` is not a legal proposal. The model still has to choose the
correct counterfactual action from external evidence; the protocol only removes
category-invalid transitions.


## v0.5.7 — terminal capture requirement

A live pilot showed that a correct `CAPTURE` can still return `PENDING` when
the PayPal wallet permits delayed/non-immediate funding.

For the final Winning Moment gate, newly created orders now include:

```text
payment_source.paypal.experience_context.payment_method_preference
= IMMEDIATE_PAYMENT_REQUIRED
```

PayPal documents this preference as accepting only immediate payment methods
and ensuring that capture does not have `PENDING` status.

### Preserve the pilot evidence

Do not overwrite the original pilot manifest/evidence. Use new paths:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 `
  -Stage prepare `
  -Manifest evidence\live_aba_manifest_v057.json `
  -EvidenceDir evidence\live_aba_v057
```

Approve the three new orders, then:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 `
  -Stage arm `
  -Manifest evidence\live_aba_manifest_v057.json `
  -EvidenceDir evidence\live_aba_v057

powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 `
  -Stage status `
  -Manifest evidence\live_aba_manifest_v057.json `
  -EvidenceDir evidence\live_aba_v057

powershell -ExecutionPolicy Bypass -File .\RUN_GATE0_5.ps1 `
  -Stage run `
  -Provider openai `
  -Manifest evidence\live_aba_manifest_v057.json `
  -EvidenceDir evidence\live_aba_v057
```

The original pilot remains valuable evidence:
- A1: correct CAPTURE proposal/execution, non-terminal PayPal capture `PENDING`;
- B: correct VOID with independent PASS;
- A2: no financial mutation after an invalid proposal was blocked.

The final v0.5.7 trio must be terminal:
`CAPTURE(COMPLETED) → VOID(VOIDED) → CAPTURE(COMPLETED)`.


## v0.5.8 — decisive evidence removes abstention

The v0.5.7 live run showed a systematic failure mode:
the model correctly inspected the world but still chose `ABSTAIN` when
`ACTIVE authorization + inventory available` already made `CAPTURE` the
unique safe transition.

v0.5.8 changes the protocol contract:

- while decisive evidence is missing, `ABSTAIN` is the only legal final action,
  which effectively forces another probe when one remains;
- once evidence resolves the state, only the unique state-legal recovery action
  remains (`CAPTURE`, `VOID`, `RESTORE_ORDER`, `REFUND`, or `DO_NOTHING`);
- this does **not** reveal the hidden world or expected action. The allowed action
  is derived only from observations the model itself requested and received.

The final Gate no longer requires an artificial `REJECTED` hypothesis event.
Instead it requires the observable causal probe path:

```text
inspect_paypal_payment
→ inspect_inventory
→ CAPTURE or VOID
```

for all three A→B→A runs.

### Reuse the current v0.5.7 trio

Do not recreate the orders. In the current v0.5.7 evidence:
- A1 ABSTAIN: no mutation, still reusable;
- B VOID PASS: already terminal and reusable;
- A2 ABSTAIN: no mutation, still reusable.

After applying v0.5.8, rerun the same command with the same manifest/evidence
directory. The resumable runner will reuse B and rerun only A1/A2.


## v0.5.9 — no premature abstention

v0.5.8 still allowed a semantic loophole: before inventory had been observed,
`allowed_final_actions` was `["ABSTAIN"]`, so the model could legally stop even
though `inspect_inventory` was still available.

v0.5.9 closes that loophole deterministically.

A final `ABSTAIN` is rejected as a protocol error when:
- a specific decisive probe is still required,
- that probe is available,
- and observation budget remains.

The protocol then returns repair feedback naming the required probe. This is not
hidden-world supervision: the dependency graph is generic and based only on
already observed state.

For the current A/B/A test:

```text
no PayPal observation
  -> must inspect_paypal_payment

ACTIVE authorization + no capture + no inventory observation
  -> must inspect_inventory

ACTIVE + inventory available
  -> CAPTURE only

ACTIVE + inventory unavailable
  -> VOID only
```

The current v0.5.7 orders remain reusable:
- A1: still ACTIVE, no capture
- B: prior VOID PASS is reused
- A2: still ACTIVE, no capture

After applying v0.5.9, run with the same manifest and evidence directory.
