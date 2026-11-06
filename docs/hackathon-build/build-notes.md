# REVERSA Grand Prize Build — Build Notes

## Locked scientific core

Gate 0.5 has passed on live PayPal Sandbox evidence with the causal action sequence:

`CAPTURE → VOID → CAPTURE`

The Grand Prize build must not change the reasoner, safety policy, PayPal mutation logic, or the locked evidence. Product work consumes proof; it does not redefine proof.

## Product modes

### Verified Proof Mode
Read-only. Loads `evidence/live_aba_FINAL` and requires no OpenAI or PayPal credentials. This is the default mode for the hosted demo.

### Live Sandbox Mode
Existing Gate 0.5 runner. Requires PayPal Sandbox + OpenAI credentials and is kept for reproducibility, not as the default judge experience.

## Winning Moment

Same visible checkout failure. Hidden business reality changes. REVERSA probes reality and safely flips:

`CAPTURE → VOID → CAPTURE`

The UI must make this understandable in under 20 seconds.


## Slices 4–7 — judge-facing Recovery Console

Implemented a Next.js 16.4 / React 19.3 console that consumes the read-only Proof API.
The default screen starts from the ambiguous timeout, animates the PayPal→inventory→decision→policy→effect→verifier trace, then reveals the outcome card and A→B→A blind-world comparison.

The UI is deliberately proof-first: it cannot trigger PayPal actions and it does not require OpenAI or PayPal credentials.


## Slice 8 — Proof Drawer

Added an optional audit drawer so the Winning Moment stays clean while technical reviewers can inspect: full PayPal IDs, independent-verifier invariants, zero-harm metrics, and a live SHA-256 integrity re-check of `proof-lock.json`.

The drawer is read-only and does not execute PayPal or OpenAI calls.

## Slice 9 — autonomous hosted proof mode

The judge-facing Next.js app now supports two proof sources without changing UI code:

- **Local reproducibility:** set `NEXT_PUBLIC_REVERSA_API_URL=http://127.0.0.1:8000`; the browser reads FastAPI.
- **Hosted demo:** leave `NEXT_PUBLIC_REVERSA_API_URL` unset; the browser reads same-origin `/api/proof/final` from Next.js.

Before deployment, `npm run proof:sync` exports the already-adapted and already-locked FINAL proof from local FastAPI into `web/data/locked-proof/final.json`. The export refuses any non-PASS gate, wrong A→B→A action sequence, unsafe execution, duplicate effect, leak, or failed source proof lock.

`npm run proof:verify` recomputes a SHA-256 over the hosted snapshot. The normal `npm run build` runs this verification first, so Vercel cannot build an ungenerated or modified hosted snapshot accidentally.

No PayPal or OpenAI credentials are required in the Vercel project. The live runner remains in the repository for reproduction; the hosted surface is explicitly a read-only presentation of locked live evidence.
