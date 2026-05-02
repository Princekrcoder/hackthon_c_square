"""
config.py — Support Ticket Triage Configuration Module

This module provides all static configuration data for the support ticket triage
system. It defines domain constants, risk escalation keywords, request-type
patterns, product-area mappings, confidence thresholds, and template responses
in a single importable file.

Any triage engine can import this module to classify, escalate, or respond to
incoming support tickets across three supported domains: HackerRank, Claude,
and Visa.

Design principles:
- All configuration is defined at module level (loaded once at import time).
- No third-party runtime dependencies — only Python built-in types and syntax.
- No side effects on import beyond loading the configuration data.
- Startup assertions validate critical invariants at import time (fail fast).

Usage:
    import config

    # Access domain constants
    print(config.DOMAIN_HACKERRANK)   # "hackerrank"
    print(config.SUPPORTED_DOMAINS)   # ["hackerrank", "claude", "visa"]

    # Use confidence thresholds
    if score >= config.CONFIDENCE_HIGH:
        ...  # route directly
    elif score >= config.CONFIDENCE_MIN:
        ...  # escalate for review
    else:
        ...  # out of scope
"""

# ---------------------------------------------------------------------------
# Section 1: Domain Constants
# ---------------------------------------------------------------------------
# Canonical string identifiers for each supported service domain.
# Use these constants instead of hardcoding domain strings throughout the
# codebase to prevent typo-related bugs.
# Type: str (one of "hackerrank", "claude", "visa")

DOMAIN_HACKERRANK = "hackerrank"  # Identifier for the HackerRank platform domain
DOMAIN_CLAUDE = "claude"          # Identifier for the Claude (Anthropic) platform domain
DOMAIN_VISA = "visa"              # Identifier for the Visa financial services domain

# Complete list of all supported domains; use `domain in SUPPORTED_DOMAINS`
# to validate that an incoming ticket belongs to a recognised service.
SUPPORTED_DOMAINS = [DOMAIN_HACKERRANK, DOMAIN_CLAUDE, DOMAIN_VISA]


# ---------------------------------------------------------------------------
# Section 2: Risk Escalation Keywords
# ---------------------------------------------------------------------------
# Maps each risk category to a list of trigger keywords that indicate a ticket
# requires escalation. Supports case-insensitive substring matching.
# Type: dict[str, list[str]]
# Keys: "account_access", "billing_money", "security", "admin"

RISK_ESCALATION_KEYWORDS: dict = {
    # account_access — Standard escalation priority.
    # Triggered when a user reports being locked out of or unable to reach
    # their account. These tickets need prompt attention to restore access.
    "account_access": [
        "locked",
        "cannot access",
        "lost access",
        "account disabled",
        "login failed",
        "can't log in",
        "unable to login",
        "account locked",
    ],

    # billing_money — Priority review escalation.
    # Triggered when a ticket involves financial transactions, charges, or
    # disputes. These tickets carry potential financial liability and should
    # be reviewed by a billing specialist before resolution.
    "billing_money": [
        "refund",
        "charge",
        "payment",
        "dispute",
        "overcharged",
        "invoice",
        "billing",
        "charged twice",
        "wrong amount",
    ],

    # security — Immediate escalation priority.
    # Triggered when a ticket indicates a potential security incident such as
    # account compromise, fraud, or unauthorized access. These tickets bypass
    # normal confidence thresholds and require immediate human review.
    "security": [
        "fraud",
        "hacked",
        "stolen",
        "compromised",
        "unauthorized",
        "breach",
        "phishing",
        "suspicious activity",
        "identity theft",
    ],

    # admin — Immediate escalation priority.
    # Triggered when a ticket requests special administrative actions that
    # fall outside standard support workflows. These tickets must be reviewed
    # by an admin before any action is taken to prevent policy violations.
    "admin": [
        "admin override",
        "special permission",
        "manual intervention",
        "bypass",
        "escalate to admin",
        "admin access",
        "override policy",
    ],
}

# Startup assertion: ensure no risk category has an empty keyword list.
# An empty list would cause that category to silently never match any ticket,
# creating a gap in escalation coverage that would be hard to detect at runtime.
assert all(v for v in RISK_ESCALATION_KEYWORDS.values()), (
    "RISK_ESCALATION_KEYWORDS contains one or more empty keyword lists. "
    "Every risk category must have at least one trigger keyword."
)


# ---------------------------------------------------------------------------
# Section 3: Request Type Patterns
# ---------------------------------------------------------------------------
# Maps each request type label to a list of indicator phrases used to classify
# the nature of a support ticket. Patterns are domain-agnostic and apply
# across all three supported domains.
# Type: dict[str, list[str]]
# Keys: "bug", "feature_request", "product_issue"

REQUEST_TYPE_PATTERNS: dict = {
    # bug — Indicator phrases that signal a defect or malfunction.
    # Domain-agnostic: these phrases apply equally to HackerRank, Claude,
    # and Visa tickets. A ticket matching these patterns likely describes
    # something that used to work (or should work) but currently does not.
    "bug": [
        "not working",       # generic malfunction report
        "broken",            # component or feature is broken
        "error",             # an error message or error state was encountered
        "crash",             # application or service crashed
        "bug",               # user explicitly labels it a bug
        "fails",             # a process or action fails to complete
        "doesn't work",      # colloquial malfunction report
        "stopped working",   # regression — previously functional, now broken
        "issue",             # general problem indicator (overlaps with product_issue)
        "exception",         # technical error / exception thrown
    ],

    # feature_request — Indicator phrases that signal a request for new
    # functionality or an enhancement to existing behaviour.
    # Domain-agnostic: users across all domains use these phrases when asking
    # for something that does not yet exist in the product.
    "feature_request": [
        "would like",        # polite request phrasing
        "please add",        # explicit addition request
        "feature request",   # user explicitly labels it a feature request
        "enhancement",       # improvement to existing functionality
        "suggestion",        # user is suggesting a new capability
        "could you add",     # question-form addition request
        "can you add",       # alternative question-form addition request
        "wish there was",    # desire for a missing feature
        "it would be great", # positive framing of a new feature idea
        "add support for",   # request to extend support to a new case
    ],

    # product_issue — Indicator phrases that signal a general product concern
    # that does not clearly fit the "bug" or "feature_request" categories.
    # Domain-agnostic: these phrases describe confusion, unexpected behaviour,
    # or dissatisfaction without necessarily pointing to a defect or new feature.
    # This type also serves as the default fallback when no patterns match.
    "product_issue": [
        "issue with",            # general issue with a specific area
        "problem",               # general problem statement
        "unexpected behavior",   # behaviour differs from expectation
        "not as expected",       # outcome does not match expectation
        "confused about",        # user is confused by product behaviour
        "doesn't make sense",    # product behaviour is unclear or illogical
        "why does",              # question about unexpected behaviour
        "how come",              # informal question about unexpected behaviour
        "seems wrong",           # user suspects something is incorrect
        "not sure why",          # user is uncertain about observed behaviour
    ],
}


# ---------------------------------------------------------------------------
# Section 4: Product Area Mappings
# ---------------------------------------------------------------------------
# Maps each domain to its list of recognized product areas, enabling accurate
# routing to the correct team. The first area in each list serves as the
# default fallback when no keyword match is found in the ticket text.
# Type: dict[str, list[str]]
# Keys: "hackerrank", "claude", "visa"

PRODUCT_AREA_MAPPINGS: dict = {
    # hackerrank — Product areas for the HackerRank technical assessment platform.
    # First area ("assessments") is the default fallback when no keyword matches.
    "hackerrank": [
        "assessments",       # default fallback: online coding assessments and tests
        "coding_challenges", # individual coding challenge problems and submissions
        "billing",           # subscription plans, invoices, and payment issues
        "account",           # user account settings, profiles, and access
        "integrations",      # ATS and third-party system integrations
        "reporting",         # analytics dashboards and candidate reports
    ],

    # claude — Product areas for the Claude (Anthropic) AI platform.
    # First area ("api") is the default fallback when no keyword matches.
    "claude": [
        "api",              # default fallback: API access, keys, and endpoints
        "model_behavior",   # model outputs, accuracy, and response quality
        "billing",          # usage-based billing, invoices, and payment issues
        "account",          # account settings, team management, and access
        "rate_limits",      # request rate limits and quota management
        "context_window",   # context length, token limits, and memory
    ],

    # visa — Product areas for Visa financial services.
    # First area ("transactions") is the default fallback when no keyword matches.
    "visa": [
        "transactions",  # default fallback: payment transactions and history
        "disputes",      # transaction disputes and chargeback requests
        "account",       # cardholder account settings and management
        "fraud",         # fraud detection, alerts, and prevention
        "cards",         # physical and virtual card issuance and management
        "payments",      # payment processing, methods, and failures
    ],
}


# ---------------------------------------------------------------------------
# Section 5: Confidence Thresholds
# ---------------------------------------------------------------------------
# Numeric thresholds that govern triage decision boundaries:
#   score >= CONFIDENCE_HIGH              → route directly (high confidence):
#       The classifier is confident enough to classify the ticket and route it
#       to the appropriate team with a request type and product area assigned.
#   CONFIDENCE_MIN <= score < CONFIDENCE_HIGH → escalate for human review (medium confidence):
#       The classifier has some signal but not enough certainty; a human agent
#       should review the ticket before a final routing decision is made.
#   score < CONFIDENCE_MIN                → out-of-scope response (low confidence):
#       The classifier cannot reliably classify the ticket; respond with the
#       out-of-scope template to inform the submitter and avoid misrouting.
# Type: float

CONFIDENCE_MIN: float = 0.6   # Minimum confidence to act on a classification (escalate branch)
CONFIDENCE_HIGH: float = 0.8  # High confidence threshold for direct routing (route branch)

# Startup assertion: validate that the threshold values are internally consistent
# and within the valid confidence score range [0.0, 1.0].
# This fails fast at import time if the constants are ever accidentally changed
# to invalid values (e.g., CONFIDENCE_MIN >= CONFIDENCE_HIGH, or values outside [0, 1]).
assert 0.0 <= CONFIDENCE_MIN < CONFIDENCE_HIGH <= 1.0, (
    f"Invalid confidence thresholds: CONFIDENCE_MIN={CONFIDENCE_MIN}, "
    f"CONFIDENCE_HIGH={CONFIDENCE_HIGH}. "
    "Must satisfy: 0.0 <= CONFIDENCE_MIN < CONFIDENCE_HIGH <= 1.0"
)


# ---------------------------------------------------------------------------
# Section 6: Template Responses
# ---------------------------------------------------------------------------
# Pre-written, professional response templates for escalation and out-of-scope
# scenarios. Each template supports string formatting with ticket-specific
# placeholder keys (documented inline with each template).
# Type: dict[str, str]
# Keys: "escalation", "out_of_scope"

TEMPLATE_RESPONSES: dict = {
    # escalation — Sent when a ticket requires human review before routing.
    # Required placeholder keys:
    #   {ticket_id}   — The unique identifier for the support ticket (e.g. "TKT-1234")
    #   {domain}      — The service domain the ticket belongs to (e.g. "HackerRank")
    #   {agent_name}  — The name of the support agent or team handling the escalation
    "escalation": (
        "Hi there,\n\n"
        "Thank you for reaching out to {domain} Support! We've received your request "
        "(Ticket #{ticket_id}) and want to make sure you get the best help possible.\n\n"
        "Your ticket has been flagged for priority review and is being passed to "
        "{agent_name}, who specialises in this area. They'll be in touch with you "
        "shortly to work through this together.\n\n"
        "We appreciate your patience and are committed to resolving this for you as "
        "quickly as we can.\n\n"
        "Warm regards,\n"
        "{domain} Support Team"
    ),

    # out_of_scope — Sent when a ticket cannot be classified within supported scope.
    # Required placeholder keys:
    #   {ticket_id}  — The unique identifier for the support ticket (e.g. "TKT-5678")
    #   {domain}     — The service domain the ticket was submitted under (e.g. "Visa")
    "out_of_scope": (
        "Hi there,\n\n"
        "Thank you for contacting {domain} Support! We've received your message "
        "(Ticket #{ticket_id}) and appreciate you taking the time to get in touch.\n\n"
        "After reviewing your request, it looks like it falls outside the scope of "
        "what our {domain} support team is able to assist with directly. We're sorry "
        "we can't be more help on this one!\n\n"
        "If you believe this was sent in error, or if you'd like to provide more "
        "details so we can better understand your situation, please don't hesitate "
        "to reply to this message and we'll do our best to point you in the right "
        "direction.\n\n"
        "Kind regards,\n"
        "{domain} Support Team"
    ),
}


# ---------------------------------------------------------------------------
# Section 7: Triage Helper Functions
# ---------------------------------------------------------------------------
# Module-level functions that implement core classification logic using the
# configuration data defined above. These are domain-agnostic utilities that
# any triage engine can call directly.


def classify_request_type(ticket_text: str) -> str:
    """
    Classify the request type of a support ticket based on indicator phrases.

    Scans the ticket text against each pattern list in REQUEST_TYPE_PATTERNS
    and returns the request type with the most matches. Falls back to
    "product_issue" when no patterns match.

    Preconditions:
        - ticket_text is a non-empty string
        - REQUEST_TYPE_PATTERNS is non-empty

    Postconditions:
        - Returns a key from REQUEST_TYPE_PATTERNS
        - Returns "product_issue" as default if no pattern matches

    Args:
        ticket_text: The raw text of the support ticket.

    Returns:
        A key from REQUEST_TYPE_PATTERNS (one of "bug", "feature_request",
        "product_issue").
    """
    scores: dict = {rtype: 0 for rtype in REQUEST_TYPE_PATTERNS}

    for request_type, patterns in REQUEST_TYPE_PATTERNS.items():
        for pattern in patterns:
            # Loop invariant: scores[request_type] reflects all patterns checked so far
            if pattern.lower() in ticket_text.lower():
                scores[request_type] += 1

    best_match = max(scores, key=lambda k: scores[k])
    return best_match if scores[best_match] > 0 else "product_issue"


def detect_product_area(ticket_text: str, domain: str) -> str:
    """
    Detect the product area of a support ticket for a given domain.

    Scans the ticket text for area keywords from PRODUCT_AREA_MAPPINGS[domain]
    and returns the first matching area. Falls back to the first area in the
    domain's list when no keyword matches.

    Preconditions:
        - ticket_text is a non-empty string
        - domain is a key in PRODUCT_AREA_MAPPINGS
        - PRODUCT_AREA_MAPPINGS[domain] is a non-empty list

    Postconditions:
        - Returns a string that is a member of PRODUCT_AREA_MAPPINGS[domain]
        - Never returns None or an empty string
        - Falls back to PRODUCT_AREA_MAPPINGS[domain][0] when no match found

    Args:
        ticket_text: The raw text of the support ticket.
        domain: A domain identifier (one of SUPPORTED_DOMAINS).

    Returns:
        A product area string from PRODUCT_AREA_MAPPINGS[domain].
    """
    areas = PRODUCT_AREA_MAPPINGS[domain]
    first_area = areas[0]  # default fallback

    for area in areas:
        # Loop invariant: first_area is always a valid area for this domain
        if area.lower().replace("_", " ") in ticket_text.lower():
            return area

    return first_area
