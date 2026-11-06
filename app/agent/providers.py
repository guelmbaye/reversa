from __future__ import annotations

import json
import os
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class DecisionProvider(Protocol):
    def next_step(self, *, system_prompt: str, state: dict[str, Any]) -> dict[str, Any]:
        ...


class ProviderError(RuntimeError):
    pass


ProbeTool = Literal[
    "inspect_paypal_payment",
    "inspect_merchant_order",
    "inspect_inventory",
    "inspect_fulfillment",
]

FinalAction = Literal[
    "RESTORE_ORDER",
    "CAPTURE",
    "VOID",
    "REFUND",
    "DO_NOTHING",
    "ABSTAIN",
]

HypothesisStatus = Literal["INITIAL", "SUPPORTED", "REVISED", "REJECTED"]


class HypothesisEventSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HypothesisStatus
    hypothesis: str = Field(min_length=1)
    previous_hypothesis: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)


class ReasonerStepSchema(BaseModel):
    """
    Single strict envelope for both probe and decision turns.
    Semantic cross-field constraints are enforced again by AdaptiveRecoveryAgent.
    """
    model_config = ConfigDict(extra="forbid")

    kind: Literal["probe", "decide"]
    tool: ProbeTool | None = None
    action: FinalAction | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    hypothesis_event: HypothesisEventSchema
    rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    remaining_uncertainty: list[str] = Field(default_factory=list)


class OpenAIResponsesProvider:
    """
    Live model provider using Responses API Structured Outputs.

    JSON is no longer obtained by prompt convention + json.loads.
    The API constrains every turn to ReasonerStepSchema, eliminating malformed
    concatenated outputs such as '{}{...}'.
    """
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("REVERSA_MODEL")
        if not self.model:
            raise ValueError("Set REVERSA_MODEL to the API model you want to evaluate.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError(
                'Install the optional provider: pip install -e ".[openai]"'
            ) from exc

        self._client = OpenAI()

    def next_step(self, *, system_prompt: str, state: dict[str, Any]) -> dict[str, Any]:
        response = self._client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "CURRENT STATE\n"
                        + json.dumps(state, indent=2, sort_keys=True)
                        + "\n\nReturn the next REVERSA step."
                    ),
                },
            ],
            text_format=ReasonerStepSchema,
            store=False,
        )

        parsed = response.output_parsed
        if parsed is None:
            # Preserve useful diagnostic information without attempting to
            # interpret unstructured model text.
            raise ProviderError(
                "Structured response was not parsed. "
                f"status={getattr(response, 'status', None)!r} "
                f"incomplete={getattr(response, 'incomplete_details', None)!r}"
            )

        return parsed.model_dump(exclude_none=True)


class ReplayProvider:
    """
    Deterministic provider used only to test the adaptive orchestrator itself.

    It reacts exclusively to observations available in state and therefore
    receives no world ID, expected action, or oracle truth.
    """

    def _event(self, status, hypothesis, previous=None, evidence=None, reason=""):
        return {
            "status": status,
            "hypothesis": hypothesis,
            "previous_hypothesis": previous,
            "evidence_ids": evidence or [],
            "reason": reason,
        }

    def next_step(self, *, system_prompt: str, state: dict[str, Any]) -> dict[str, Any]:
        observations = state["observations"]
        by_tool = {o["tool"]: o for o in observations}
        events = state.get("hypothesis_events", [])

        if "inspect_paypal_payment" not in by_tool:
            initial_h = "the payment may already have been captured despite the timeout"
            return {
                "kind": "probe",
                "tool": "inspect_paypal_payment",
                "hypothesis_event": self._event(
                    "INITIAL",
                    initial_h,
                    reason="A lost response after capture is a plausible cause of an ambiguous timeout.",
                ),
                "rationale": "First determine whether a financial effect already occurred.",
            }

        p_obs = by_tool["inspect_paypal_payment"]
        p = p_obs["payload"]
        previous = events[-1]["hypothesis"] if events else None

        if not p.get("available", False):
            h = "decisive payment truth is unavailable"
            return {
                "kind": "decide",
                "action": "ABSTAIN",
                "confidence": 0.99,
                "hypothesis_event": self._event(
                    "REVISED",
                    h,
                    previous,
                    [p_obs["id"]],
                    "PayPal could not be inspected, so the prior payment hypothesis cannot be resolved safely.",
                ),
                "rationale": "Moving money without payment truth is unsafe.",
                "evidence_ids": [p_obs["id"]],
                "remaining_uncertainty": ["paypal_state_unavailable"],
            }

        if p.get("capture") == "COMPLETED":
            captured_h = "the payment was captured; merchant-side completion is still unknown"
            if "inspect_merchant_order" not in by_tool:
                return {
                    "kind": "probe",
                    "tool": "inspect_merchant_order",
                    "hypothesis_event": self._event(
                        "SUPPORTED",
                        captured_h,
                        previous,
                        [p_obs["id"]],
                        "The PayPal observation confirms that a capture actually completed.",
                    ),
                    "rationale": "Determine whether the merchant side already committed.",
                }

            order_obs = by_tool["inspect_merchant_order"]
            order = order_obs["payload"]
            previous = events[-1]["hypothesis"] if events else captured_h

            if order.get("exists"):
                healthy_h = "client timed out but payment and merchant order both completed"
                return {
                    "kind": "decide",
                    "action": "DO_NOTHING",
                    "confidence": 0.99,
                    "hypothesis_event": self._event(
                        "REVISED",
                        healthy_h,
                        previous,
                        [order_obs["id"]],
                        "The merchant order exists, so no recovery mutation is needed.",
                    ),
                    "rationale": "Payment and merchant order are already consistent.",
                    "evidence_ids": [p_obs["id"], order_obs["id"]],
                    "remaining_uncertainty": [],
                }

            missing_h = "capture completed but merchant order is missing"
            if "inspect_fulfillment" not in by_tool:
                return {
                    "kind": "probe",
                    "tool": "inspect_fulfillment",
                    "hypothesis_event": self._event(
                        "REVISED",
                        missing_h,
                        previous,
                        [order_obs["id"]],
                        "The merchant observation shows that the order did not commit.",
                    ),
                    "rationale": "Fulfillment viability determines restore versus refund.",
                }

            f_obs = by_tool["inspect_fulfillment"]
            possible = f_obs["payload"].get("possible")
            final_h = (
                "capture completed, order missing, fulfillment still possible"
                if possible
                else "capture completed, order missing, fulfillment impossible"
            )
            return {
                "kind": "decide",
                "action": "RESTORE_ORDER" if possible else "REFUND",
                "confidence": 0.99,
                "hypothesis_event": self._event(
                    "REVISED",
                    final_h,
                    events[-1]["hypothesis"] if events else missing_h,
                    [f_obs["id"]],
                    "Fulfillment viability determines whether to restore the order or compensate with a refund.",
                ),
                "rationale": "Fulfillment remains possible." if possible else "The paid purchase cannot be fulfilled.",
                "evidence_ids": [p_obs["id"], order_obs["id"], f_obs["id"]],
                "remaining_uncertainty": [],
            }

        if p.get("authorization") == "ACTIVE" and p.get("capture") is None:
            auth_h = "the payment was authorized but never captured"
            if "inspect_inventory" not in by_tool:
                return {
                    "kind": "probe",
                    "tool": "inspect_inventory",
                    "hypothesis_event": self._event(
                        "REJECTED",
                        auth_h,
                        previous,
                        [p_obs["id"]],
                        "PayPal shows no completed capture, contradicting the prior hypothesis that payment may already have been captured.",
                    ),
                    "rationale": "Inventory viability determines capture versus void.",
                }

            inv_obs = by_tool["inspect_inventory"]
            available = inv_obs["payload"].get("available")
            final_h = (
                "authorized, uncaptured, and still fulfillable"
                if available
                else "authorized, uncaptured, but purchase can no longer proceed"
            )
            return {
                "kind": "decide",
                "action": "CAPTURE" if available else "VOID",
                "confidence": 0.99,
                "hypothesis_event": self._event(
                    "REVISED",
                    final_h,
                    events[-1]["hypothesis"] if events else auth_h,
                    [inv_obs["id"]],
                    "Inventory evidence decides whether the active authorization should be captured or released.",
                ),
                "rationale": "Inventory is available." if available else "Inventory is unavailable.",
                "evidence_ids": [p_obs["id"], inv_obs["id"]],
                "remaining_uncertainty": [],
            }

        h = "unsupported or ambiguous payment state"
        return {
            "kind": "decide",
            "action": "ABSTAIN",
            "confidence": 0.8,
            "hypothesis_event": self._event(
                "REVISED",
                h,
                previous,
                [p_obs["id"]],
                "The observed PayPal state does not justify a safe mutation.",
            ),
            "rationale": "No safe action can be justified.",
            "evidence_ids": [p_obs["id"]],
            "remaining_uncertainty": ["unsupported_payment_state"],
        }
