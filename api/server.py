from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.evidence_adapter import EvidenceError, load_final_bundle, load_proof_lock, load_scenario


def _default_evidence_dir() -> Path:
    return Path(os.getenv("REVERSA_EVIDENCE_DIR", "evidence/live_aba_FINAL"))


def create_app(evidence_dir: Path | None = None) -> FastAPI:
    resolved = evidence_dir or _default_evidence_dir()

    app = FastAPI(
        title="REVERSA Recovery Proof API",
        version="0.1.0",
        description=(
            "Product-facing read-only API over the locked Gate 0.5 PayPal evidence. "
            "No PayPal or OpenAI credentials are required in Verified Proof Mode."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": "VERIFIED_PROOF",
            "evidence_dir": str(resolved),
            "evidence_present": resolved.exists(),
        }

    @app.get("/api/proof/final")
    def final_proof():
        try:
            return load_final_bundle(resolved)
        except EvidenceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc


    @app.get("/api/proof/lock")
    def proof_lock():
        try:
            lock = load_proof_lock(resolved)
            if lock is None:
                raise HTTPException(status_code=404, detail="proof-lock.json not found")
            return lock
        except EvidenceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/proof/{slot}")
    def scenario(slot: str):
        normalized = slot.upper()
        if normalized not in {"A1", "B", "A2"}:
            raise HTTPException(status_code=404, detail="Scenario must be A1, B, or A2")
        try:
            return load_scenario(resolved, normalized)
        except EvidenceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app


app = create_app()
