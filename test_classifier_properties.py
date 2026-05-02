"""
test_classifier_properties.py — Property-based tests for classifier.py

Uses the hypothesis library to verify universal invariants of the classifier
module across a wide range of generated inputs.

Properties tested:
  Property 1: Classification result validity
  Property 2: Confidence bounds
  Property 3: Risk detection consistency
  Property 4: Product area validity
  Property 5: Classification consistency (determinism)
  Property 6: Batch consistency

**Validates: Requirements 15.1–15.8**
"""

import math

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import config
from config import (
    RISK_ESCALATION_KEYWORDS,
    PRODUCT_AREA_MAPPINGS,
    SUPPORTED_DOMAINS,
)
from data_loader import TicketRecord
from classifier import (
    Classifier,
    RequestType,
    RiskLevel,
    Domain,
    ClassificationResult,
)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Strategy: positive integer IDs in a reasonable range
positive_ids = st.integers(min_value=1, max_value=10_000)

# Strategy: non-empty issue strings (at least one non-whitespace character)
non_empty_issues = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())

# Strategy: subject text (may be empty)
subject_text = st.text(min_size=0, max_size=200)

# Strategy: optional company — None or one of the supported domains
optional_company = st.one_of(
    st.none(),
    st.sampled_from(SUPPORTED_DOMAINS),
)


@st.composite
def valid_ticket(draw):
    """Composite strategy that generates a valid TicketRecord."""
    ticket_id = draw(positive_ids)
    issue = draw(non_empty_issues)
    subject = draw(subject_text)
    company = draw(optional_company)
    return TicketRecord(id=ticket_id, issue=issue, subject=subject, company=company)


# ---------------------------------------------------------------------------
# Property 1: Classification result validity
# **Validates: Requirements 15.1, 15.2**
# ---------------------------------------------------------------------------


@given(ticket=valid_ticket())
@settings(max_examples=50)
def test_property_1_classification_result_validity(ticket):
    """
    Property 1: Classification result validity

    Every ClassificationResult produced by classify_ticket has:
    - Non-None fields: request_type, product_area, risk, detected_domain,
      raw_text, cleaned_text
    - Valid enum values: request_type.type is a RequestType,
      risk.level is a RiskLevel, detected_domain is a Domain

    **Validates: Requirements 15.1, 15.2**
    """
    clf = Classifier()
    result = clf.classify_ticket(ticket)

    # All top-level fields must be non-None
    assert result.request_type is not None, "request_type must not be None"
    assert result.product_area is not None, "product_area must not be None"
    assert result.risk is not None, "risk must not be None"
    assert result.detected_domain is not None, "detected_domain must not be None"
    assert result.raw_text is not None, "raw_text must not be None"
    assert result.cleaned_text is not None, "cleaned_text must not be None"

    # Enum values must be valid members of their respective enums
    assert isinstance(result.request_type.type, RequestType), (
        f"request_type.type must be a RequestType, got {type(result.request_type.type)}"
    )
    assert isinstance(result.risk.level, RiskLevel), (
        f"risk.level must be a RiskLevel, got {type(result.risk.level)}"
    )
    assert isinstance(result.detected_domain, Domain), (
        f"detected_domain must be a Domain, got {type(result.detected_domain)}"
    )

    # request_type.type must be one of the known RequestType members
    assert result.request_type.type in list(RequestType), (
        f"request_type.type {result.request_type.type!r} is not a valid RequestType"
    )

    # risk.level must be one of the known RiskLevel members
    assert result.risk.level in list(RiskLevel), (
        f"risk.level {result.risk.level!r} is not a valid RiskLevel"
    )

    # detected_domain must be one of the known Domain members
    assert result.detected_domain in list(Domain), (
        f"detected_domain {result.detected_domain!r} is not a valid Domain"
    )


# ---------------------------------------------------------------------------
# Property 2: Confidence bounds
# **Validates: Requirements 15.1, 15.3**
# ---------------------------------------------------------------------------


@given(ticket=valid_ticket())
@settings(max_examples=50)
def test_property_2_confidence_bounds(ticket):
    """
    Property 2: Confidence bounds

    All confidence values in a ClassificationResult are in [0.0, 1.0]
    with no NaN or infinity:
    - result.request_type.confidence
    - result.product_area.confidence
    - result.risk.confidence

    **Validates: Requirements 15.1, 15.3**
    """
    clf = Classifier()
    result = clf.classify_ticket(ticket)

    confidences = {
        "request_type.confidence": result.request_type.confidence,
        "product_area.confidence": result.product_area.confidence,
        "risk.confidence": result.risk.confidence,
    }

    for field_name, value in confidences.items():
        # Must be a finite number (no NaN or infinity)
        assert not math.isnan(value), (
            f"{field_name} is NaN"
        )
        assert not math.isinf(value), (
            f"{field_name} is infinite: {value}"
        )
        # Must be within [0.0, 1.0]
        assert 0.0 <= value <= 1.0, (
            f"{field_name} = {value} is outside [0.0, 1.0]"
        )


# ---------------------------------------------------------------------------
# Property 3: Risk detection consistency
# **Validates: Requirements 15.1, 15.4**
# ---------------------------------------------------------------------------

# Pre-compute the list of risk categories and their keywords once
_RISK_CATEGORIES = list(RISK_ESCALATION_KEYWORDS.keys())
_RISK_CATEGORY_KEYWORDS = {
    cat: list(kws) for cat, kws in RISK_ESCALATION_KEYWORDS.items()
}


@given(
    # Pick 3 distinct category indices
    category_indices=st.lists(
        st.integers(min_value=0, max_value=len(_RISK_CATEGORIES) - 1),
        min_size=3,
        max_size=3,
        unique=True,
    ),
    # For each category, pick a keyword index (sampled per category below)
    keyword_indices=st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=3,
        max_size=3,
    ),
    # Extra surrounding text (may be empty)
    extra_text=st.text(min_size=0, max_size=100),
)
@settings(max_examples=50)
def test_property_3_risk_detection_consistency(
    category_indices, keyword_indices, extra_text
):
    """
    Property 3: Risk detection consistency

    Tickets containing keywords from at least 3 distinct RISK_ESCALATION_KEYWORDS
    categories always produce CRITICAL or HIGH risk level.

    **Validates: Requirements 15.1, 15.4**
    """
    # Build text by picking one keyword from each of 3 different categories
    selected_keywords = []
    for i, cat_idx in enumerate(category_indices):
        category = _RISK_CATEGORIES[cat_idx]
        kws = _RISK_CATEGORY_KEYWORDS[category]
        kw_idx = keyword_indices[i] % len(kws)
        selected_keywords.append(kws[kw_idx])

    # Construct the ticket text with the 3 risk keywords embedded
    risk_text = " ".join(selected_keywords)
    full_issue = f"{extra_text} {risk_text}".strip() if extra_text.strip() else risk_text

    # Ensure the issue is non-empty (it always will be since risk_text is non-empty)
    assume(full_issue.strip())

    ticket = TicketRecord(id=1, issue=full_issue, subject="", company=None)
    clf = Classifier()
    result = clf.classify_ticket(ticket)

    assert result.risk.level in (RiskLevel.CRITICAL, RiskLevel.HIGH), (
        f"Expected CRITICAL or HIGH risk for text with 3 risk categories, "
        f"got {result.risk.level!r}. "
        f"Keywords used: {selected_keywords!r}. "
        f"Text: {full_issue!r}"
    )


# ---------------------------------------------------------------------------
# Property 4: Product area validity
# **Validates: Requirements 15.1, 15.5**
# ---------------------------------------------------------------------------


@given(ticket=valid_ticket())
@settings(max_examples=50)
def test_property_4_product_area_validity(ticket):
    """
    Property 4: Product area validity

    The returned area in ProductAreaResult is always:
    - A member of PRODUCT_AREA_MAPPINGS[domain.value] for known domains
      (HACKERRANK, CLAUDE, VISA)
    - "general" for Domain.UNKNOWN

    **Validates: Requirements 15.1, 15.5**
    """
    clf = Classifier()
    result = clf.classify_ticket(ticket)

    domain = result.detected_domain
    area = result.product_area.area

    if domain == Domain.UNKNOWN:
        assert area == "general", (
            f"Expected area='general' for Domain.UNKNOWN, got {area!r}"
        )
    else:
        valid_areas = PRODUCT_AREA_MAPPINGS[domain.value]
        assert area in valid_areas, (
            f"area={area!r} is not in PRODUCT_AREA_MAPPINGS[{domain.value!r}]={valid_areas!r}"
        )


# ---------------------------------------------------------------------------
# Property 5: Classification consistency (determinism)
# **Validates: Requirements 15.1, 15.6**
# ---------------------------------------------------------------------------


@given(ticket=valid_ticket())
@settings(max_examples=50)
def test_property_5_classification_consistency(ticket):
    """
    Property 5: Classification consistency (determinism)

    Classifying the same ticket twice always produces identical RequestType,
    Domain, RiskLevel, and area values.

    **Validates: Requirements 15.1, 15.6**
    """
    clf = Classifier()
    result1 = clf.classify_ticket(ticket)
    result2 = clf.classify_ticket(ticket)

    assert result1.request_type.type == result2.request_type.type, (
        f"RequestType differs between two classifications: "
        f"{result1.request_type.type!r} vs {result2.request_type.type!r}"
    )
    assert result1.detected_domain == result2.detected_domain, (
        f"Domain differs between two classifications: "
        f"{result1.detected_domain!r} vs {result2.detected_domain!r}"
    )
    assert result1.risk.level == result2.risk.level, (
        f"RiskLevel differs between two classifications: "
        f"{result1.risk.level!r} vs {result2.risk.level!r}"
    )
    assert result1.product_area.area == result2.product_area.area, (
        f"Product area differs between two classifications: "
        f"{result1.product_area.area!r} vs {result2.product_area.area!r}"
    )


# ---------------------------------------------------------------------------
# Property 6: Batch consistency
# **Validates: Requirements 15.1, 15.7**
# ---------------------------------------------------------------------------


@given(ticket=valid_ticket())
@settings(max_examples=50)
def test_property_6_batch_consistency(ticket):
    """
    Property 6: Batch consistency

    classify_batch([ticket]) produces the same RequestType, Domain, RiskLevel,
    and area as classify_ticket(ticket) for any single valid ticket.

    **Validates: Requirements 15.1, 15.7**
    """
    clf = Classifier()
    single_result = clf.classify_ticket(ticket)

    clf2 = Classifier()
    batch_results = clf2.classify_batch([ticket])

    assert len(batch_results) == 1, (
        f"classify_batch([ticket]) should return exactly 1 result, "
        f"got {len(batch_results)}"
    )

    batch_result = batch_results[0]

    assert single_result.request_type.type == batch_result.request_type.type, (
        f"RequestType differs: single={single_result.request_type.type!r}, "
        f"batch={batch_result.request_type.type!r}"
    )
    assert single_result.detected_domain == batch_result.detected_domain, (
        f"Domain differs: single={single_result.detected_domain!r}, "
        f"batch={batch_result.detected_domain!r}"
    )
    assert single_result.risk.level == batch_result.risk.level, (
        f"RiskLevel differs: single={single_result.risk.level!r}, "
        f"batch={batch_result.risk.level!r}"
    )
    assert single_result.product_area.area == batch_result.product_area.area, (
        f"Product area differs: single={single_result.product_area.area!r}, "
        f"batch={batch_result.product_area.area!r}"
    )
