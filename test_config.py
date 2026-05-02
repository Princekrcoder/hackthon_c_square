"""
test_config.py — Unit tests for config.py

Tests cover all six configuration sections plus the classify_request_type
helper function defined in config.py.
"""

import pytest
import config


# ---------------------------------------------------------------------------
# 8.2 / 8.3  Domain Constants and SUPPORTED_DOMAINS
# ---------------------------------------------------------------------------

class TestDomainConstants:
    """Tests for DOMAIN_* constants and SUPPORTED_DOMAINS."""

    def test_domain_hackerrank_is_non_empty_string(self):
        """DOMAIN_HACKERRANK must be a non-empty string."""
        assert isinstance(config.DOMAIN_HACKERRANK, str)
        assert len(config.DOMAIN_HACKERRANK) > 0

    def test_domain_claude_is_non_empty_string(self):
        """DOMAIN_CLAUDE must be a non-empty string."""
        assert isinstance(config.DOMAIN_CLAUDE, str)
        assert len(config.DOMAIN_CLAUDE) > 0

    def test_domain_visa_is_non_empty_string(self):
        """DOMAIN_VISA must be a non-empty string."""
        assert isinstance(config.DOMAIN_VISA, str)
        assert len(config.DOMAIN_VISA) > 0

    def test_domain_hackerrank_in_supported_domains(self):
        """DOMAIN_HACKERRANK must be a member of SUPPORTED_DOMAINS."""
        assert config.DOMAIN_HACKERRANK in config.SUPPORTED_DOMAINS

    def test_domain_claude_in_supported_domains(self):
        """DOMAIN_CLAUDE must be a member of SUPPORTED_DOMAINS."""
        assert config.DOMAIN_CLAUDE in config.SUPPORTED_DOMAINS

    def test_domain_visa_in_supported_domains(self):
        """DOMAIN_VISA must be a member of SUPPORTED_DOMAINS."""
        assert config.DOMAIN_VISA in config.SUPPORTED_DOMAINS

    def test_supported_domains_contains_exactly_three_constants(self):
        """SUPPORTED_DOMAINS must contain exactly the three domain constants."""
        assert len(config.SUPPORTED_DOMAINS) == 3
        assert set(config.SUPPORTED_DOMAINS) == {
            config.DOMAIN_HACKERRANK,
            config.DOMAIN_CLAUDE,
            config.DOMAIN_VISA,
        }


# ---------------------------------------------------------------------------
# 8.4  RISK_ESCALATION_KEYWORDS
# ---------------------------------------------------------------------------

class TestRiskEscalationKeywords:
    """Tests for RISK_ESCALATION_KEYWORDS structure."""

    def test_has_exactly_four_keys(self):
        """RISK_ESCALATION_KEYWORDS must have exactly four keys."""
        assert len(config.RISK_ESCALATION_KEYWORDS) == 4

    def test_expected_keys_present(self):
        """RISK_ESCALATION_KEYWORDS must contain the four expected category keys."""
        expected_keys = {"account_access", "billing_money", "security", "admin"}
        assert set(config.RISK_ESCALATION_KEYWORDS.keys()) == expected_keys


# ---------------------------------------------------------------------------
# 8.5  REQUEST_TYPE_PATTERNS
# ---------------------------------------------------------------------------

class TestRequestTypePatterns:
    """Tests for REQUEST_TYPE_PATTERNS structure."""

    def test_has_exactly_three_keys(self):
        """REQUEST_TYPE_PATTERNS must have exactly three keys."""
        assert len(config.REQUEST_TYPE_PATTERNS) == 3

    def test_expected_keys_present(self):
        """REQUEST_TYPE_PATTERNS must contain the three expected request type keys."""
        expected_keys = {"bug", "feature_request", "product_issue"}
        assert set(config.REQUEST_TYPE_PATTERNS.keys()) == expected_keys


# ---------------------------------------------------------------------------
# 8.6  PRODUCT_AREA_MAPPINGS
# ---------------------------------------------------------------------------

class TestProductAreaMappings:
    """Tests for PRODUCT_AREA_MAPPINGS structure."""

    def test_has_exactly_three_keys(self):
        """PRODUCT_AREA_MAPPINGS must have exactly three keys."""
        assert len(config.PRODUCT_AREA_MAPPINGS) == 3

    def test_keys_match_supported_domains(self):
        """PRODUCT_AREA_MAPPINGS keys must exactly match SUPPORTED_DOMAINS."""
        assert set(config.PRODUCT_AREA_MAPPINGS.keys()) == set(config.SUPPORTED_DOMAINS)


# ---------------------------------------------------------------------------
# 8.7 / 8.8  Confidence Thresholds
# ---------------------------------------------------------------------------

class TestConfidenceThresholds:
    """Tests for CONFIDENCE_MIN and CONFIDENCE_HIGH values."""

    def test_confidence_min_equals_0_6(self):
        """CONFIDENCE_MIN must equal 0.6."""
        assert config.CONFIDENCE_MIN == 0.6

    def test_confidence_high_equals_0_8(self):
        """CONFIDENCE_HIGH must equal 0.8."""
        assert config.CONFIDENCE_HIGH == 0.8

    def test_confidence_min_less_than_confidence_high(self):
        """CONFIDENCE_MIN must be strictly less than CONFIDENCE_HIGH."""
        assert config.CONFIDENCE_MIN < config.CONFIDENCE_HIGH

    def test_confidence_min_within_valid_range(self):
        """CONFIDENCE_MIN must be within [0.0, 1.0]."""
        assert 0.0 <= config.CONFIDENCE_MIN <= 1.0

    def test_confidence_high_within_valid_range(self):
        """CONFIDENCE_HIGH must be within [0.0, 1.0]."""
        assert 0.0 <= config.CONFIDENCE_HIGH <= 1.0


# ---------------------------------------------------------------------------
# 8.9 / 8.10  Template Responses
# ---------------------------------------------------------------------------

class TestTemplateResponses:
    """Tests for TEMPLATE_RESPONSES content and formatting."""

    def test_escalation_key_present(self):
        """TEMPLATE_RESPONSES must contain the 'escalation' key."""
        assert "escalation" in config.TEMPLATE_RESPONSES

    def test_out_of_scope_key_present(self):
        """TEMPLATE_RESPONSES must contain the 'out_of_scope' key."""
        assert "out_of_scope" in config.TEMPLATE_RESPONSES

    def test_escalation_value_is_non_empty_string(self):
        """TEMPLATE_RESPONSES['escalation'] must be a non-empty string."""
        value = config.TEMPLATE_RESPONSES["escalation"]
        assert isinstance(value, str)
        assert len(value) > 0

    def test_out_of_scope_value_is_non_empty_string(self):
        """TEMPLATE_RESPONSES['out_of_scope'] must be a non-empty string."""
        value = config.TEMPLATE_RESPONSES["out_of_scope"]
        assert isinstance(value, str)
        assert len(value) > 0

    def test_escalation_template_formats_without_exception(self):
        """Formatting the escalation template with all required placeholders must not raise."""
        template = config.TEMPLATE_RESPONSES["escalation"]
        # Required placeholders: {ticket_id}, {domain}, {agent_name}
        result = template.format(
            ticket_id="TKT-0001",
            domain="HackerRank",
            agent_name="Support Team",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_out_of_scope_template_formats_without_exception(self):
        """Formatting the out_of_scope template with all required placeholders must not raise."""
        template = config.TEMPLATE_RESPONSES["out_of_scope"]
        # Required placeholders: {ticket_id}, {domain}
        result = template.format(
            ticket_id="TKT-0002",
            domain="Visa",
        )
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# 8.11  classify_request_type — default fallback
# ---------------------------------------------------------------------------

class TestClassifyRequestType:
    """Tests for the classify_request_type helper function."""

    def test_returns_product_issue_when_no_patterns_match(self):
        """classify_request_type must return 'product_issue' for text with no matching patterns."""
        # A ticket text that contains none of the indicator phrases from any
        # REQUEST_TYPE_PATTERNS list — purely neutral/generic text.
        neutral_text = "Hello, I have a question about my account."
        result = config.classify_request_type(neutral_text)
        assert result == "product_issue"

    def test_returns_valid_key_for_any_input(self):
        """classify_request_type must always return a key present in REQUEST_TYPE_PATTERNS."""
        test_inputs = [
            "The feature is not working at all",
            "I would like a new dashboard",
            "There is an issue with my billing",
            "xyz abc 123",  # no patterns match → default
        ]
        for text in test_inputs:
            result = config.classify_request_type(text)
            assert result in config.REQUEST_TYPE_PATTERNS, (
                f"classify_request_type({text!r}) returned {result!r}, "
                f"which is not a key in REQUEST_TYPE_PATTERNS"
            )
