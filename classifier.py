"""
classifier.py — Support Ticket Triage Classifier Module

Purpose:
    This module is the core intelligence engine of the support ticket triage
    system. It classifies incoming support tickets across four dimensions:
    request type, product area, risk level, and domain. All classification
    logic is driven by pattern matching and keyword analysis using constants
    defined in config.py — no machine-learning dependencies are required.

Responsibilities:
    - Classify ticket request type (bug, feature request, product issue, invalid)
    - Detect the domain a ticket belongs to (HackerRank, Claude, Visa, or unknown)
    - Identify the product area within a domain (e.g. billing, account, api)
    - Assess the risk level of a ticket (critical, high, or low)
    - Expose a Classifier class for single-ticket and batch classification
    - Provide a PatternMatcher utility for reusable multi-category keyword matching
    - Provide module-level helper functions for text analysis

Typical usage:
    from data_loader import load_tickets
    from classifier import Classifier

    tickets = load_tickets("inputs/sample_support_tickets.csv")
    clf = Classifier()
    results = clf.classify_batch(tickets)
    summary = clf.get_classification_summary()

    for result in results:
        print(result.request_type.type, result.risk.level, result.detected_domain)
"""

# ---------------------------------------------------------------------------
# Section 1: Standard Library Imports
# ---------------------------------------------------------------------------

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, List

# ---------------------------------------------------------------------------
# Section 2: Local Module Imports
# ---------------------------------------------------------------------------

from config import (
    REQUEST_TYPE_PATTERNS,
    RISK_ESCALATION_KEYWORDS,
    PRODUCT_AREA_MAPPINGS,
    SUPPORTED_DOMAINS,
)
from data_loader import TicketRecord, sanitize_ticket_text

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
    _console_handler.setLevel(logging.DEBUG)
    logger.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# Section 4: Enums
# ---------------------------------------------------------------------------

class RequestType(Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    PRODUCT_ISSUE = "product_issue"
    INVALID = "invalid"


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    LOW = "low"


class Domain(Enum):
    HACKERRANK = "hackerrank"
    CLAUDE = "claude"
    VISA = "visa"
    UNKNOWN = "unknown"

# ---------------------------------------------------------------------------
# Section 5: Result Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RequestTypeResult:
    """Result of request type classification."""
    type: RequestType
    confidence: float
    matched_patterns: list

    def __repr__(self) -> str:
        return (
            f"RequestTypeResult(type={self.type.value!r}, "
            f"confidence={self.confidence}, "
            f"matched_patterns={self.matched_patterns!r})"
        )


@dataclass
class ProductAreaResult:
    """Result of product area classification."""
    area: str
    domain: Domain
    confidence: float
    matched_keywords: list

    def __repr__(self) -> str:
        return (
            f"ProductAreaResult(area={self.area!r}, "
            f"domain={self.domain.value!r}, "
            f"confidence={self.confidence}, "
            f"matched_keywords={self.matched_keywords!r})"
        )


@dataclass
class RiskAssessment:
    """Result of risk level assessment."""
    level: RiskLevel
    confidence: float
    risk_keywords: list
    reason: str

    def __repr__(self) -> str:
        return (
            f"RiskAssessment(level={self.level.value!r}, "
            f"confidence={self.confidence}, "
            f"risk_keywords={self.risk_keywords!r}, "
            f"reason={self.reason!r})"
        )


@dataclass
class ClassificationResult:
    """Complete classification result for a single support ticket."""
    request_type: RequestTypeResult
    product_area: ProductAreaResult
    risk: RiskAssessment
    detected_domain: Domain
    raw_text: str
    cleaned_text: str

    def to_dict(self) -> dict:
        """Serialise all fields — including nested result objects — to a plain dict."""
        return {
            "request_type": {
                "type": self.request_type.type.value,
                "confidence": self.request_type.confidence,
                "matched_patterns": self.request_type.matched_patterns,
            },
            "product_area": {
                "area": self.product_area.area,
                "domain": self.product_area.domain.value,
                "confidence": self.product_area.confidence,
                "matched_keywords": self.product_area.matched_keywords,
            },
            "risk": {
                "level": self.risk.level.value,
                "confidence": self.risk.confidence,
                "risk_keywords": self.risk.risk_keywords,
                "reason": self.risk.reason,
            },
            "detected_domain": self.detected_domain.value,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
        }

    def __repr__(self) -> str:
        return (
            f"ClassificationResult("
            f"request_type={self.request_type!r}, "
            f"product_area={self.product_area!r}, "
            f"risk={self.risk!r}, "
            f"detected_domain={self.detected_domain.value!r}, "
            f"raw_text={self.raw_text!r}, "
            f"cleaned_text={self.cleaned_text!r})"
        )

# ---------------------------------------------------------------------------
# Section 6: PatternMatcher Utility Class
# ---------------------------------------------------------------------------

class PatternMatcher:
    """Reusable utility for multi-category keyword/pattern matching and confidence scoring."""

    @staticmethod
    def match_patterns(text: str, patterns_dict: dict) -> dict:
        """
        Perform case-insensitive substring matching of patterns against text.

        Args:
            text: The input string to search within.
            patterns_dict: A dict mapping category strings to lists of pattern strings.

        Returns:
            A dict with keys:
              - matched_categories (list): categories that had at least one match
              - match_details (dict): {category: [matched_patterns, ...]}
              - total_matches (int): sum of all per-category match counts
        """
        if not text:
            return {"matched_categories": [], "match_details": {}, "total_matches": 0}

        lower_text = text.lower()
        match_details = {}
        total_matches = 0

        for category, patterns in patterns_dict.items():
            # Loop invariant: total_matches reflects all categories processed so far
            category_matches = []
            for pattern in patterns:
                if pattern.lower() in lower_text:
                    category_matches.append(pattern)
                    total_matches += 1
            if category_matches:
                match_details[category] = category_matches

        matched_categories = list(match_details.keys())

        return {
            "matched_categories": matched_categories,
            "match_details": match_details,
            "total_matches": total_matches,
        }

    @staticmethod
    def score_matches(match_details: dict, patterns_dict: dict) -> float:
        """
        Compute a normalised confidence score based on match density.

        Args:
            match_details: Dict of {category: [matched_patterns, ...]} from match_patterns.
            patterns_dict: The original patterns dict used for matching.

        Returns:
            A float in [0.0, 1.0] representing the proportion of total patterns matched.
            Returns 0.0 for empty match_details or empty patterns_dict.
        """
        if not match_details or not patterns_dict:
            return 0.0

        total_patterns = sum(len(patterns) for patterns in patterns_dict.values())
        if total_patterns == 0:
            return 0.0

        total_matched = sum(len(matches) for matches in match_details.values())
        raw_score = total_matched / total_patterns

        return min(1.0, raw_score)


# ---------------------------------------------------------------------------
# Section 7: Classifier Class
# ---------------------------------------------------------------------------

class Classifier:
    """Main classification engine for support ticket triage."""

    def __init__(self):
        # Initialise summary counters
        self._total_classified = 0
        self._by_request_type = {rt.value: 0 for rt in RequestType}
        self._by_risk_level = {rl.value: 0 for rl in RiskLevel}
        self._by_domain = {d.value: 0 for d in Domain}

    def detect_domain(self, ticket_text: str, specified_domain: Optional[str] = None) -> Tuple[Domain, float]:
        """
        Detect the domain a support ticket belongs to.

        Args:
            ticket_text: The text of the support ticket.
            specified_domain: If provided, return this domain with confidence 1.0.

        Returns:
            A tuple of (Domain, confidence) where confidence is in [0.0, 1.0].
        """
        if specified_domain is not None:
            return (Domain[specified_domain.upper()], 1.0)

        domain_keywords = {
            Domain.HACKERRANK: ["assessment", "test", "contest", "hackerrank", "coding challenge"],
            Domain.CLAUDE: ["claude", "api", "model", "tokens", "conversation"],
            Domain.VISA: ["visa", "card", "payment", "refund", "transaction"],
        }

        lower_text = ticket_text.lower() if ticket_text else ""
        best_domain = None
        best_count = 0

        for domain, keywords in domain_keywords.items():
            count = sum(1 for kw in keywords if kw in lower_text)
            if count > best_count:
                best_count = count
                best_domain = domain

        if best_count > 0:
            return (best_domain, 0.85)

        return (Domain.UNKNOWN, 0.3)

    def classify_request_type(self, ticket_text: str) -> RequestTypeResult:
        """
        Classify the request type of a support ticket.

        Args:
            ticket_text: The text of the support ticket.

        Returns:
            A RequestTypeResult with the classified type, confidence, and
            matched patterns.
        """
        # Return INVALID for empty or whitespace-only text
        if not ticket_text or not ticket_text.strip():
            return RequestTypeResult(
                type=RequestType.INVALID,
                confidence=0.0,
                matched_patterns=[],
            )

        # Use PatternMatcher to match against REQUEST_TYPE_PATTERNS
        result = PatternMatcher.match_patterns(ticket_text, REQUEST_TYPE_PATTERNS)
        match_details = result["match_details"]

        # No patterns matched — return default fallback
        if not match_details:
            return RequestTypeResult(
                type=RequestType.PRODUCT_ISSUE,
                confidence=0.5,
                matched_patterns=[],
            )

        # Determine winner by highest match count per category
        best_category = max(match_details, key=lambda cat: len(match_details[cat]))
        winning_patterns = match_details[best_category]

        # Map category string to RequestType enum and confidence
        confidence_map = {
            "bug": (RequestType.BUG, 0.9),
            "feature_request": (RequestType.FEATURE_REQUEST, 0.85),
            "product_issue": (RequestType.PRODUCT_ISSUE, 0.75),
        }

        request_type, confidence = confidence_map.get(
            best_category, (RequestType.PRODUCT_ISSUE, 0.75)
        )

        return RequestTypeResult(
            type=request_type,
            confidence=confidence,
            matched_patterns=winning_patterns,
        )

    def classify_product_area(self, ticket_text: str, domain: Optional[Domain] = None) -> ProductAreaResult:
        """
        Classify the product area of a support ticket for a given domain.

        Args:
            ticket_text: The text of the support ticket.
            domain: The domain to classify within. If None or Domain.UNKNOWN,
                    returns a generic "general" result.

        Returns:
            A ProductAreaResult with the detected area, domain, confidence,
            and matched keywords.
        """
        # Return generic result for unknown/unspecified domain
        if domain is None or domain == Domain.UNKNOWN:
            return ProductAreaResult(
                area="general",
                domain=Domain.UNKNOWN,
                confidence=0.3,
                matched_keywords=[],
            )

        # Scan ticket text against product area mappings for the known domain
        areas = PRODUCT_AREA_MAPPINGS[domain.value]
        lower_text = ticket_text.lower() if ticket_text else ""

        for area in areas:
            # Replace underscores with spaces for matching (e.g. "coding_challenges" → "coding challenges")
            keyword = area.lower().replace("_", " ")
            if keyword in lower_text:
                return ProductAreaResult(
                    area=area,
                    domain=domain,
                    confidence=0.85,
                    matched_keywords=[keyword],
                )

        # No match found — fall back to first area in mapping
        return ProductAreaResult(
            area=areas[0],
            domain=domain,
            confidence=0.5,
            matched_keywords=[],
        )

    def assess_risk_level(self, ticket_text: str) -> RiskAssessment:
        """
        Assess the risk level of a support ticket based on escalation keywords.

        Counts the number of distinct RISK_ESCALATION_KEYWORDS categories that
        have at least one matching keyword in the ticket text, then maps that
        score to a risk level and confidence value.

        Score mapping:
            >= 3 categories matched → CRITICAL, confidence 1.0  (log WARNING)
            == 2 categories matched → HIGH,     confidence 0.95 (log INFO)
            == 1 category  matched → HIGH,     confidence 0.8  (log INFO)
            == 0 categories matched → LOW,      confidence 0.9  (log DEBUG)

        Args:
            ticket_text: The text of the support ticket.

        Returns:
            A RiskAssessment with level, confidence, matched risk_keywords,
            and a human-readable reason.
        """
        lower_text = ticket_text.lower() if ticket_text else ""

        # Collect all matched keywords and count distinct matched categories
        all_matched_keywords: list = []
        matched_category_count = 0

        for category, keywords in RISK_ESCALATION_KEYWORDS.items():
            category_matches = [kw for kw in keywords if kw.lower() in lower_text]
            if category_matches:
                matched_category_count += 1
                all_matched_keywords.extend(category_matches)

        # Determine risk level, confidence, and reason based on score
        if matched_category_count >= 3:
            level = RiskLevel.CRITICAL
            confidence = 1.0
            reason = (
                f"Ticket matches {matched_category_count} distinct risk categories "
                f"({', '.join(all_matched_keywords)}), indicating a critical escalation risk."
            )
            logger.warning("Risk assessment: CRITICAL — %d categories matched: %s",
                           matched_category_count, all_matched_keywords)

        elif matched_category_count == 2:
            level = RiskLevel.HIGH
            confidence = 0.95
            reason = (
                f"Ticket matches {matched_category_count} distinct risk categories "
                f"({', '.join(all_matched_keywords)}), indicating a high escalation risk."
            )
            logger.info("Risk assessment: HIGH (score=2) — categories matched: %s",
                        all_matched_keywords)

        elif matched_category_count == 1:
            level = RiskLevel.HIGH
            confidence = 0.8
            reason = (
                f"Ticket matches 1 risk category "
                f"({', '.join(all_matched_keywords)}), indicating an elevated risk."
            )
            logger.info("Risk assessment: HIGH (score=1) — keywords matched: %s",
                        all_matched_keywords)

        else:
            level = RiskLevel.LOW
            confidence = 0.9
            reason = "No risk escalation keywords detected; ticket appears low risk."
            logger.debug("Risk assessment: LOW — no risk keywords matched.")

        return RiskAssessment(
            level=level,
            confidence=confidence,
            risk_keywords=all_matched_keywords,
            reason=reason,
        )

    def classify_ticket(self, ticket: TicketRecord) -> ClassificationResult:
        """
        Classify a single support ticket across all four dimensions.

        Args:
            ticket: A TicketRecord instance to classify.

        Returns:
            A ClassificationResult with request type, product area, risk
            assessment, detected domain, raw text, and cleaned text.

        Raises:
            TypeError: If ticket is not a TicketRecord instance.
        """
        if not isinstance(ticket, TicketRecord):
            raise TypeError(
                f"classify_ticket expects a TicketRecord instance, got {type(ticket).__name__!r}"
            )

        # Build full text from subject and issue
        full_text = f"{ticket.subject} {ticket.issue}"

        # Sanitize the combined text
        cleaned_text = sanitize_ticket_text(full_text)

        # Run all four classification steps
        request_type = self.classify_request_type(cleaned_text)
        domain, domain_confidence = self.detect_domain(cleaned_text)
        product_area = self.classify_product_area(cleaned_text, domain)
        risk = self.assess_risk_level(cleaned_text)

        # Assemble the result
        result = ClassificationResult(
            request_type=request_type,
            product_area=product_area,
            risk=risk,
            detected_domain=domain,
            raw_text=full_text,
            cleaned_text=cleaned_text,
        )

        # Update internal summary statistics
        self._total_classified += 1
        self._by_request_type[result.request_type.type.value] += 1
        self._by_risk_level[result.risk.level.value] += 1
        self._by_domain[result.detected_domain.value] += 1

        logger.info(
            "Classified ticket id=%s: type=%s, domain=%s, risk=%s",
            ticket.id,
            result.request_type.type.value,
            result.detected_domain.value,
            result.risk.level.value,
        )

        return result

    def classify_batch(self, tickets_list: list) -> List[ClassificationResult]:
        """
        Classify a list of support tickets.

        Args:
            tickets_list: A list of TicketRecord instances to classify.

        Returns:
            A list of ClassificationResult objects in the same order as the
            input list. Returns an empty list for empty input.
        """
        if not tickets_list:
            return []

        results = []
        for ticket in tickets_list:
            result = self.classify_ticket(ticket)
            results.append(result)

        return results

    def get_classification_summary(self) -> dict:
        """
        Return a summary of all classifications performed so far.

        Counters accumulate across all calls to classify_ticket and
        classify_batch since this Classifier instance was created.

        Returns:
            A dict with keys:
              - total_classified (int): total number of tickets classified
              - by_request_type (dict): counts per RequestType value
              - by_risk_level (dict): counts per RiskLevel value
              - by_domain (dict): counts per Domain value
              - high_risk_count (int): count of CRITICAL + HIGH risk tickets
        """
        high_risk_count = (
            self._by_risk_level.get(RiskLevel.CRITICAL.value, 0)
            + self._by_risk_level.get(RiskLevel.HIGH.value, 0)
        )

        return {
            "total_classified": self._total_classified,
            "by_request_type": dict(self._by_request_type),
            "by_risk_level": dict(self._by_risk_level),
            "by_domain": dict(self._by_domain),
            "high_risk_count": high_risk_count,
        }

# ---------------------------------------------------------------------------
# Section 8: Module-Level Utility Functions
# ---------------------------------------------------------------------------

def infer_company_from_text(text: str) -> Optional[str]:
    """
    Infer the company a support ticket is related to based on domain keywords.

    Uses the same keyword tables as Classifier.detect_domain with
    case-insensitive matching. Returns the company with the most keyword
    matches, or None when no keywords are found.

    Args:
        text: The input text to analyse.

    Returns:
        "HackerRank", "Claude", "Visa", or None.
    """
    domain_keywords = {
        "HackerRank": ["assessment", "test", "contest", "hackerrank", "coding challenge"],
        "Claude": ["claude", "api", "model", "tokens", "conversation"],
        "Visa": ["visa", "card", "payment", "refund", "transaction"],
    }

    lower_text = text.lower() if text else ""
    best_company = None
    best_count = 0

    for company, keywords in domain_keywords.items():
        count = sum(1 for kw in keywords if kw in lower_text)
        if count > best_count:
            best_count = count
            best_company = company

    return best_company if best_count > 0 else None


def extract_keywords(text: str, keyword_dict: dict) -> dict:
    """
    Extract keywords from text grouped by category.

    Performs case-insensitive matching of each keyword in keyword_dict
    against the input text. Categories with no matches are omitted from
    the result.

    Args:
        text: The input text to search within.
        keyword_dict: A dict mapping category keys to lists of keyword strings.

    Returns:
        A dict mapping each category key to a list of matched keywords.
        Categories with no matches are not included.
    """
    lower_text = text.lower() if text else ""
    result = {}

    for category, keywords in keyword_dict.items():
        matches = [kw for kw in keywords if kw.lower() in lower_text]
        if matches:
            result[category] = matches

    return result


def score_text_length_confidence(text: str) -> float:
    """
    Return a confidence score based on the length of the input text.

    Longer texts generally provide more signal for classification, so
    they receive higher confidence scores.

    Args:
        text: The input text to score.

    Returns:
        0.7  for text shorter than 50 characters,
        0.85 for text between 50 and 199 characters (inclusive),
        1.0  for text of 200 or more characters.
    """
    length = len(text) if text else 0

    if length < 50:
        return 0.7
    elif length < 200:
        return 0.85
    else:
        return 1.0
