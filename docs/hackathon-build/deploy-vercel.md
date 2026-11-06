# REVERSA — Hosted Demo Deployment (Vercel)

## Goal

Deploy the judge-facing Recovery Console as one autonomous Next.js application.
The hosted demo needs **no PayPal credentials, no OpenAI key, and no FastAPI process**.

The real PayPal/OpenAI runner remains in the repository for reproducibility. The
public demo serves a read-only snapshot exported from the cryptographically locked
Gate 0.5 evidence.

## Architecture

```text
Local reproducibility
  OpenAI + PayPal Sandbox + FastAPI
            ↓
  locked Gate 0.5 evidence
            ↓ npm run proof:sync
  web/data/locked-proof/final.json
            ↓
GitHub repository
            ↓
Vercel / Next.js
  GET /api/proof/final
            ↓
REVERSA Recovery Console
```

## 1. Export the locked proof snapshot

Keep the local product API running from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_API.ps1
```

In a second terminal:

```powershell
cd .\web
npm run proof:sync
npm run proof:verify
npm run build
cd ..
```

`proof:sync` refuses to export unless all of these are true:

- Gate result = PASS
- actions = CAPTURE → VOID → CAPTURE
- A→B→A flip = PASS
- independent outcomes = PASS
- causal probe paths = PASS
- unsafe executions = 0
- duplicate financial effects = 0
- no-leak = PASS
- source SHA-256 proof lock = PASS with 5 locked files

It writes:

```text
web/data/locked-proof/final.json
web/data/locked-proof/manifest.json
```

The manifest stores a SHA-256 of the exported snapshot. `npm run build` runs
`proof:verify` first and fails if the committed snapshot changes without a new export.

## 2. Commit the hosted snapshot

```powershell
git add web/data/locked-proof web app docs README.md
git commit -m "feat: add autonomous hosted REVERSA proof demo"
git push
```

Do not commit `.env.local`. Do not add PayPal or OpenAI credentials to Vercel.

## 3. Vercel project settings

Import the GitHub repository in Vercel and set:

- Framework Preset: **Next.js**
- Root Directory: **web**
- Build Command: leave default (`npm run build`)
- Output Directory: leave framework default (`.next`)
- Install Command: leave default (`npm install`)
- Node.js: current supported Node 22/24; Node 24 is appropriate for the current Next.js 16 deployment environment.

### Production environment variables

Do **not** set `NEXT_PUBLIC_REVERSA_API_URL` in Production.

When this variable is absent, the frontend calls the same-origin endpoint:

```text
/api/proof/final
```

which serves the bundled locked snapshot.

For local development, `.env.local` may still contain:

```text
NEXT_PUBLIC_REVERSA_API_URL=http://127.0.0.1:8000
```

so the UI reads FastAPI directly.

## 4. Production verification

After Vercel deploys, verify:

```text
https://<project>.vercel.app/api/health
https://<project>.vercel.app/api/proof/final
https://<project>.vercel.app/
```

`/api/health` must report:

```json
{
  "status": "ok",
  "mode": "HOSTED_VERIFIED_PROOF",
  "snapshot_generated": true,
  "gate_result": "PASS"
}
```

The homepage must show:

```text
LIVE PAYPAL GATE  PASS
CAPTURE → VOID → CAPTURE
```

Then verify manually:

1. `RECOVER SAFELY` completes the 6-step trace.
2. Outcome says `Purchase recovered` for A1/A2.
3. B shows `VOID` / customer protected.
4. `SHOW COUNTERFACTUAL` displays A1/B/A2.
5. `VIEW PROOF` shows verifier PASS, zero harm and source proof-lock integrity PASS.
6. Browser DevTools Network shows `/api/proof/final` from the same Vercel origin.

## Deployment rule

The hosted snapshot is a **presentation surface of locked live evidence**, not a
replacement for the reproducible live runner. The README and Devpost submission
must state this explicitly.
