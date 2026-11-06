export type ProofObservation = {
  id: string;
  tool: string;
  source: string;
  result: string;
  details: Record<string, unknown>;
};

export type ProofScenario = {
  scenario: "A1" | "B" | "A2";
  product: string;
  quantity: number;
  amount: string;
  currency: string;
  initial_state: {
    checkout: string;
    payment: string;
    merchant_order: string;
  };
  observations: ProofObservation[];
  decision: string;
  confidence: number;
  policy: { allowed: boolean; reason: string };
  paypal_effect: string;
  verification: { result: "PASS" | "FAIL"; invariants: Record<string, boolean> };
  verified: boolean;
  no_leak: boolean;
  probe_count: number;
  identifiers: {
    order_id?: string | null;
    authorization_id?: string | null;
    capture_id?: string | null;
  };
};

export type FinalProofBundle = {
  tagline: string;
  summary: {
    gate: string;
    provider: string;
    actions: string[];
    expected_actions: string[];
    aba_flip_pass: boolean;
    all_independent_outcomes_pass: boolean;
    unsafe_proposals_blocked: number;
    unsafe_executions: number;
    duplicate_financial_effects: number;
    world_pushback_events: number;
    counterfactual_probe_paths_pass: boolean;
    no_leak: boolean;
    result: "PASS" | "FAIL";
  };
  scenarios: ProofScenario[];
  proof_lock?: ProofLock | null;
};


export type ProofLockFile = {
  path: string;
  sha256: string;
  bytes: number;
  current_sha256: string;
  matches: boolean;
};

export type ProofLock = {
  proof: string;
  gate_result: string;
  locked_at_utc: string;
  integrity_pass: boolean;
  file_count: number;
  files: ProofLockFile[];
};
