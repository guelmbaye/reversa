# REVERSA — Grand Prize Build Checklist

Mode: autonomous implementation. Proof engine is frozen. Verification pauses at the end of Slices 3 and 7.

- [x] **1. Freeze Gate 0.5 evidence**
  Spec ref: `Gate 0.5 > Live Blind A→B→A`
  What to build: SHA-256 proof-lock generator over FINAL manifest and evidence.
  Acceptance: refuses any summary whose result is not PASS.
  Verify: `powershell -ExecutionPolicy Bypass -File .\FREEZE_GATE0_5.ps1`

- [x] **2. Evidence adapter**
  Spec ref: `Product > Verified Proof Mode`
  What to build: translate raw evidence JSON into judge-facing incident/observation/decision/outcome models.
  Acceptance: exposes identical initial state and A1/B/A2 decisions without mutating evidence.
  Verify: `pytest tests/test_evidence_adapter.py -q`

- [x] **3. Read-only proof API**
  Spec ref: `Product > Recovery Console backend`
  What to build: FastAPI endpoints for health, final proof bundle, and individual scenarios.
  Acceptance: API starts without PayPal/OpenAI credentials and returns the FINAL proof.
  Verify: `pytest tests/test_proof_api.py -q`

- [x] **4. Recovery Console shell**
  Spec ref: `UX > Incident surface`
  What to build: Next.js judge-facing console at 1440×900 and responsive widths.
  Acceptance: TIMEOUT, amount, merchant-order uncertainty, and Recover Safely CTA visible above fold.
  Verify: manual 1440×900 screenshot.

- [x] **5. Recovery trace animation**
  Spec ref: `UX > Obvious Magic`
  What to build: progressive PayPal → inventory → decision → policy → external effect → verification trace.
  Acceptance: one proof scenario completes visually in 6–10 seconds.
  Verify: screen recording.

- [x] **6. Outcome card**
  Spec ref: `UX > Irreplaceable Outcome`
  What to build: 1 intended purchase / 1 PayPal effect / 0 duplicates / VERIFIED.
  Acceptance: result understood without JSON.
  Verify: blind 10-second screenshot review.

- [x] **7. Blind World Compare**
  Spec ref: `Winning Moment > A→B→A`
  What to build: side-by-side A1/B/A2 with identical initial failure and CAPTURE/VOID/CAPTURE split.
  Acceptance: causal flip understandable in under 20 seconds.
  Verify: blind-world review checkpoint.

- [x] **8. Proof drawer**
  Spec ref: `Trust > Evidence`
  What to build: PayPal identifiers, verifier invariants, no-leak and duplicate-effect checks.
  Acceptance: technical reviewer can audit the result without leaving UI.
  Verify: compare drawer values to locked evidence.

- [ ] **9. Hosted demo + reproducibility**
  Spec ref: `Submission > Functional demo`
  What to build: deploy autonomous Next.js Proof Mode from a verified locked snapshot while preserving FastAPI/Live Sandbox reproduction locally.
  Acceptance: Vercel build refuses unverified snapshots; public URL works without PayPal/OpenAI secrets; README can reproduce Gate 0.5 with credentials.
  Verify: `npm run proof:sync && npm run proof:verify && npm run build`, then Vercel incognito test.
  Implementation status: deployment package ready; mark complete only after the public URL passes production verification.

- [ ] **10. Devpost handoff**
  Spec ref: `Submission > Presentation`
  What to build: <3 minute video, screenshots, project description, repo links, proof narrative.
  Acceptance: first 45 seconds show pain → same timeout → different reality → different safe action.
  Verify: final submission dry run.
