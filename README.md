# REVERSA — Gate 0 Blind World Spike

This repository validates the core Winning Moment thesis before building the full product.

## Goal

Starting from the same visible symptom:

```text
PAYMENT TIMED OUT
ORDER NOT CONFIRMED
```

REVERSA must discover the hidden transaction reality and reach the independently verified safe outcome:

- W1 → RESTORE_ORDER
- W2 → CAPTURE
- W3 → VOID
- W4 → REFUND
- W5 → DO_NOTHING
- W6 → ABSTAIN

The agent must **not** receive the world/scenario ID, expected action, hidden truth, or test seed.

## Run

```bash
python -m app.cli arena
python -m app.cli blind-run --world W3
python -m app.cli baseline
pytest -q
```

`--world` is only a harness/developer selector. The selected world ID is never passed into the agent context.

## Gate 0 current scope

This version uses a deterministic PayPal simulator to validate:

1. hidden-world isolation,
2. adaptive observations,
3. counterfactual decisions,
4. safety rules,
5. independent verification,
6. replay/idempotence,
7. no-leak guarantees.

The next step is replacing `PayPalSimulator` with a real PayPal Sandbox adapter while keeping the same tool contract.


## PayPal Sandbox adapter (v0.2)

The repository now includes a real REST adapter using the current PayPal REST endpoints.

Install:

```bash
pip install -e ".[dev]"
```

Set credentials (never commit them):

```bash
export PAYPAL_CLIENT_ID="..."
export PAYPAL_CLIENT_SECRET="..."
export PAYPAL_BASE_URL="https://api-m.sandbox.paypal.com"
```

Create an `AUTHORIZE` order:

```bash
python -m app.paypal_cli create-order --amount 249.00 --currency USD
```

Open the returned `approve_url` using a Sandbox buyer account and approve the purchase. Then:

```bash
python -m app.paypal_cli authorize --order-id <ORDER_ID>
python -m app.paypal_cli snapshot --order-id <ORDER_ID>
```

For a live W2/W3 starting point, stop after authorization.

For a live W1/W4/W5 starting point, capture the authorization:

```bash
python -m app.paypal_cli capture --authorization-id <AUTHORIZATION_ID>
python -m app.paypal_cli snapshot --order-id <ORDER_ID>
```

The live Gate 0 adapter intentionally re-reads `GET /v2/checkout/orders/{id}` after a lost/ignored response. This is the external truth source for the payment side of the blind world.

### Lost-response injection

For the W1 proof, do **not** fake PayPal success. Call the real capture endpoint, intentionally discard/withhold the successful HTTP response from the local checkout state, and then let REVERSA re-inspect the order. The local UI remains `UNKNOWN`; PayPal independently says the capture is complete.

### Security

- Never put `PAYPAL_CLIENT_SECRET` in the browser or repository.
- Never expose hidden world metadata to the reasoner.
- Use `PayPal-Request-Id` on mutating calls.
- The payer approval step is real and remains outside the recovery agent.


## Adaptive Reasoner (v0.3)

Gate 0.3 adds a real active-observation orchestration loop.

The provider is allowed to do only two things:

1. request one probe from the fixed allow-list;
2. propose one final action.

The provider can never execute PayPal or merchant mutations. The deterministic Safety Gate remains authoritative.

Run the reference adaptive provider:

```bash
python -m app.adaptive_cli --provider replay arena
```

This provider is deliberately deterministic and exists to validate the orchestrator contract.

### Live LLM evaluation

Install the optional OpenAI provider:

```bash
pip install -e ".[openai,dev]"
```

Set:

```bash
export OPENAI_API_KEY="..."
export REVERSA_MODEL="<model available in your API account>"
```

Then:

```bash
python -m app.adaptive_cli --provider openai blind-run --world W3
python -m app.adaptive_cli --provider openai arena
```

The provider uses the Responses API as a stateless next-step reasoner. REVERSA itself owns the tool loop, probe budget, observation history, no-leak boundary, safety gate, and independent verifier.

The live LLM Gate passes only if all six hidden worlds independently verify with:

- 0 unsafe actions
- 0 duplicate financial effects
- no hidden-world leakage
- <= 3 probes per run
- correct counterfactual divergence

Do not treat the deterministic `replay` result as evidence that the AI thesis has passed. It validates the environment and orchestration only.


## World Pushback instrumentation (v0.4)

A hypothesis change is no longer automatically counted as evidence of causal adaptation.

Each reasoning step now emits one of:

- `INITIAL`
- `SUPPORTED`
- `REVISED`
- `REJECTED`

A `REJECTED` event is accepted only when it cites an observation already returned by the external world.

Example:

```text
INITIAL:
"the payment may already have been captured"

obs_01:
PayPal => AUTHORIZATION ACTIVE, CAPTURE NONE

REJECTED:
"the payment was authorized but never captured"
because obs_01 contradicted the capture hypothesis
```

This is the measurable `THE WORLD PUSHED BACK` event.

For live model evaluation, use repeated blind runs:

```bash
python -m app.adaptive_cli --provider openai --repeats 5 arena
```

The live AI thesis should not be considered passed unless:
- independent outcome pass rate is 100% on the core six worlds,
- unsafe actions = 0,
- duplicate effects = 0,
- no-leak = true,
- at least one genuine `REJECTED` hypothesis event is observed,
- counterfactual worlds continue to produce different correct actions.


## Gate 0.5 — Live Blind Counterfactual A→B→A

Winning Moment Rule v2 requires a real external outcome, not only the simulator.

Gate 0.5 creates three distinct PayPal Sandbox `AUTHORIZE` orders and tests:

```text
same visible timeout
same real PayPal starting state (fresh authorization)
different hidden merchant reality

A1 inventory available   -> CAPTURE
B  inventory unavailable -> VOID
A2 inventory available   -> CAPTURE
```

The model never receives A1/B/A2, expected_action, or the hidden harness secret.

After execution, REVERSA re-reads PayPal using Payments v2:
- `GET /v2/payments/authorizations/{authorization_id}`
- `GET /v2/payments/captures/{capture_id}` when captured

See `GATE_0_5_RUNBOOK.md`.

Quick path:

```bash
python -m app.live_aba prepare
# approve all three PayPal Sandbox URLs
python -m app.live_aba arm
python -m app.live_aba status
python -m app.live_aba run --provider openai
```


## v0.5.5
Structured Outputs provider, stronger investigation rules, and resumable irreversible A→B→A runs.


## v0.5.7
Final live gate orders use `IMMEDIATE_PAYMENT_REQUIRED` so successful captures must be terminal rather than `PENDING`.


## v0.5.8
Decisive observed evidence removes `ABSTAIN` from legal actions; Gate PASS now uses the actual PayPal→inventory counterfactual probe path rather than a synthetic hypothesis-rejection requirement.


## v0.5.9
Protocol-level prevention of premature abstention: if a decisive probe remains available, ABSTAIN is rejected and repaired.

## Grand Prize Build — Verified Proof API

The judge-facing product surface can run without PayPal or OpenAI credentials. It reads only the locked final Gate 0.5 evidence.

Freeze the final proof once:

```powershell
powershell -ExecutionPolicy Bypass -File .\FREEZE_GATE0_5.ps1
```

Start the read-only API:

```powershell
$env:REVERSA_EVIDENCE_DIR="evidence/live_aba_FINAL"
python -m uvicorn api.server:app --reload --port 8000
```

Endpoints:

- `GET /api/health`
- `GET /api/proof/final`
- `GET /api/proof/A1`
- `GET /api/proof/B`
- `GET /api/proof/A2`

The API never writes to the proof directory.

Verify later that the locked evidence is unchanged:

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_GATE0_5_LOCK.ps1
```

Or launch the product API directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_API.ps1
```


## Grand Prize Build — Recovery Console

Start the Proof API in one terminal:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_API.ps1
```

Start the judge-facing web console in another terminal:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_WEB.ps1
```

Open `http://127.0.0.1:3000` and click **RECOVER SAFELY**. The frontend only reads the locked `FINAL` proof through `/api/proof/final`; it cannot execute financial actions.
