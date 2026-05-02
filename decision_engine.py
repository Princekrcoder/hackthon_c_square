"""
decision_engine.py — Support Ticket Triage Decision Engine

Purpose:
    This module is the production-grade routing layer of the support ticket
    triage system. It consumes ClassificationResult objects produced by
    classifier.py and applies a deterministic, priority-ordered rule chain
    to decide whether a ticket should receive an automated reply (REPLIED)
    or be escalated to a human agent (ESCALATED).

    The engine is safety-first: when in doubt, it escalates rather than
    risks an incorrect automated response.

Responsibilities:
    - Apply a 6-rule priority chain to every ClassificationResult
    - Produce a DecisionResult carrying the action, confidence, reason,
      reasoning text, triggered rules, suggested response, and a full
      audit trail
    - Accumulate per-action, per-reason, and confidence statistics across
      all decisions made by a DecisionEngine instance
    - Generate formatted response strings via ResponseRecommendationEngine
    - Expose a triage_ticket() integration function that orchestrates the
      full pipeline from a raw TicketRecord to a final response dict

Typical usage:
    from data_loader import load_tickets
    from classifier import Classifier
    from decision_engine import DecisionEngine, triage_ticket

    tickets = load_tickets("inputs/sample_support_tickets.csv")
    clf = Classifier()
    engine = DecisionEngine()

    for ticket in tickets:
        result = triage_ticket(ticket, clf, engine)
        print(result["decision"]["action"], result["response"][:80])

    stats = engine.get_decision_statistics()
    print(stats)
"""

# ---------------------------------------------------------------------------
# Section 1: Standard Library Imports
# ---------------------------------------------------------------------------

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Tuple
import statistics

# ---------------------------------------------------------------------------
# Section 2: Local Module Imports
# ---------------------------------------------------------------------------

from config import (
    CONFIDENCE_MIN,
    CONFIDENCE_HIGH,
    SUPPORTED_DOMAINS,
    TEMPLATE_RESPONSES,
)

from classifier import (
    RequestType,
    RiskLevel,
    Domain,
    ClassificationResult,
    RequestTypeResult,
    ProductAreaResult,
    RiskAssessment,
)

from data_loader import TicketRecord

# ---------------------------------------------------------------------------
# Section 3: Logging Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only attach a handler if none are already configured on this logger.
# This prevents duplicate log output when the module is imported multiple
# times or used inside a larger application that configures its own handlers.
if not logger.handlers:
    _console_handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(levelname)s] %(message)s")
    _console_handler.setFormatter(_formatter)
    logger.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# Section 4: Enums
# ---------------------------------------------------------------------------

class TriageAction(Enum):
    """Possible outcomes of a triage decision."""
    REPLIED = "replied"
    ESCALATED = "escalated"


class EscalationReason(Enum):
    """Reason codes identifying which rule triggered an escalation or reply decision."""
    CRITICAL_RISK = "critical_risk"
    HIGH_RISK = "high_risk"
    LOW_CONFIDENCE = "low_confidence"
    UNSUPPORTED_REQUEST = "unsupported_request"
    MULTI_ISSUE = "multi_issue"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Section 5: Module-Level Constants
# ---------------------------------------------------------------------------

# Priority-ordered list of escalation rule triggers.
# Rules are evaluated in this order inside DecisionEngine.decide():
#   1. RiskLevel.CRITICAL          → always escalate (highest priority)
#   2. RiskLevel.HIGH              → escalate when combined with low confidence
#   3. RequestType.INVALID         → reply with out-of-scope template
#   4. EscalationReason.LOW_CONFIDENCE       → escalate when avg confidence < CONFIDENCE_MIN
#   5. EscalationReason.UNSUPPORTED_REQUEST  → escalate when domain threshold not met
#   6. EscalationReason.MULTI_ISSUE          → (reserved for future multi-issue rule)
#   7. EscalationReason.UNKNOWN              → all checks passed; safe to reply
ESCALATION_RULE_PRIORITY_ORDER: list = [
    RiskLevel.CRITICAL,
    RiskLevel.HIGH,
    RequestType.INVALID,
    EscalationReason.LOW_CONFIDENCE,
    EscalationReason.UNSUPPORTED_REQUEST,
    EscalationReason.MULTI_ISSUE,
    EscalationReason.UNKNOWN,
]

# Domain-specific confidence thresholds for sensitive product areas.
# When a ticket's detected domain and product area appear in this dict,
# the average classification confidence must meet or exceed the listed
# threshold before an automated reply is permitted. Areas not listed here
# fall back to the global CONFIDENCE_MIN threshold.
DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS: dict = {
    "hackerrank": {
        "billing": 0.95,
        "account": 0.98,
        "assessments": 0.8,
    },
    "claude": {
        "api": 0.85,
        "subscription": 0.95,
        "account": 0.98,
    },
    "visa": {
        "payments": 0.95,
        "refunds": 0.98,
        "disputes": 0.98,
    },
}

# ---------------------------------------------------------------------------
# Section 6: DecisionResult Dataclass
# ---------------------------------------------------------------------------

@dataclass
class DecisionResult:
    """
    Typed, structured value object carrying the complete output of a single
    triage decision.

    Fields:
        action           — Final routing decision: REPLIED or ESCALATED.
        confidence       — Confidence in the decision, in [0.0, 1.0].
        reason           — Enum value identifying which rule triggered the decision.
        reasoning_text   — Human-readable explanation of the decision.
        triggered_rules  — Ordered list of rule names that were evaluated.
        suggested_response — Pre-formatted response text for the ticket submitter.
        domain           — Domain from the classification result.
        request_type     — Request type from the classification result.
        risk_level       — Risk level from the classification result.
        audit_trail      — Full structured record of inputs, rules, and outputs.
    """

    action: TriageAction
    confidence: float
    reason: EscalationReason
    reasoning_text: str
    triggered_rules: list
    suggested_response: str
    domain: Domain
    request_type: RequestType
    risk_level: RiskLevel
    audit_trail: dict

    def __repr__(self) -> str:
        """Return a human-readable string representation of this DecisionResult."""
        return (
            f"DecisionResult("
            f"action={self.action.value!r}, "
            f"confidence={self.confidence:.4f}, "
            f"reason={self.reason.value!r}, "
            f"domain={self.domain.value!r}, "
            f"request_type={self.request_type.value!r}, "
            f"risk_level={self.risk_level.value!r}, "
            f"reasoning_text={self.reasoning_text!r}, "
            f"triggered_rules={self.triggered_rules!r})"
        )

    def to_dict(self) -> dict:
        """
        Return a plain dict representation of all fields.

        Enum values are serialised to their `.value` strings so the result
        is safe for JSON serialisation and downstream consumers that do not
        import the enum types.
        """
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "reason": self.reason.value,
            "reasoning_text": self.reasoning_text,
            "triggered_rules": list(self.triggered_rules),
            "suggested_response": self.suggested_response,
            "domain": self.domain.value,
            "request_type": self.request_type.value,
            "risk_level": self.risk_level.value,
            "audit_trail": dict(self.audit_trail),
        }

    def is_safe_to_reply(self) -> bool:
        """
        Return True if and only if this decision is safe to act on as an
        automated reply.

        A decision is considered safe to reply when:
          - action == TriageAction.REPLIED  (the engine decided to reply, not escalate)
          - confidence >= CONFIDENCE_HIGH   (the engine is highly confident in the decision)

        Returns:
            True when both conditions are met; False otherwise.
        """
        return self.action == TriageAction.REPLIED and self.confidence >= CONFIDENCE_HIGH


# ---------------------------------------------------------------------------
# Section 7: EscalationRuleChecker Class
# ---------------------------------------------------------------------------

class EscalationRuleChecker:
    """
    Modular, single-responsibility rule evaluators for the triage decision engine.

    Each method checks exactly one escalation condition and returns a
    ``(triggered: bool, reason_text: str | None)`` tuple.

    Contract:
    - Returns ``(True, human_readable_reason)`` when the rule triggers.
    - Returns ``(False, None)`` when the rule does not trigger.
    - Never raises exceptions for expected inputs.
    """

    def check_critical_risk(
        self, risk_assessment: RiskAssessment
    ) -> tuple:
        """
        Check whether the risk assessment indicates a CRITICAL risk level.

        Args:
            risk_assessment: A RiskAssessment instance from the classifier.

        Returns:
            ``(True, "Critical risk detected")`` when ``risk_assessment.level``
            is ``RiskLevel.CRITICAL``; ``(False, None)`` otherwise.
        """
        if risk_assessment.level == RiskLevel.CRITICAL:
            return (True, "Critical risk detected")
        return (False, None)

    def check_high_risk(
        self, risk_assessment: RiskAssessment
    ) -> tuple:
        """
        Check whether the risk assessment indicates a HIGH risk level.

        Args:
            risk_assessment: A RiskAssessment instance from the classifier.

        Returns:
            ``(True, reason_str)`` when ``risk_assessment.level`` is
            ``RiskLevel.HIGH``, where ``reason_str`` includes the risk
            assessment's own reason text; ``(False, None)`` otherwise.
        """
        if risk_assessment.level == RiskLevel.HIGH:
            reason = f"High risk detected: {risk_assessment.reason}"
            return (True, reason)
        return (False, None)

    def check_invalid_request(
        self, request_type_result: RequestTypeResult
    ) -> tuple:
        """
        Check whether the request type is INVALID (out-of-scope).

        Args:
            request_type_result: A RequestTypeResult instance from the classifier.

        Returns:
            ``(True, "Invalid/out-of-scope request")`` when
            ``request_type_result.type`` is ``RequestType.INVALID``;
            ``(False, None)`` otherwise.
        """
        if request_type_result.type == RequestType.INVALID:
            return (True, "Invalid/out-of-scope request")
        return (False, None)

    def check_low_confidence(
        self, classification_result: ClassificationResult
    ) -> tuple:
        """
        Check whether the average classification confidence is below the
        minimum threshold.

        Computes the arithmetic mean of:
        - ``classification_result.request_type.confidence``
        - ``classification_result.product_area.confidence``
        - ``classification_result.risk.confidence``

        Args:
            classification_result: A ClassificationResult instance.

        Returns:
            ``(True, f"Low confidence ({avg:.2f})")`` when the average is
            less than ``CONFIDENCE_MIN``; ``(False, None)`` otherwise.
        """
        confidences = [
            classification_result.request_type.confidence,
            classification_result.product_area.confidence,
            classification_result.risk.confidence,
        ]
        avg = sum(confidences) / len(confidences)

        if avg < CONFIDENCE_MIN:
            return (True, f"Low confidence ({avg:.2f})")
        return (False, None)

    def check_domain_specific_thresholds(
        self, classification_result: ClassificationResult
    ) -> tuple:
        """
        Check whether the average confidence meets the domain-specific
        threshold for the detected product area.

        Looks up the domain and product area in
        ``DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS``. If both are present and
        the average confidence is below the required threshold, the rule
        triggers.

        Args:
            classification_result: A ClassificationResult instance.

        Returns:
            ``(True, reason_str)`` when the domain and area are both in the
            thresholds dict AND the average confidence is below the required
            threshold; ``(False, None)`` when the domain is not in the dict,
            the area is not in the domain's map, or confidence meets the
            threshold.
        """
        domain_key = classification_result.detected_domain.value
        area_key = classification_result.product_area.area

        # Domain not in thresholds — no domain-specific rule applies
        if domain_key not in DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS:
            return (False, None)

        domain_thresholds = DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS[domain_key]

        # Area not in domain's threshold map — no area-specific rule applies
        if area_key not in domain_thresholds:
            return (False, None)

        required_threshold = domain_thresholds[area_key]

        confidences = [
            classification_result.request_type.confidence,
            classification_result.product_area.confidence,
            classification_result.risk.confidence,
        ]
        avg = sum(confidences) / len(confidences)

        if avg < required_threshold:
            reason = (
                f"Domain threshold not met for {domain_key}/{area_key}: "
                f"{avg:.2f} < {required_threshold}"
            )
            return (True, reason)

        return (False, None)

    def check_multi_issue_ticket(self, ticket_text: str) -> tuple:
        """
        Check whether the ticket text contains multiple issues, indicated by
        more than 3 question mark characters.

        Args:
            ticket_text: The raw or cleaned text of the support ticket.

        Returns:
            ``(True, "Ticket contains multiple issues")`` when the count of
            ``"?"`` characters exceeds 3; ``(False, None)`` otherwise.
        """
        question_count = ticket_text.count("?") if ticket_text else 0
        if question_count > 3:
            return (True, "Ticket contains multiple issues")
        return (False, None)
