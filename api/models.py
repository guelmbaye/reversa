from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IncidentState(BaseModel):
    checkout: str
    payment: str
    merchant_order: str


class ProofObservation(BaseModel):
    id: str
    tool: str
    source: str
    result: str
    details: dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    allowed: bool
    reason: str


class VerificationView(BaseModel):
    result: Literal["PASS", "FAIL"]
    invariants: dict[str, bool] = Field(default_factory=dict)


class ProofIdentifiers(BaseModel):
    order_id: str | None = None
    authorization_id: str | None = None
    capture_id: str | None = None


class ProofScenario(BaseModel):
    scenario: Literal["A1", "B", "A2"]
    product: str
    quantity: int
    amount: str
    currency: str
    initial_state: IncidentState
    observations: list[ProofObservation]
    decision: str
    confidence: float
    policy: PolicyResult
    paypal_effect: str
    verification: VerificationView
    verified: bool
    no_leak: bool
    probe_count: int
    identifiers: ProofIdentifiers


class GateSummary(BaseModel):
    gate: str
    provider: str
    actions: list[str]
    expected_actions: list[str]
    aba_flip_pass: bool
    all_independent_outcomes_pass: bool
    unsafe_proposals_blocked: int
    unsafe_executions: int
    duplicate_financial_effects: int
    world_pushback_events: int
    counterfactual_probe_paths_pass: bool
    no_leak: bool
    result: Literal["PASS", "FAIL"]


class ProofLockFile(BaseModel):
    path: str
    sha256: str
    bytes: int
    current_sha256: str
    matches: bool


class ProofLockView(BaseModel):
    proof: str
    gate_result: str
    locked_at_utc: str
    integrity_pass: bool
    file_count: int
    files: list[ProofLockFile] = Field(default_factory=list)


class FinalProofBundle(BaseModel):
    tagline: str = "Same failure signal. Different reality. Different safe action."
    summary: GateSummary
    scenarios: list[ProofScenario]
    proof_lock: ProofLockView | None = None
