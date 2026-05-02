"""
test_config_properties.py — Property-based tests for config.py

Uses the `hypothesis` library to verify universal properties of the
configuration data and helper functions defined in config.py.

Properties tested:
  Property 2: All keyword lists in RISK_ESCALATION_KEYWORDS are non-empty
  Property 3: Keyword detection is comprehensive (any keyword in a category is detected)
  Property 4: classify_request_type always returns a key in REQUEST_TYPE_PATTERNS
  Property 5: detect_product_area always returns a member of PRODUCT_AREA_MAPPINGS[domain]
  Property 6: Template formatting never raises on valid placeholder dicts
  Property 7: All pattern lists in REQUEST_TYPE_PATTERNS are non-empty
  Property 8: PRODUCT_AREA_MAPPINGS[domain] is a non-empty list for every domain
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import config


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Strategy: sample a valid category key from RISK_ESCALATION_KEYWORDS
risk_category_keys = st.sampled_from(list(config.RISK_ESCALATION_KEYWORDS.keys()))

# Strategy: sample a valid domain from SUPPORTED_DOMAINS
valid_domain = st.sampled_from(config.SUPPORTED_DOMAINS)

# Strategy: sample a valid request type key from REQUEST_TYPE_PATTERNS
request_type_keys = st.sampled_from(list(config.REQUEST_TYPE_PATTERNS.keys()))


# ---------------------------------------------------------------------------
# Property 2: All keyword lists are non-empty
# Validates: Requirements 2.1, 2.7
# ---------------------------------------------------------------------------

@given(category=risk_category_keys)
def test_property_2_all_keyword_lists_are_non_empty(category):
    """
    **Validates: Requirements 2.1, 2.7**

    For any category key in RISK_ESCALATION_KEYWORDS, the associated keyword
    list must contain at least one entry. An empty list would cause that
    category to silently never match any ticket.
    """
    keyword_list = config.RISK_ESCALATION_KEYWORDS[category]
    assert isinstance(keyword_list, list), (
        f"RISK_ESCALATION_KEYWORDS[{category!r}] must be a list, got {type(keyword_list)}"
    )
    assert len(keyword_list) > 0, (
        f"RISK_ESCALATION_KEYWORDS[{category!r}] must be non-empty"
    )


# ---------------------------------------------------------------------------
# Property 3: Keyword detection is comprehensive
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------

@given(category=risk_category_keys, prefix=st.text(), suffix=st.text())
@settings(max_examples=200)
def test_property_3_keyword_detection_is_comprehensive(category, prefix, suffix):
    """
    **Validates: Requirements 2.6**

    For any keyword k in RISK_ESCALATION_KEYWORDS[category] and for any ticket
    text that contains k (case-insensitively), a keyword scanner iterating over
    RISK_ESCALATION_KEYWORDS must detect `category` as a match.
    """
    keywords = config.RISK_ESCALATION_KEYWORDS[category]
    # Pick the first keyword from the category as the representative keyword
    keyword = keywords[0]

    # Build a ticket text that contains the keyword surrounded by arbitrary text
    ticket_text = prefix + keyword + suffix

    # Simulate the keyword scanner from the design's triage algorithm
    matched_categories = []
    for cat, kws in config.RISK_ESCALATION_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in ticket_text.lower():
                matched_categories.append(cat)
                break

    assert category in matched_categories, (
        f"Expected category {category!r} to be detected in ticket text "
        f"{ticket_text!r} (keyword: {keyword!r}), but matched: {matched_categories}"
    )


# ---------------------------------------------------------------------------
# Property 4: Request type classification always returns a valid key
# Validates: Requirements 3.5, 3.6
# ---------------------------------------------------------------------------

@given(ticket_text=st.text(min_size=1))
@settings(max_examples=300)
def test_property_4_classify_request_type_always_returns_valid_key(ticket_text):
    """
    **Validates: Requirements 3.5, 3.6**

    For any non-empty ticket text string, classify_request_type must return a
    value that is a key present in REQUEST_TYPE_PATTERNS. The function must
    never return None, an empty string, or a value outside the defined types.
    """
    result = config.classify_request_type(ticket_text)

    assert result is not None, "classify_request_type must not return None"
    assert isinstance(result, str), (
        f"classify_request_type must return a str, got {type(result)}"
    )
    assert result in config.REQUEST_TYPE_PATTERNS, (
        f"classify_request_type({ticket_text!r}) returned {result!r}, "
        f"which is not a key in REQUEST_TYPE_PATTERNS: "
        f"{list(config.REQUEST_TYPE_PATTERNS.keys())}"
    )


# ---------------------------------------------------------------------------
# Property 5: Product area detection always returns a valid area
# Validates: Requirements 4.5, 4.6
# ---------------------------------------------------------------------------

@given(ticket_text=st.text(min_size=1), domain=valid_domain)
@settings(max_examples=300)
def test_property_5_detect_product_area_always_returns_valid_area(ticket_text, domain):
    """
    **Validates: Requirements 4.5, 4.6**

    For any non-empty ticket text and any domain in SUPPORTED_DOMAINS,
    detect_product_area must return a string that is a member of
    PRODUCT_AREA_MAPPINGS[domain]. The function must never return None or
    an empty string.
    """
    result = config.detect_product_area(ticket_text, domain)

    assert result is not None, "detect_product_area must not return None"
    assert isinstance(result, str), (
        f"detect_product_area must return a str, got {type(result)}"
    )
    assert len(result) > 0, "detect_product_area must not return an empty string"
    assert result in config.PRODUCT_AREA_MAPPINGS[domain], (
        f"detect_product_area({ticket_text!r}, {domain!r}) returned {result!r}, "
        f"which is not in PRODUCT_AREA_MAPPINGS[{domain!r}]: "
        f"{config.PRODUCT_AREA_MAPPINGS[domain]}"
    )


# ---------------------------------------------------------------------------
# Property 6: Template formatting never raises on valid placeholders
# Validates: Requirements 6.4, 6.5
# ---------------------------------------------------------------------------

# Strategy: generate valid placeholder dictionaries with all required keys
valid_placeholder_dict = st.fixed_dictionaries({
    "ticket_id": st.text(min_size=1),
    "domain": st.text(min_size=1),
    "agent_name": st.text(min_size=1),
})

@given(placeholders=valid_placeholder_dict)
@settings(max_examples=200)
def test_property_6_template_formatting_never_raises(placeholders):
    """
    **Validates: Requirements 6.4, 6.5**

    For any template key in TEMPLATE_RESPONSES and any dictionary of placeholder
    values that includes all documented required keys, calling .format(**placeholders)
    on the template string must complete without raising a KeyError or any other
    exception.

    The escalation template requires: {ticket_id}, {domain}, {agent_name}
    The out_of_scope template requires: {ticket_id}, {domain}
    Both sets of keys are covered by the generated placeholder dict.
    """
    for template_key, template_str in config.TEMPLATE_RESPONSES.items():
        try:
            result = template_str.format(**placeholders)
            assert isinstance(result, str), (
                f"Formatting TEMPLATE_RESPONSES[{template_key!r}] must return a str"
            )
        except KeyError as exc:
            pytest.fail(
                f"Formatting TEMPLATE_RESPONSES[{template_key!r}] raised KeyError {exc} "
                f"with placeholders {placeholders!r}. "
                "All required placeholder keys must be present."
            )


# ---------------------------------------------------------------------------
# Property 7: All pattern lists are non-empty
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------

@given(request_type=request_type_keys)
def test_property_7_all_pattern_lists_are_non_empty(request_type):
    """
    **Validates: Requirements 3.1**

    For any request type key in REQUEST_TYPE_PATTERNS, the associated list of
    indicator phrases must contain at least one entry. An empty list would mean
    that request type can never be classified from ticket text.
    """
    pattern_list = config.REQUEST_TYPE_PATTERNS[request_type]
    assert isinstance(pattern_list, list), (
        f"REQUEST_TYPE_PATTERNS[{request_type!r}] must be a list, got {type(pattern_list)}"
    )
    assert len(pattern_list) > 0, (
        f"REQUEST_TYPE_PATTERNS[{request_type!r}] must be non-empty"
    )


# ---------------------------------------------------------------------------
# Property 8: All product area lists are non-empty
# Validates: Requirements 4.1
# ---------------------------------------------------------------------------

@given(domain=valid_domain)
def test_property_8_all_product_area_lists_are_non_empty(domain):
    """
    **Validates: Requirements 4.1**

    For any domain in SUPPORTED_DOMAINS, PRODUCT_AREA_MAPPINGS[domain] must
    return a non-empty list, ensuring every domain has at least one valid
    routing destination.
    """
    area_list = config.PRODUCT_AREA_MAPPINGS[domain]
    assert isinstance(area_list, list), (
        f"PRODUCT_AREA_MAPPINGS[{domain!r}] must be a list, got {type(area_list)}"
    )
    assert len(area_list) > 0, (
        f"PRODUCT_AREA_MAPPINGS[{domain!r}] must be non-empty"
    )
