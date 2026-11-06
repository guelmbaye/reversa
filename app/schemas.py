from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Action(str, Enum):
    RESTORE_ORDER = "RESTORE_ORDER"
    CAPTURE = "CAPTURE"
    VOID = "VOID"
    REFUND = "REFUND"
    DO_NOTHING = "DO_NOTHING"
    ABSTAIN = "ABSTAIN"

@dataclass(frozen=True)
class Intent:
    product: str = "27-inch monitor"
    quantity: int = 1
    amount: str = "249.00"
    currency: str = "USD"

@dataclass
class Observation:
    id: str
    tool: str
    payload: dict[str, Any]

@dataclass
class Decision:
    action: Action
    confidence: float
    evidence: list[str] = field(default_factory=list)
    remaining_uncertainty: list[str] = field(default_factory=list)
    rationale: str = ""

@dataclass
class VerificationResult:
    result: str
    invariants: dict[str, bool]
    observed: dict[str, Any]
    expected_action: str
    actual_action: str
