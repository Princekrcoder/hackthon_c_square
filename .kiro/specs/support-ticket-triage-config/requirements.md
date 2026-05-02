# Requirements Document

## Introduction

This document defines the requirements for the `config.py` module of the support ticket triage system. The module provides all static configuration data — domain constants, risk escalation keywords, request-type patterns, product-area mappings, confidence thresholds, and template responses — in a single importable Python file. Any triage engine can import this module to classify, escalate, or respond to incoming support tickets across three supported domains: HackerRank, Claude, and Visa.

## Glossary

- **Config_Module**: The `config.py` Python file that is the subject of this specification
- **Domain**: One of the three supported service domains — HackerRank, Claude, or Visa
- **Domain_Constant**: A module-level string variable (`DOMAIN_HACKERRANK`, `DOMAIN_CLAUDE`, `DOMAIN_VISA`) that holds the canonical identifier for a domain
- **SUPPORTED_DOMAINS**: The module-level list containing all three domain constant values
- **Risk_Category**: One of the four escalation risk categories: `account_access`, `billing_money`, `security`, `admin`
- **RISK_ESCALATION_KEYWORDS**: The module-level dictionary mapping each Risk_Category to a list of trigger keywords
- **Request_Type**: One of the three ticket classification types: `bug`, `feature_request`, `product_issue`
- **REQUEST_TYPE_PATTERNS**: The module-level dictionary mapping each Request_Type to a list of indicator phrases
- **PRODUCT_AREA_MAPPINGS**: The module-level dictionary mapping each Domain to its list of recognized product areas
- **CONFIDENCE_MIN**: The minimum confidence threshold (0.6) below which a ticket is treated as out-of-scope
- **CONFIDENCE_HIGH**: The high confidence threshold (0.8) above which a ticket is routed directly
- **TEMPLATE_RESPONSES**: The module-level dictionary containing pre-written response templates
- **Triage_Engine**: Any external Python component that imports and uses the Config_Module
- **Confidence_Score**: A float in `[0.0, 1.0]` representing how confidently a ticket can be classified

---

## Requirements

### Requirement 1: Domain Constants

**User Story:** As a triage engine developer, I want canonical domain identifiers defined in one place, so that I can reference domains without hardcoding strings throughout the codebase.

#### Acceptance Criteria

1. THE Config_Module SHALL define `DOMAIN_HACKERRANK` as the non-empty string `"hackerrank"`
2. THE Config_Module SHALL define `DOMAIN_CLAUDE` as the non-empty string `"claude"`
3. THE Config_Module SHALL define `DOMAIN_VISA` as the non-empty string `"visa"`
4. THE Config_Module SHALL define `SUPPORTED_DOMAINS` as a list containing exactly `DOMAIN_HACKERRANK`, `DOMAIN_CLAUDE`, and `DOMAIN_VISA`
5. WHEN a Triage_Engine checks `domain in SUPPORTED_DOMAINS`, THE Config_Module SHALL enable that check to return `True` for each of the three defined domain constants and `False` for any other string

---

### Requirement 2: Risk Escalation Keywords

**User Story:** As a triage engine developer, I want a structured dictionary of escalation keywords organized by risk category, so that I can detect which tickets require escalation and at what priority level.

#### Acceptance Criteria

1. THE Config_Module SHALL define `RISK_ESCALATION_KEYWORDS` as a dictionary with exactly four keys: `"account_access"`, `"billing_money"`, `"security"`, and `"admin"`
2. THE `RISK_ESCALATION_KEYWORDS["account_access"]` list SHALL contain keywords covering scenarios where a user cannot access their account (e.g., `"locked"`, `"cannot access"`, `"lost access"`)
3. THE `RISK_ESCALATION_KEYWORDS["billing_money"]` list SHALL contain keywords covering financial dispute scenarios (e.g., `"refund"`, `"charge"`, `"payment"`, `"dispute"`)
4. THE `RISK_ESCALATION_KEYWORDS["security"]` list SHALL contain keywords covering security breach scenarios (e.g., `"fraud"`, `"hacked"`, `"stolen"`, `"compromised"`)
5. THE `RISK_ESCALATION_KEYWORDS["admin"]` list SHALL contain keywords covering administrative override scenarios (e.g., `"admin override"`, `"special permission"`, `"manual intervention"`)
6. WHEN a ticket text contains any keyword from `RISK_ESCALATION_KEYWORDS[category]`, THE Config_Module SHALL enable case-insensitive substring matching so that the Triage_Engine can detect that `category`
7. IF any keyword list in `RISK_ESCALATION_KEYWORDS` is empty, THEN THE Config_Module SHALL fail a startup assertion so that missing escalation coverage is detected immediately

---

### Requirement 3: Request Type Patterns

**User Story:** As a triage engine developer, I want indicator phrases for each request type, so that I can classify incoming tickets as bugs, feature requests, or product issues.

#### Acceptance Criteria

1. THE Config_Module SHALL define `REQUEST_TYPE_PATTERNS` as a dictionary with exactly three keys: `"bug"`, `"feature_request"`, and `"product_issue"`
2. THE `REQUEST_TYPE_PATTERNS["bug"]` list SHALL contain indicator phrases that signal a defect or malfunction (e.g., `"not working"`, `"broken"`, `"error"`)
3. THE `REQUEST_TYPE_PATTERNS["feature_request"]` list SHALL contain indicator phrases that signal a request for new functionality (e.g., `"would like"`, `"please add"`, `"feature request"`)
4. THE `REQUEST_TYPE_PATTERNS["product_issue"]` list SHALL contain indicator phrases that signal a general product concern (e.g., `"issue with"`, `"problem"`, `"unexpected behavior"`)
5. WHEN `classify_request_type` is called with any non-empty ticket text, THE Config_Module SHALL ensure the function returns a key that is present in `REQUEST_TYPE_PATTERNS`
6. WHEN no patterns from `REQUEST_TYPE_PATTERNS` match the ticket text, THE Config_Module SHALL ensure `classify_request_type` returns `"product_issue"` as the default

---

### Requirement 4: Product Area Mappings

**User Story:** As a triage engine developer, I want a per-domain list of recognized product areas, so that I can route tickets to the correct team within each domain.

#### Acceptance Criteria

1. THE Config_Module SHALL define `PRODUCT_AREA_MAPPINGS` as a dictionary with exactly three keys corresponding to `DOMAIN_HACKERRANK`, `DOMAIN_CLAUDE`, and `DOMAIN_VISA`
2. THE `PRODUCT_AREA_MAPPINGS["hackerrank"]` list SHALL contain product areas relevant to the HackerRank platform (e.g., `"assessments"`, `"coding_challenges"`, `"billing"`, `"account"`)
3. THE `PRODUCT_AREA_MAPPINGS["claude"]` list SHALL contain product areas relevant to the Claude platform (e.g., `"api"`, `"model_behavior"`, `"billing"`, `"account"`)
4. THE `PRODUCT_AREA_MAPPINGS["visa"]` list SHALL contain product areas relevant to Visa services (e.g., `"transactions"`, `"disputes"`, `"account"`, `"fraud"`)
5. WHEN `detect_product_area` is called with any non-empty ticket text and a valid domain, THE Config_Module SHALL ensure the function returns a string that is a member of `PRODUCT_AREA_MAPPINGS[domain]`
6. WHEN no product area keyword is found in the ticket text, THE Config_Module SHALL ensure `detect_product_area` returns the first element of `PRODUCT_AREA_MAPPINGS[domain]` as the default

---

### Requirement 5: Confidence Thresholds

**User Story:** As a triage engine developer, I want numeric confidence thresholds defined in one place, so that I can tune triage sensitivity without modifying business logic.

#### Acceptance Criteria

1. THE Config_Module SHALL define `CONFIDENCE_MIN` as the float value `0.6`
2. THE Config_Module SHALL define `CONFIDENCE_HIGH` as the float value `0.8`
3. THE Config_Module SHALL ensure `CONFIDENCE_MIN` is strictly less than `CONFIDENCE_HIGH`
4. THE Config_Module SHALL ensure both `CONFIDENCE_MIN` and `CONFIDENCE_HIGH` are within the range `[0.0, 1.0]`
5. WHEN a Confidence_Score is greater than or equal to `CONFIDENCE_HIGH`, THE Triage_Engine SHALL route the ticket directly with a classified request type and product area
6. WHEN a Confidence_Score is greater than or equal to `CONFIDENCE_MIN` and less than `CONFIDENCE_HIGH`, THE Triage_Engine SHALL escalate the ticket using the escalation template response
7. WHEN a Confidence_Score is less than `CONFIDENCE_MIN`, THE Triage_Engine SHALL respond with the out-of-scope template response

---

### Requirement 6: Template Responses

**User Story:** As a triage engine developer, I want pre-written professional response templates for escalation and out-of-scope scenarios, so that automated responses maintain a consistent and friendly tone.

#### Acceptance Criteria

1. THE Config_Module SHALL define `TEMPLATE_RESPONSES` as a dictionary containing at least the keys `"escalation"` and `"out_of_scope"`
2. THE `TEMPLATE_RESPONSES["escalation"]` value SHALL be a non-empty string with a professional and friendly tone suitable for sending to a support ticket submitter
3. THE `TEMPLATE_RESPONSES["out_of_scope"]` value SHALL be a non-empty string with a professional and friendly tone that informs the submitter their request is outside the supported scope
4. WHEN `TEMPLATE_RESPONSES["escalation"]` is formatted with all required placeholder keys, THE Config_Module SHALL ensure no `KeyError` is raised
5. WHEN `TEMPLATE_RESPONSES["out_of_scope"]` is formatted with all required placeholder keys, THE Config_Module SHALL ensure no `KeyError` is raised
6. THE Config_Module SHALL document all required placeholder keys in comments adjacent to each template string

---

### Requirement 7: Module Importability and Structure

**User Story:** As a triage engine developer, I want `config.py` to be importable as a standard Python module with no side effects, so that I can safely import it in any context without triggering unintended behavior.

#### Acceptance Criteria

1. THE Config_Module SHALL be importable with `import config` without raising any exceptions under normal conditions
2. THE Config_Module SHALL define all configuration data at module level so that it is loaded once at import time with zero per-request overhead
3. THE Config_Module SHALL have no third-party runtime dependencies — only Python built-in types and syntax
4. THE Config_Module SHALL include inline comments explaining the purpose of each configuration section
5. THE Config_Module SHALL use Python type hint syntax in comments to document the type of each configuration variable
6. WHERE startup assertions are used, THE Config_Module SHALL place them at module level so they execute on import and fail fast if configuration is invalid
