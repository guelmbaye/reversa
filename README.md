# REVERSA

## Self-healing commerce for AI agents

> A payment timeout does not tell you what happened.  
> **REVERSA checks external reality before money moves again.**

**Live demo:** https://reversa-orpin.vercel.app/  
**Source:** https://github.com/guelmbaye/reversa

REVERSA is a recovery layer for agentic commerce. When an AI checkout times out or loses certainty after a payment call, blindly retrying can create a duplicate charge, while blindly stopping can lose a valid purchase.

REVERSA does neither.

It inspects the real payment state, checks the business state required to complete the purchase safely, selects the correct recovery transition under deterministic policy, executes the allowed PayPal action, and independently verifies the final financial outcome.

---

## The problem

A network timeout is not a payment state.

After a checkout timeout, an agent may see only:

```text
PAYMENT TIMEOUT
PAYMENT UNKNOWN
MERCHANT ORDER NOT CONFIRMED
```

But the real world may be different:

- the authorization exists and inventory is still available;
- the authorization exists but inventory is now unavailable;
- a capture may already have happened;
- the merchant order may be missing even though the payment succeeded.

A retry rule cannot resolve those worlds safely.

---

## The Winning Moment

REVERSA was tested against three blind PayPal Sandbox worlds with the **same visible failure** and the **same initial PayPal payment state**.

Only the hidden business reality changed.

| Blind world | Visible symptom | PayPal state | Hidden inventory | REVERSA action | Independent outcome |
|---|---|---|---|---|---|
| A1 | PAYMENT TIMEOUT | fresh authorization | available | **CAPTURE** | **PASS — capture COMPLETED** |
| B | PAYMENT TIMEOUT | fresh authorization | unavailable | **VOID** | **PASS — authorization VOIDED** |
| A2 | PAYMENT TIMEOUT | fresh authorization | available | **CAPTURE** | **PASS — capture COMPLETED** |

### Result

```text
CAPTURE → VOID → CAPTURE
```

with:

```text
aba_flip_pass                   true
all_independent_outcomes_pass   true
counterfactual_probe_paths_pass true
unsafe_executions               0
duplicate_financial_effects     0
no_leak                         true
result                          PASS
```

The model did not receive the blind-world label, expected action, hidden inventory truth, or test secret.

**Same failure signal. Different reality. Different safe action.**

---

## Try the public demo

Open:

https://reversa-orpin.vercel.app/

The hosted console runs in **Verified Proof Mode**. It does not need PayPal or OpenAI credentials.

1. Click **REPLAY RECOVERY**.
2. Watch the recovery trace:
   - Check PayPal
   - Check inventory
   - Choose safe action
   - Safety gate
   - Real PayPal effect
   - Independent verifier
3. Click **SHOW COUNTERFACTUAL** to compare A1 → B → A2.
4. Click **VIEW PROOF** for:
   - real PayPal Sandbox IDs;
   - independent verifier invariants;
   - zero unsafe executions;
   - zero duplicate financial effects;
   - no hidden-world leak;
   - SHA-256 proof-lock integrity.

The public UI is read-only. It replays cryptographically locked evidence from the successful live Gate rather than exposing financial credentials in the browser.

---

## How REVERSA works

```text
                 CHECKOUT LOSES CERTAINTY
                          │
                          ▼
                ┌───────────────────┐
                │      REVERSA      │
                └─────────┬─────────┘
                          │
                  1. inspect reality
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
       PayPal payment             Business state
       authorization              inventory/order/
       capture/refund             fulfillment
             │                         │
             └────────────┬────────────┘
                          ▼
                   AI RECONSTRUCTS
                          │
                          ▼
                DETERMINISTIC POLICY
                          │
                allow / block action
                          │
                          ▼
                     PAYPAL EFFECT
                          │
                          ▼
                INDEPENDENT RE-READ
                          │
                          ▼
                    VERIFIED OUTCOME
```

### Separation of responsibilities

**AI reasons.**  
The model decides which observation is needed next and reconstructs the transaction state from external evidence.

**Deterministic policy authorizes.**  
The model cannot directly execute unrestricted financial calls. State-legality rules constrain the available recovery transition.

**PayPal executes.**  
Money-moving effects use the PayPal Sandbox Payments/Orders APIs.

**Independent evidence verifies.**  
After mutation, REVERSA re-reads PayPal rather than trusting the agent's own claim that the action succeeded.

---

## Why this is different from idempotency

PayPal already supports request-level idempotency through `PayPal-Request-Id`.

REVERSA solves a different problem:

> **Which action is correct now?**

When payment state and merchant state diverge, the safe recovery may be:

- `CAPTURE`
- `VOID`
- `RESTORE_ORDER`
- `REFUND`
- `DO_NOTHING`
- `ABSTAIN`

Idempotency can make a repeated API request safer. It cannot, by itself, decide whether the correct recovery is to capture an authorization, void it, restore a missing order, refund a completed payment, or do nothing.

---

## Safety architecture

REVERSA uses four boundaries:

1. **Blind-world isolation**  
   Hidden scenario metadata and expected actions never enter the model-visible state.

2. **Probe dependency graph**  
   The reasoner must establish payment truth before asking the business-state question required by that payment state.

3. **Deterministic safety gate**  
   A financial proposal is executed only if the observed state permits it.

4. **Independent verification**  
   PayPal is read again after the effect to validate the actual financial world.

The final live A→B→A run produced:

```text
unsafe executions             0
duplicate financial effects   0
hidden-world leak             none
```

---

## Evidence integrity

After the successful live Gate, the five source evidence files were frozen with SHA-256 hashes.

The Recovery Console's **Proof Drawer** recalculates and displays the integrity state.

The Vercel deployment contains a read-only snapshot exported from that locked evidence. Its build fails if the hosted snapshot no longer matches its manifest.

---

## Tech stack

### Recovery engine
- Python 3.11+
- OpenAI Responses API with Structured Outputs
- Pydantic
- PayPal Orders v2 / Payments v2
- httpx
- pytest

### Product surface
- FastAPI read-only proof API for local/reproducible mode
- Next.js
- React
- TypeScript
- Vercel

### Evidence
- SHA-256 proof lock
- independent PayPal re-reads
- resumable irreversible A→B→A harness

---

## Repository map

```text
app/
  agent/                 adaptive reasoning + deterministic protocol
  tools/                 PayPal integration
  live_aba.py            live blind A→B→A gate

api/
  evidence_adapter.py    locked proof → product model
  server.py              read-only FastAPI proof API

evidence/
  live_aba_FINAL/        final locked live evidence
  live_aba_manifest_FINAL.json

web/
  app/                   Next.js hosted application
  components/            Recovery Console + Proof Drawer
  data/locked-proof/     deployable verified snapshot
  scripts/               proof export + SHA-256 verification

tests/
  protocol, safety, proof, product and hosted-demo tests
```

---

## Run locally

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,openai]"
```

### Verify locked evidence

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFY_GATE0_5_LOCK.ps1
```

Expected:

```text
PROOF LOCK: PASS
Verified 5 locked files.
```

### Start local proof API

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_API.ps1
```

### Start frontend

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_WEB.ps1
```

Open `http://127.0.0.1:3000`.

---

## Reproduce the live PayPal Sandbox gate

The hosted demo does **not** execute new financial actions.

To reproduce the underlying experiment, configure locally:

```text
PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
OPENAI_API_KEY
REVERSA_MODEL
```

Then follow `GATE_0_5_RUNBOOK.md`.

Final target:

```text
A1 → CAPTURE → COMPLETED
B  → VOID    → VOIDED
A2 → CAPTURE → COMPLETED
```

---

## What is proven — and what is not

### Proven
- adaptive counterfactual action selection;
- real PayPal Sandbox financial effects;
- independent outcome verification;
- zero unsafe executions in the final run;
- zero duplicate financial effects;
- no hidden-world leak;
- cryptographically locked final evidence.

### Current limitations
- PayPal is Sandbox, not production money.
- Hidden merchant inventory is controlled by the blind test harness.
- The public Vercel experience is a verified replay, not a live financial endpoint.
- Production use would require authenticated merchant inventory/order/fulfillment connectors.

---

## North star

> **One intended purchase. One correct financial outcome. Even when the transaction breaks halfway.**

Agentic commerce needs more than payment initiation.

**It needs recovery.**

---

## License

MIT
