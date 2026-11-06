# REVERSA Recovery Console

Judge-facing frontend for the locked Gate 0.5 evidence.

## Local Verified Proof Mode

Start FastAPI from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_API.ps1
```

Keep this local-only setting in `web/.env.local`:

```text
NEXT_PUBLIC_REVERSA_API_URL=http://127.0.0.1:8000
```

Then:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_PRODUCT_WEB.ps1
```

Open `http://127.0.0.1:3000`.

## Autonomous Hosted Demo

With the local Proof API running:

```powershell
cd web
npm run proof:sync
npm run proof:verify
npm run build
cd ..
```

This exports the already locked PASS proof to:

```text
web/data/locked-proof/final.json
web/data/locked-proof/manifest.json
```

Commit those two generated files before Vercel deployment.

On Vercel, set the project **Root Directory** to `web` and leave
`NEXT_PUBLIC_REVERSA_API_URL` **unset**. The Recovery Console then reads the
same-origin Next.js route `/api/proof/final`; no PayPal or OpenAI credentials
are required for the public demo.

See `docs/hackathon-build/deploy-vercel.md` for the complete deployment check.

The frontend is read-only and cannot execute financial actions.
