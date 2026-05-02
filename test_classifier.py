"""
test_classifier.py — Unit tests for classifier.py

Organised into 8 test classes covering all public APIs:
  TestEnums, TestRequestTypeClassification, TestDomainDetection,
  TestProductAreaClassification, TestRiskAssessment,
  TestClassificationResult, TestBatchClassification, TestUtilityFunctions

Requirements: 14.1–14.10
"""

import logging
import pytest

from classifier import (
    Classifier,
    ClassificationResult,
    Domain,
    PatternMatcher,
    ProductAreaResult,
    RequestType,
    RequestTypeResult,
    RiskAssessment,
    RiskLevel,
    extract_keywords,
    infer_company_from_text,
    score_text_length_confidence,
)
from data_loader import TicketRecord
from config import PRODUCT_AREA_MAPPINGS, RISK_ESCALATION_KEYWORDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ticket(subject: str = "", issue: str = "test issue", ticket_id: int = 1) -> TicketRecord:
    """Create a minimal TicketRecord for testing."""
    return TicketRecord(id=ticket_id, issue=issue, subject=subject)


# ---------------------------------------------------------------------------
# TestEnums — 3 tests
# ---------------------------------------------------------------------------

class TestEnums:
    """Verify enum values, membership, and string representations."""

    def test_enum_values(self):
        """Verify the string values of all enum members."""
        # RequestType
        assert RequestType.BUG.value == "bug"
        assert RequestType.FEATURE_REQUEST.value == "feature_request"
        assert RequestType.PRODUCT_ISSUE.value == "product_issue"
        assert RequestType.INVALID.value == "invalid"
        # RiskLevel
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.LOW.value == "low"
        # Domain
        assert Domain.HACKERRANK.value == "hackerrank"
        assert Domain.CLAUDE.value == "claude"
        assert Domain.VISA.value == "visa"
        assert Domain.UNKNOWN.value == "unknown"

    def test_enum_membership(self):
        """Verify that expected members exist in each enum."""
        assert RequestType.BUG in RequestType
        assert RequestType.FEATURE_REQUEST in RequestType
        assert RequestType.PRODUCT_ISSUE in RequestType
        assert RequestType.INVALID in RequestType

        assert RiskLevel.CRITICAL in RiskLevel
        assert RiskLevel.HIGH in RiskLevel
        assert RiskLevel.LOW in RiskLevel

        assert Domain.HACKERRANK in Domain
        assert Domain.CLAUDE in Domain
        assert Domain.VISA in Domain
        assert Domain.UNKNOWN in Domain

    def test_enum_string_representations(self):
        """Verify __str__ / name attributes for all three enums."""
        # Enum name attribute
        assert RequestType.BUG.name == "BUG"
        assert RiskLevel.CRITICAL.name == "CRITICAL"
        assert Domain.HACKERRANK.name == "HACKERRANK"

        # str() includes the class name and member name
        assert "BUG" in str(RequestType.BUG)
        assert "CRITICAL" in str(RiskLevel.CRITICAL)
        assert "HACKERRANK" in str(Domain.HACKERRANK)


# ---------------------------------------------------------------------------
# TestRequestTypeClassification — 6 tests
# ---------------------------------------------------------------------------

class TestRequestTypeClassification:
    """Tests for Classifier.classify_request_type."""

    def setup_method(self):
        self.clf = Classifier()

    def test_bug_detection(self):
        """Text with bug keywords → RequestType.BUG, confidence 0.9."""
        result = self.clf.classify_request_type("There is a bug and a crash and an error")
        assert result.type == RequestType.BUG
        assert result.confidence == 0.9
        assert len(result.matched_patterns) > 0

    def test_feature_request_detection(self):
        """Text with feature request keywords → RequestType.FEATURE_REQUEST, confidence 0.85."""
        result = self.clf.classify_request_type("feature request: please add dark mode")
        assert result.type == RequestType.FEATURE_REQUEST
        assert result.confidence == 0.85
        assert len(result.matched_patterns) > 0

    def test_product_issue_detection(self):
        """Text with product issue keywords → RequestType.PRODUCT_ISSUE, confidence 0.75."""
        result = self.clf.classify_request_type("issue with the dashboard, seems like a problem")
        assert result.type == RequestType.PRODUCT_ISSUE
        assert result.confidence == 0.75
        assert len(result.matched_patterns) > 0

    def test_invalid_empty_text(self):
        """Empty or whitespace-only text → RequestType.INVALID, confidence 0.0."""
        for text in ("", "   ", "\t\n"):
            result = self.clf.classify_request_type(text)
            assert result.type == RequestType.INVALID
            assert result.confidence == 0.0
            assert result.matched_patterns == []

    def test_priority_ordering_highest_count_wins(self):
        """When multiple categories match, the one with the most matches wins."""
        # Craft text with 3 bug keywords and only 1 feature_request keyword
        text = "bug crash error not working please add"
        result = self.clf.classify_request_type(text)
        # bug has 3 matches ("bug", "crash", "error", "not working") vs feature_request 1 ("please add")
        assert result.type == RequestType.BUG

    def test_case_insensitivity(self):
        """'BUG', 'Bug', and 'bug' all match the bug pattern."""
        for variant in ("BUG", "Bug", "bug"):
            result = self.clf.classify_request_type(f"I found a {variant} in the system")
            assert result.type == RequestType.BUG, f"Expected BUG for variant {variant!r}"


# ---------------------------------------------------------------------------
# TestDomainDetection — 6 tests
# ---------------------------------------------------------------------------

class TestDomainDetection:
    """Tests for Classifier.detect_domain."""

    def setup_method(self):
        self.clf = Classifier()

    def test_hackerrank_keywords_detected(self):
        """Text with HackerRank keywords → Domain.HACKERRANK, confidence 0.85."""
        domain, confidence = self.clf.detect_domain("I have an issue with my assessment on hackerrank")
        assert domain == Domain.HACKERRANK
        assert confidence == 0.85

    def test_claude_keywords_detected(self):
        """Text with Claude keywords → Domain.CLAUDE, confidence 0.85."""
        domain, confidence = self.clf.detect_domain("The claude api is returning wrong model output")
        assert domain == Domain.CLAUDE
        assert confidence == 0.85

    def test_visa_keywords_detected(self):
        """Text with Visa keywords → Domain.VISA, confidence 0.85."""
        domain, confidence = self.clf.detect_domain("My visa card payment was declined and I need a refund")
        assert domain == Domain.VISA
        assert confidence == 0.85

    def test_specified_domain_override(self):
        """specified_domain overrides keyword detection and returns confidence 1.0."""
        domain, confidence = self.clf.detect_domain("anything here", specified_domain="claude")
        assert domain == Domain.CLAUDE
        assert confidence == 1.0

    def test_unknown_domain_no_keywords(self):
        """Text with no domain keywords → Domain.UNKNOWN, confidence 0.3."""
        domain, confidence = self.clf.detect_domain("hello world, nothing relevant here")
        assert domain == Domain.UNKNOWN
        assert confidence == 0.3

    def test_confidence_values_are_floats_in_range(self):
        """All returned confidence values are floats in [0.0, 1.0]."""
        texts = [
            "assessment on hackerrank",
            "claude api tokens",
            "visa card payment",
            "no keywords at all",
        ]
        for text in texts:
            _, confidence = self.clf.detect_domain(text)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# TestProductAreaClassification — 7 tests
# ---------------------------------------------------------------------------

class TestProductAreaClassification:
    """Tests for Classifier.classify_product_area."""

    def setup_method(self):
        self.clf = Classifier()

    def test_hackerrank_matching_keyword(self):
        """HackerRank domain with 'billing' keyword → area='billing', confidence 0.85."""
        result = self.clf.classify_product_area("I have a billing issue", domain=Domain.HACKERRANK)
        assert result.area == "billing"
        assert result.confidence == 0.85
        assert result.domain == Domain.HACKERRANK

    def test_claude_matching_keyword(self):
        """Claude domain with 'api' keyword → area='api', confidence 0.85."""
        result = self.clf.classify_product_area("The api endpoint is broken", domain=Domain.CLAUDE)
        assert result.area == "api"
        assert result.confidence == 0.85
        assert result.domain == Domain.CLAUDE

    def test_visa_matching_keyword(self):
        """Visa domain with 'fraud' keyword → area='fraud', confidence 0.85."""
        # Use text that only contains 'fraud' and not earlier-listed areas like 'account'
        result = self.clf.classify_product_area("I suspect fraud on my card", domain=Domain.VISA)
        # 'cards' appears before 'fraud' in the mapping, so use text with only 'fraud'
        result = self.clf.classify_product_area("suspicious fraud detected", domain=Domain.VISA)
        assert result.area == "fraud"
        assert result.confidence == 0.85
        assert result.domain == Domain.VISA

    def test_hackerrank_no_match_fallback(self):
        """HackerRank domain with no matching keyword → first area ('assessments'), confidence 0.5."""
        result = self.clf.classify_product_area("something completely unrelated", domain=Domain.HACKERRANK)
        assert result.area == PRODUCT_AREA_MAPPINGS["hackerrank"][0]
        assert result.confidence == 0.5
        assert result.matched_keywords == []

    def test_claude_no_match_fallback(self):
        """Claude domain with no matching keyword → first area ('api'), confidence 0.5."""
        result = self.clf.classify_product_area("something completely unrelated", domain=Domain.CLAUDE)
        assert result.area == PRODUCT_AREA_MAPPINGS["claude"][0]
        assert result.confidence == 0.5
        assert result.matched_keywords == []

    def test_visa_no_match_fallback(self):
        """Visa domain with no matching keyword → first area ('transactions'), confidence 0.5."""
        result = self.clf.classify_product_area("something completely unrelated", domain=Domain.VISA)
        assert result.area == PRODUCT_AREA_MAPPINGS["visa"][0]
        assert result.confidence == 0.5
        assert result.matched_keywords == []

    def test_unknown_domain_returns_general(self):
        """Domain.UNKNOWN → area='general', confidence 0.3."""
        for domain_arg in (Domain.UNKNOWN, None):
            result = self.clf.classify_product_area("any text", domain=domain_arg)
            assert result.area == "general"
            assert result.confidence == 0.3
            assert result.domain == Domain.UNKNOWN
            assert result.matched_keywords == []


# ---------------------------------------------------------------------------
# TestRiskAssessment — 6 tests
# ---------------------------------------------------------------------------

class TestRiskAssessment:
    """Tests for Classifier.assess_risk_level."""

    def setup_method(self):
        self.clf = Classifier()

    def test_critical_three_or_more_categories(self):
        """Text matching keywords from 3+ categories → CRITICAL, confidence 1.0."""
        # account_access + billing_money + security
        text = "account locked refund fraud"
        result = self.clf.assess_risk_level(text)
        assert result.level == RiskLevel.CRITICAL
        assert result.confidence == 1.0
        assert len(result.risk_keywords) >= 3

    def test_high_two_categories(self):
        """Text matching keywords from exactly 2 categories → HIGH, confidence 0.95."""
        # account_access + billing_money only
        text = "account locked refund"
        result = self.clf.assess_risk_level(text)
        assert result.level == RiskLevel.HIGH
        assert result.confidence == 0.95

    def test_high_one_category(self):
        """Text matching keywords from exactly 1 category → HIGH, confidence 0.8."""
        # billing_money only
        text = "I need a refund for the overcharged invoice"
        result = self.clf.assess_risk_level(text)
        assert result.level == RiskLevel.HIGH
        assert result.confidence == 0.8

    def test_low_no_keywords(self):
        """Text with no risk keywords → LOW, confidence 0.9."""
        result = self.clf.assess_risk_level("I would like to know more about the product features")
        assert result.level == RiskLevel.LOW
        assert result.confidence == 0.9
        assert result.risk_keywords == []

    def test_logging_level_critical_logs_warning(self, caplog):
        """CRITICAL risk assessment logs at WARNING level."""
        text = "account locked refund fraud"
        with caplog.at_level(logging.WARNING, logger="classifier"):
            result = self.clf.assess_risk_level(text)
        assert result.level == RiskLevel.CRITICAL
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1

    def test_confidence_values_match_spec(self):
        """Confidence values match the spec exactly for each risk level."""
        # CRITICAL
        text_critical = "account locked refund fraud"
        r = self.clf.assess_risk_level(text_critical)
        assert r.level == RiskLevel.CRITICAL and r.confidence == 1.0

        # HIGH score=2
        text_high2 = "account locked refund"
        r = self.clf.assess_risk_level(text_high2)
        assert r.level == RiskLevel.HIGH and r.confidence == 0.95

        # HIGH score=1
        text_high1 = "refund please"
        r = self.clf.assess_risk_level(text_high1)
        assert r.level == RiskLevel.HIGH and r.confidence == 0.8

        # LOW
        text_low = "general inquiry about features"
        r = self.clf.assess_risk_level(text_low)
        assert r.level == RiskLevel.LOW and r.confidence == 0.9


# ---------------------------------------------------------------------------
# TestClassificationResult — 3 tests
# ---------------------------------------------------------------------------

class TestClassificationResult:
    """Tests for ClassificationResult serialisation and full pipeline."""

    def setup_method(self):
        self.clf = Classifier()

    def _make_result(self) -> ClassificationResult:
        ticket = make_ticket(subject="billing issue", issue="I need a refund for the overcharged amount")
        return self.clf.classify_ticket(ticket)

    def test_to_dict_structure(self):
        """to_dict() returns a dict with all required top-level and nested keys."""
        result = self._make_result()
        d = result.to_dict()

        # Top-level keys
        assert set(d.keys()) == {"request_type", "product_area", "risk", "detected_domain", "raw_text", "cleaned_text"}

        # Nested request_type keys
        assert set(d["request_type"].keys()) == {"type", "confidence", "matched_patterns"}

        # Nested product_area keys
        assert set(d["product_area"].keys()) == {"area", "domain", "confidence", "matched_keywords"}

        # Nested risk keys
        assert set(d["risk"].keys()) == {"level", "confidence", "risk_keywords", "reason"}

        # Values are plain Python types (not enum instances)
        assert isinstance(d["detected_domain"], str)
        assert isinstance(d["request_type"]["type"], str)
        assert isinstance(d["product_area"]["domain"], str)
        assert isinstance(d["risk"]["level"], str)

    def test_repr_returns_non_empty_string(self):
        """__repr__ returns a non-empty string."""
        result = self._make_result()
        r = repr(result)
        assert isinstance(r, str)
        assert len(r) > 0

    def test_full_pipeline_classify_ticket(self):
        """classify_ticket returns a ClassificationResult with all non-None fields."""
        ticket = make_ticket(subject="API error", issue="The claude api is crashing with an error")
        result = self.clf.classify_ticket(ticket)

        assert isinstance(result, ClassificationResult)
        assert result.request_type is not None
        assert result.product_area is not None
        assert result.risk is not None
        assert result.detected_domain is not None
        assert result.raw_text is not None
        assert result.cleaned_text is not None

        # Enum types are correct
        assert isinstance(result.request_type.type, RequestType)
        assert isinstance(result.risk.level, RiskLevel)
        assert isinstance(result.detected_domain, Domain)


# ---------------------------------------------------------------------------
# TestBatchClassification — 3 tests
# ---------------------------------------------------------------------------

class TestBatchClassification:
    """Tests for Classifier.classify_batch and get_classification_summary."""

    def setup_method(self):
        self.clf = Classifier()

    def test_empty_batch_returns_empty_list(self):
        """classify_batch([]) returns [] without raising."""
        results = self.clf.classify_batch([])
        assert results == []

    def test_single_ticket_batch(self):
        """classify_batch with one ticket returns a list of length 1."""
        ticket = make_ticket(subject="test", issue="There is a bug in the system")
        results = self.clf.classify_batch([ticket])
        assert len(results) == 1
        assert isinstance(results[0], ClassificationResult)

    def test_multiple_tickets_correct_count_and_summary(self):
        """Multiple tickets: result count matches input, summary totals are correct."""
        tickets = [
            make_ticket(subject="bug report", issue="crash error bug", ticket_id=1),
            make_ticket(subject="feature", issue="please add dark mode feature request", ticket_id=2),
            make_ticket(subject="visa issue", issue="my visa card payment failed", ticket_id=3),
        ]
        results = self.clf.classify_batch(tickets)
        assert len(results) == 3

        summary = self.clf.get_classification_summary()
        assert summary["total_classified"] == 3
        # Sum of all request type counts equals total
        assert sum(summary["by_request_type"].values()) == 3
        # Sum of all risk level counts equals total
        assert sum(summary["by_risk_level"].values()) == 3
        # Sum of all domain counts equals total
        assert sum(summary["by_domain"].values()) == 3
        # high_risk_count is non-negative
        assert summary["high_risk_count"] >= 0


# ---------------------------------------------------------------------------
# TestUtilityFunctions — 3 tests
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    """Tests for module-level utility functions."""

    def test_infer_company_from_text(self):
        """infer_company_from_text returns correct display names and None."""
        assert infer_company_from_text("I have an issue with my hackerrank assessment") == "HackerRank"
        assert infer_company_from_text("The claude api is not responding") == "Claude"
        assert infer_company_from_text("My visa card was charged twice") == "Visa"
        assert infer_company_from_text("completely unrelated text with no keywords") is None

    def test_extract_keywords(self):
        """extract_keywords returns only categories with matches, omits empty ones."""
        keyword_dict = {
            "greetings": ["hello", "howdy"],
            "farewells": ["goodbye", "farewell"],
            "numbers": ["alpha", "beta", "gamma"],
        }
        text = "hello there, goodbye and beta"
        result = extract_keywords(text, keyword_dict)

        # "greetings", "farewells", and "numbers" should all have matches
        assert "greetings" in result
        assert "hello" in result["greetings"]
        assert "farewells" in result
        assert "goodbye" in result["farewells"]
        assert "numbers" in result
        assert "beta" in result["numbers"]

        # Test that categories with no matches are omitted
        text_no_match = "completely unrelated words xyz"
        result_empty = extract_keywords(text_no_match, keyword_dict)
        assert result_empty == {}

    def test_score_text_length_confidence(self):
        """score_text_length_confidence returns 0.7, 0.85, 1.0 for the three length bands."""
        # Short text (< 50 chars)
        short_text = "short"
        assert score_text_length_confidence(short_text) == 0.7

        # Medium text (50–199 chars)
        medium_text = "a" * 50
        assert score_text_length_confidence(medium_text) == 0.85

        medium_text_199 = "a" * 199
        assert score_text_length_confidence(medium_text_199) == 0.85

        # Long text (>= 200 chars)
        long_text = "a" * 200
        assert score_text_length_confidence(long_text) == 1.0

        long_text_more = "a" * 500
        assert score_text_length_confidence(long_text_more) == 1.0
