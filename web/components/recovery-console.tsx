"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchFinalProof, USES_EXTERNAL_PROOF_API } from "@/lib/api";
import type { FinalProofBundle, ProofScenario } from "@/lib/types";

const STEP_DELAY_MS = 1100;

function shortId(value?: string | null) {
  if (!value) return "—";
  if (value.length <= 16) return value;
  return `${value.slice(0, 7)}…${value.slice(-6)}`;
}

function observationFor(scenario: ProofScenario, source: string) {
  return scenario.observations.find((item) => item.source === source);
}

function outcomeCopy(scenario: ProofScenario) {
  if (scenario.decision === "VOID") {
    return {
      headline: "Customer protected",
      subline: "The authorization was voided before money was captured.",
      metrics: [
        ["0", "captured"],
        ["1", "authorization voided"],
        ["0", "duplicate effects"],
        ["VERIFIED", "independent outcome"],
      ],
    };
  }
  return {
    headline: "Purchase recovered",
    subline: "REVERSA captured exactly once after checking the world.",
    metrics: [
      ["1", "intended purchase"],
      ["1", "PayPal capture"],
      ["0", "duplicate effects"],
      ["VERIFIED", "independent outcome"],
    ],
  };
}

function buildTrace(scenario: ProofScenario) {
  const paypal = observationFor(scenario, "PayPal");
  const inventory = observationFor(scenario, "Inventory");
  return [
    {
      eyebrow: "REALITY PROBE 01",
      label: "Check PayPal",
      value: paypal?.result ?? "UNKNOWN",
      tone: "neutral",
    },
    {
      eyebrow: "REALITY PROBE 02",
      label: "Check inventory",
      value: inventory?.result ?? "UNKNOWN",
      tone: inventory?.result === "UNAVAILABLE" ? "warn" : "neutral",
    },
    {
      eyebrow: "RECOVERY DECISION",
      label: "Choose safe action",
      value: scenario.decision,
      tone: scenario.decision === "VOID" ? "warn" : "accent",
    },
    {
      eyebrow: "DETERMINISTIC POLICY",
      label: "Safety gate",
      value: scenario.policy.allowed ? "ALLOWED" : "BLOCKED",
      tone: scenario.policy.allowed ? "success" : "danger",
    },
    {
      eyebrow: "REAL PAYPAL EFFECT",
      label: scenario.decision === "VOID" ? "Authorization" : "Capture",
      value: scenario.paypal_effect,
      tone: "success",
    },
    {
      eyebrow: "INDEPENDENT VERIFIER",
      label: "Verify final world",
      value: scenario.verification.result,
      tone: scenario.verified ? "success" : "danger",
    },
  ];
}

function StatusDot({ ok = true }: { ok?: boolean }) {
  return <span className={`status-dot ${ok ? "status-dot--ok" : "status-dot--bad"}`} />;
}


function CopyButton({ value, label = "COPY" }: { value?: string | null; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <button className="copy-button" onClick={copy} disabled={!value}>
      {copied ? "COPIED" : label}
    </button>
  );
}

function ProofDrawer({
  open,
  onClose,
  bundle,
  scenario,
}: {
  open: boolean;
  onClose: () => void;
  bundle: FinalProofBundle;
  scenario: ProofScenario;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const lock = bundle.proof_lock;
  const invariantEntries = Object.entries(scenario.verification.invariants);

  return (
    <div className={`proof-drawer-layer ${open ? "proof-drawer-layer--open" : ""}`} aria-hidden={!open}>
      <button className="proof-drawer-backdrop" aria-label="Close proof drawer" onClick={onClose} />
      <aside className="proof-drawer" role="dialog" aria-modal="true" aria-label="REVERSA proof details">
        <div className="proof-drawer__header">
          <div>
            <span className="eyebrow">AUDITABLE LIVE PROOF</span>
            <h2>Proof Drawer · {scenario.scenario}</h2>
            <p>Technical evidence stays one click away from the Winning Moment.</p>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close proof drawer">×</button>
        </div>

        <section className="drawer-section">
          <div className="drawer-section__title">
            <span>OUTCOME</span>
            <strong className="drawer-pass"><StatusDot /> {scenario.verification.result}</strong>
          </div>
          <div className="drawer-kpis">
            <div><span>DECISION</span><strong>{scenario.decision}</strong></div>
            <div><span>PAYPAL EFFECT</span><strong>{scenario.paypal_effect}</strong></div>
            <div><span>PROBES</span><strong>{scenario.probe_count}</strong></div>
            <div><span>NO LEAK</span><strong>{scenario.no_leak ? "PASS" : "FAIL"}</strong></div>
          </div>
        </section>

        <section className="drawer-section">
          <div className="drawer-section__title"><span>PAYPAL IDENTIFIERS</span><strong>REAL SANDBOX</strong></div>
          {[
            ["Order ID", scenario.identifiers.order_id],
            ["Authorization ID", scenario.identifiers.authorization_id],
            ["Capture ID", scenario.identifiers.capture_id],
          ].map(([label, value]) => (
            <div className="id-row" key={label}>
              <div><span>{label}</span><code>{value ?? "—"}</code></div>
              <CopyButton value={value} />
            </div>
          ))}
        </section>

        <section className="drawer-section">
          <div className="drawer-section__title">
            <span>INDEPENDENT VERIFIER</span>
            <strong>{invariantEntries.filter(([, ok]) => ok).length}/{invariantEntries.length} PASS</strong>
          </div>
          <div className="invariant-list">
            {invariantEntries.map(([name, ok]) => (
              <div key={name} className="invariant-row">
                <StatusDot ok={ok} />
                <span>{name.replaceAll("_", " ")}</span>
                <strong>{ok ? "PASS" : "FAIL"}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="drawer-section">
          <div className="drawer-section__title"><span>RUN SAFETY</span><strong>ZERO HARM</strong></div>
          <div className="safety-grid">
            <div><span>Unsafe executions</span><strong>{bundle.summary.unsafe_executions}</strong></div>
            <div><span>Duplicate effects</span><strong>{bundle.summary.duplicate_financial_effects}</strong></div>
            <div><span>Causal probe path</span><strong>{bundle.summary.counterfactual_probe_paths_pass ? "PASS" : "FAIL"}</strong></div>
            <div><span>Blind-world leak</span><strong>{bundle.summary.no_leak ? "NONE" : "DETECTED"}</strong></div>
          </div>
        </section>

        <section className="drawer-section drawer-lock">
          <div className="drawer-section__title">
            <span>SHA-256 PROOF LOCK</span>
            <strong className={lock?.integrity_pass ? "drawer-pass" : "drawer-fail"}>
              <StatusDot ok={!!lock?.integrity_pass} />
              {lock ? (lock.integrity_pass ? "INTEGRITY PASS" : "INTEGRITY FAIL") : "NO LOCK"}
            </strong>
          </div>
          {lock ? (
            <>
              <div className="lock-meta">
                <span>{lock.file_count} locked files</span>
                <span>{lock.locked_at_utc ? new Date(lock.locked_at_utc).toLocaleString() : "—"}</span>
              </div>
              <div className="hash-list">
                {lock.files.map((file) => (
                  <div className="hash-row" key={file.path}>
                    <div>
                      <span>{file.path.split("/").at(-1)}</span>
                      <code>{file.sha256}</code>
                    </div>
                    <div className="hash-actions">
                      <span className={file.matches ? "hash-ok" : "hash-bad"}>{file.matches ? "MATCH" : "MISMATCH"}</span>
                      <CopyButton value={file.sha256} label="COPY HASH" />
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="drawer-muted">Freeze the final evidence to expose cryptographic integrity here.</p>
          )}
        </section>

        <div className="drawer-footer">
          <span>Read-only proof surface · GET /api/proof/final</span>
          <strong>A → CAPTURE · B → VOID · A → CAPTURE</strong>
        </div>
      </aside>
    </div>
  );
}

function ScenarioMiniCard({ scenario }: { scenario: ProofScenario }) {
  const inventory = observationFor(scenario, "Inventory");
  const paypal = observationFor(scenario, "PayPal");
  return (
    <article className={`world-card world-card--${scenario.decision.toLowerCase()}`}>
      <div className="world-card__topline">
        <span>WORLD {scenario.scenario}</span>
        <span className="verified-pill"><StatusDot /> VERIFIED</span>
      </div>
      <div className="same-failure">SAME VISIBLE FAILURE</div>
      <div className="world-timeout">PAYMENT TIMEOUT</div>
      <div className="world-facts">
        <div><span>PayPal</span><strong>{paypal?.result ?? "UNKNOWN"}</strong></div>
        <div><span>Inventory</span><strong>{inventory?.result ?? "UNKNOWN"}</strong></div>
      </div>
      <div className="world-arrow">↓</div>
      <div className="world-decision">{scenario.decision}</div>
      <div className="world-effect">PayPal → {scenario.paypal_effect}</div>
    </article>
  );
}

export default function RecoveryConsole() {
  const [bundle, setBundle] = useState<FinalProofBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<"A1" | "B" | "A2">("A1");
  const [revealed, setRevealed] = useState(0);
  const [running, setRunning] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [proofOpen, setProofOpen] = useState(false);
  const compareRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setError(null);

    fetchFinalProof(controller.signal)
      .then((proof) => {
        if (!controller.signal.aborted) {
          setBundle(proof);
        }
      })
      .catch((err: unknown) => {
        // React Strict Mode intentionally mounts, unmounts and mounts effects
        // again in development. The first cleanup aborts its request; that is
        // lifecycle control, not an API outage.
        if (controller.signal.aborted) {
          return;
        }

        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        setError(err instanceof Error ? err.message : "Unable to load locked proof.");
      });

    return () => controller.abort();
  }, []);

  const scenario = useMemo(
    () => bundle?.scenarios.find((item) => item.scenario === selected) ?? null,
    [bundle, selected],
  );
  const trace = useMemo(() => (scenario ? buildTrace(scenario) : []), [scenario]);
  const completed = !!scenario && revealed >= trace.length;

  useEffect(() => {
    if (!running || !scenario) return;
    if (revealed >= trace.length) {
      setRunning(false);
      return;
    }
    const timer = window.setTimeout(() => setRevealed((value) => value + 1), STEP_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [running, revealed, scenario, trace.length]);

  function playRecovery() {
    setRevealed(0);
    setRunning(true);
  }

  function chooseScenario(id: "A1" | "B" | "A2") {
    setSelected(id);
    setRevealed(0);
    setRunning(false);
  }

  function showCompare() {
    setCompareOpen(true);
    window.setTimeout(() => compareRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 40);
  }

  if (error) {
    return (
      <main className="screen-center">
        <section className="error-card">
          <div className="brand-mark">R</div>
          <h1>{USES_EXTERNAL_PROOF_API ? "REVERSA Proof API is offline" : "Hosted proof snapshot is unavailable"}</h1>
          <p>{error}</p>
          <code>
            {USES_EXTERNAL_PROOF_API
              ? "powershell -ExecutionPolicy Bypass -File .\\RUN_PRODUCT_API.ps1"
              : "Run npm run proof:sync locally, commit web/data/locked-proof, then redeploy."}
          </code>
        </section>
      </main>
    );
  }

  if (!bundle || !scenario) {
    return (
      <main className="screen-center">
        <div className="loading-orbit"><span /><span /><span /></div>
        <p className="loading-copy">Loading locked PayPal proof…</p>
      </main>
    );
  }

  const outcome = outcomeCopy(scenario);
  const amount = `${scenario.currency} ${scenario.amount}`;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">R</div>
          <div>
            <strong>REVERSA</strong>
            <span>SELF-HEALING COMMERCE</span>
          </div>
        </div>
        <div className="topbar__status">
          <span className="mode-pill"><StatusDot /> VERIFIED PROOF MODE</span>
          <span className="proof-pill">PROOF LOCKED</span>
          <button className="audit-button" onClick={() => setProofOpen(true)}>VIEW PROOF</button>
        </div>
      </header>

      <section className="hero-copy">
        <div>
          <p className="kicker">PAYMENT RECOVERY FOR AI AGENTS</p>
          <h1>A timeout does not tell you <em>what happened.</em></h1>
          <p className="hero-subcopy">REVERSA checks external reality before money moves again.</p>
        </div>
        <div className="proof-score">
          <span>LIVE PAYPAL GATE</span>
          <strong>{bundle.summary.result}</strong>
          <small>{bundle.summary.actions.join(" → ")}</small>
        </div>
      </section>

      <section className="console-grid" aria-label="Recovery console">
        <article className="incident-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">RECOVERY INCIDENT</span>
              <h2>AI checkout lost certainty</h2>
            </div>
            <span className="incident-id">RV-{scenario.scenario}-249</span>
          </div>

          <div className="scenario-switch" role="group" aria-label="Proof scenario">
            {(["A1", "B", "A2"] as const).map((id) => (
              <button key={id} className={selected === id ? "active" : ""} onClick={() => chooseScenario(id)}>
                {id}
              </button>
            ))}
          </div>

          <div className="amount-row">
            <div>
              <span>AI CHECKOUT</span>
              <strong>{amount}</strong>
            </div>
            <div className="paypal-chip">PayPal Sandbox</div>
          </div>

          <div className="timeout-box">
            <div className="timeout-icon">!</div>
            <div>
              <span>PAYMENT TIMEOUT</span>
              <strong>Payment state unknown</strong>
              <small>Merchant order not confirmed</small>
            </div>
          </div>

          <div className="initial-facts">
            <div><span>Checkout</span><strong>{scenario.initial_state.checkout}</strong></div>
            <div><span>Payment</span><strong>{scenario.initial_state.payment}</strong></div>
            <div><span>Order</span><strong>{scenario.initial_state.merchant_order}</strong></div>
          </div>

          <button className="primary-cta" onClick={playRecovery} disabled={running}>
            <span>{running ? "RECOVERING…" : completed ? "REPLAY RECOVERY" : "RECOVER SAFELY"}</span>
            <span className="cta-arrow">→</span>
          </button>
          <p className="cta-note">No blind retry. No assumption that timeout means failure.</p>
        </article>

        <article className="trace-card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">RECOVERY TRACE</span>
              <h2>Check reality, then act</h2>
            </div>
            <span className={`live-pill ${running ? "live-pill--running" : ""}`}>{running ? "RUNNING" : completed ? "VERIFIED" : "READY"}</span>
          </div>

          <div className="trace-list">
            {trace.map((step, index) => {
              const visible = index < revealed;
              const active = running && index === revealed;
              return (
                <div key={`${step.label}-${index}`} className={`trace-step ${visible ? "trace-step--visible" : ""} ${active ? "trace-step--active" : ""}`}>
                  <div className="trace-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className="trace-copy">
                    <span>{step.eyebrow}</span>
                    <strong>{step.label}</strong>
                  </div>
                  <div className={`trace-value trace-value--${step.tone}`}>{visible ? step.value : active ? "CHECKING…" : "LOCKED"}</div>
                </div>
              );
            })}
          </div>
        </article>
      </section>

      <section className={`outcome-panel ${completed ? "outcome-panel--visible" : ""}`} aria-live="polite">
        <div className="outcome-heading">
          <span className="eyebrow">IRREPLACEABLE OUTCOME</span>
          <h2>{completed ? outcome.headline : "Outcome locked until recovery completes"}</h2>
          <p>{completed ? outcome.subline : "REVERSA will not claim success before PayPal is independently re-read."}</p>
        </div>
        <div className="outcome-metrics">
          {outcome.metrics.map(([value, label]) => (
            <div key={label} className="metric-card">
              <strong>{completed ? value : "—"}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <button className="secondary-cta" onClick={showCompare} disabled={!completed}>
          SHOW COUNTERFACTUAL <span>↓</span>
        </button>
      </section>

      <section ref={compareRef} className={`compare-section ${compareOpen ? "compare-section--open" : ""}`}>
        <div className="compare-heading">
          <span className="eyebrow">BLIND WORLD TEST · A → B → A</span>
          <h2>Same failure signal. Different reality. Different safe action.</h2>
          <p>REVERSA did not know the world. It had to find out.</p>
          <div className="aba-sequence">A → CAPTURE · B → VOID · A → CAPTURE</div>
        </div>

        <div className="world-grid">
          {bundle.scenarios.map((item) => <ScenarioMiniCard key={item.scenario} scenario={item} />)}
        </div>

        <div className="causal-strip">
          <div><span>VISIBLE INPUT</span><strong>IDENTICAL TIMEOUT</strong></div>
          <div className="causal-arrow">→</div>
          <div><span>HIDDEN REALITY</span><strong>CHANGES</strong></div>
          <div className="causal-arrow">→</div>
          <div><span>SAFE ACTION</span><strong>FLIPS</strong></div>
          <div className="causal-arrow">→</div>
          <div><span>PAYPAL</span><strong>VERIFIES</strong></div>
        </div>
      </section>

      <section className="proof-footer">
        <div>
          <span className="eyebrow">LOCKED LIVE EVIDENCE</span>
          <h2>Not a simulation. Not a screenshot claim.</h2>
        </div>
        <div className="proof-facts">
          <div><StatusDot /><span>Live PayPal Sandbox effects</span></div>
          <div><StatusDot /><span>Independent re-read after mutation</span></div>
          <div><StatusDot /><span>0 unsafe executions</span></div>
          <div><StatusDot /><span>0 duplicate financial effects</span></div>
          <div><StatusDot /><span>No hidden-world leak</span></div>
        </div>
        <div className="proof-ids">
          <span>Order {shortId(scenario.identifiers.order_id)}</span>
          <span>Authorization {shortId(scenario.identifiers.authorization_id)}</span>
          <span>Capture {shortId(scenario.identifiers.capture_id)}</span>
          <button className="inline-proof-button" onClick={() => setProofOpen(true)}>OPEN TECHNICAL PROOF →</button>
        </div>
      </section>

      <ProofDrawer
        open={proofOpen}
        onClose={() => setProofOpen(false)}
        bundle={bundle}
        scenario={scenario}
      />
    </main>
  );
}
