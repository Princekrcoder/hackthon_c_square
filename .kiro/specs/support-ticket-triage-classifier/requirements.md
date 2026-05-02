# Requirements: Support Ticket Triage Classifier

## Introduction

This document defines the functional and non-functional requirements for the `classifier.py` module. The module is the core intelligence engine of the support ticket triage system, consuming `TicketRecord` objects from `data_loader.py` and classifying each ticket across four dimensions — request type, product area, risk level, and domain — using pattern matching and keyword analysis driven by constants from `config.py`.

---

## Requirements

### Requirement 1: Module Structure and Imports

**User Story**: As a developer integrating the classifier, I want the module to be importable without side effects and to expose a clean public API, so that I can use it in any Python application without unexpected behaviour.

#### Acceptance Criteria

1.1 The module MUST include a docstring explaining its purpose, responsibilities, and typical usage.

1.2 The module MUST import only Python standard library modules (`re`, `logging`, `enum`, `dataclasses`, `typing`) and the local `config` and `data_loader` modules.

1.3 The module MUST import the following constants from `config`: `REQUEST_TYPE_PATTERNS`, `RISK_ESCALATION_KEYWORDS`, `PRODUCT_AREA_MAPPINGS`, `SUPPORTED_DOMAINS`.

1.4 The module MUST import `TicketRecord` and `sanitize_ticket_text` from `data_loader`.

1.5 Importing the module MUST NOT produce any side effects beyond configuring the logger and defining module-level names.

---

### Requirement 2: Logging Configuration

**User Story**: As an operator running the classifier in production, I want structured log output with timestamps and log levels, so that I can diagnose classification decisions from application logs.

#### Acceptance Criteria

2.1 The module MUST create a logger named `__name__` using `logging.getLogger(__name__)`.

2.2 The logger MUST be set to `INFO` level.

2.3 The module MUST attach a `StreamHandler` (console) to the logger.

2.4 The handler MUST only be added if no handlers are already configured on the logger, guarded by `if not logger.handlers`.

---

### Requirement 3: Enums

**User Story**: As a developer consuming classification results, I want type-safe enum values for request type, risk level, and domain, so that I can write exhaustive pattern matches without relying on magic strings.

#### Acceptance Criteria

3.1 The module MUST define `RequestType(Enum)` with members: `BUG = "bug"`, `FEATURE_REQUEST = "feature_request"`, `PRODUCT_ISSUE = "product_issue"`, `INVALID = "invalid"`.

3.2 The module MUST define `RiskLevel(Enum)` with members: `CRITICAL = "critical"`, `HIGH = "high"`, `LOW = "low"`.

3.3 The module MUST define `Domain(Enum)` with members: `HACKERRANK = "hackerrank"`, `CLAUDE = "claude"`, `VISA = "visa"`, `UNKNOWN = "unknown"`.

3.4 All three enum classes MUST be importable from the module's public namespace.

---

### Requirement 4: Result Dataclasses

**User Story**: As a downstream consumer of classification results, I want typed, structured result objects for each classification dimension, so that I can access fields with confidence and serialise results for storage or display.

#### Acceptance Criteria

4.1 The module MUST define a `@dataclass` `RequestTypeResult` with fields: `type: RequestType`, `confidence: float`, `matched_patterns: list[str]`, and a `__repr__` method.

4.2 The module MUST define a `@dataclass` `ProductAreaResult` with fields: `area: str`, `domain: Domain`, `confidence: float`, `matched_keywords: list[str]`, and a `__repr__` method.

4.3 The module MUST define a `@dataclass` `RiskAssessment` with fields: `level: RiskLevel`, `confidence: float`, `risk_keywords: list[str]`, `reason: str`, and a `__repr__` method.

4.4 The module MUST define a `@dataclass` `ClassificationResult` with fields: `request_type: RequestTypeResult`, `product_area: ProductAreaResult`, `risk: RiskAssessment`, `detected_domain: Domain`, `raw_text: str`, `cleaned_text: str`.

4.5 `ClassificationResult` MUST implement `to_dict()` returning a plain `dict` representation of all fields, with nested result objects also serialised to dicts.

4.6 `ClassificationResult` MUST implement `__repr__()` returning a human-readable string.

---

### Requirement 5: PatternMatcher Utility Class

**User Story**: As a developer extending the classifier, I want a reusable pattern-matching utility, so that I can apply multi-category keyword matching and confidence scoring without duplicating logic.

#### Acceptance Criteria

5.1 The module MUST define a `PatternMatcher` class with a static method `match_patterns(text: str, patterns_dict: dict) -> dict`.

5.2 `match_patterns` MUST return a dict with exactly the keys: `matched_categories` (list of category strings), `match_details` (dict mapping category to list of matched patterns), `total_matches` (int).

5.3 `match_patterns` MUST perform case-insensitive substring matching of each pattern against `text`.

5.4 `match_patterns` MUST return `{matched_categories: [], match_details: {}, total_matches: 0}` for empty or falsy `text`.

5.5 The module MUST define a static method `score_matches(match_details: dict, patterns_dict: dict) -> float` on `PatternMatcher`.

5.6 `score_matches` MUST return a float in `[0.0, 1.0]` representing the proportion of total patterns that were matched.

5.7 `score_matches` MUST return `0.0` for empty `match_details` or empty `patterns_dict`.

---

### Requirement 6: Classifier — Request Type Classification

**User Story**: As a support routing system, I want each ticket classified by request type (bug, feature request, product issue, or invalid), so that tickets can be routed to the correct handling team.

#### Acceptance Criteria

6.1 `Classifier.classify_request_type(ticket_text: str) -> RequestTypeResult` MUST scan `ticket_text` against `REQUEST_TYPE_PATTERNS` from `config.py` using case-insensitive substring matching.

6.2 `classify_request_type` MUST return `RequestType.BUG` with confidence `0.9` when bug patterns produce the highest match count.

6.3 `classify_request_type` MUST return `RequestType.FEATURE_REQUEST` with confidence `0.85` when feature request patterns produce the highest match count.

6.4 `classify_request_type` MUST return `RequestType.PRODUCT_ISSUE` with confidence `0.75` when product issue patterns produce the highest match count.

6.5 `classify_request_type` MUST return `RequestType.PRODUCT_ISSUE` with confidence `0.5` when no patterns match (default fallback).

6.6 `classify_request_type` MUST return `RequestType.INVALID` with confidence `0.0` for empty or whitespace-only `ticket_text`.

6.7 `classify_request_type` MUST populate `matched_patterns` in the result with the list of patterns that matched.

6.8 Classification MUST be case-insensitive: "BUG", "Bug", and "bug" in ticket text MUST all match the bug pattern "bug".

---

### Requirement 7: Classifier — Domain Detection

**User Story**: As a support routing system, I want each ticket's domain detected automatically from its text, so that tickets can be routed to the correct domain team without requiring the submitter to specify a domain.

#### Acceptance Criteria

7.1 `Classifier.detect_domain(ticket_text: str, specified_domain: Optional[str] = None) -> Tuple[Domain, float]` MUST return `(Domain[specified_domain.upper()], 1.0)` when `specified_domain` is provided and non-None.

7.2 When `specified_domain` is None, `detect_domain` MUST scan `ticket_text` for domain-specific keywords using case-insensitive matching.

7.3 HackerRank keywords MUST include: `"assessment"`, `"test"`, `"contest"`, `"hackerrank"`, `"coding challenge"`.

7.4 Claude keywords MUST include: `"claude"`, `"api"`, `"model"`, `"tokens"`, `"conversation"`.

7.5 Visa keywords MUST include: `"visa"`, `"card"`, `"payment"`, `"refund"`, `"transaction"`.

7.6 `detect_domain` MUST return the domain with the highest keyword match count and confidence `0.85` when at least one keyword matches.

7.7 `detect_domain` MUST return `(Domain.UNKNOWN, 0.3)` when no domain keywords match.

7.8 The returned confidence MUST be a float in `[0.0, 1.0]`.

---

### Requirement 8: Classifier — Product Area Classification

**User Story**: As a support routing system, I want each ticket classified into a product area within its domain, so that tickets can be routed to the correct specialist team.

#### Acceptance Criteria

8.1 `Classifier.classify_product_area(ticket_text: str, domain: Optional[Domain] = None) -> ProductAreaResult` MUST return `ProductAreaResult("general", Domain.UNKNOWN, 0.3, [])` when `domain` is `None` or `Domain.UNKNOWN`.

8.2 For a known domain, `classify_product_area` MUST scan `ticket_text` for area keywords from `PRODUCT_AREA_MAPPINGS[domain.value]` using case-insensitive matching (replacing underscores with spaces for matching).

8.3 When a keyword match is found, `classify_product_area` MUST return the matched area with confidence `0.85` and the matched keyword in `matched_keywords`.

8.4 When no keyword matches, `classify_product_area` MUST return the first area in `PRODUCT_AREA_MAPPINGS[domain.value]` with confidence `0.5` and an empty `matched_keywords` list.

8.5 The returned `area` MUST always be a member of `PRODUCT_AREA_MAPPINGS[domain.value]` for known domains, or `"general"` for `Domain.UNKNOWN`.

---

### Requirement 9: Classifier — Risk Assessment

**User Story**: As a support escalation system, I want each ticket assessed for risk level based on escalation keywords, so that high-risk tickets are flagged for immediate human review.

#### Acceptance Criteria

9.1 `Classifier.assess_risk_level(ticket_text: str) -> RiskAssessment` MUST scan `ticket_text` against `RISK_ESCALATION_KEYWORDS` from `config.py` using case-insensitive substring matching.

9.2 The risk score MUST be computed by counting the number of distinct keyword categories (from `RISK_ESCALATION_KEYWORDS`) that have at least one matching keyword in the text.

9.3 A score ≥ 3 MUST produce `RiskLevel.CRITICAL` with confidence `1.0`.

9.4 A score of 2 MUST produce `RiskLevel.HIGH` with confidence `0.95`.

9.5 A score of 1 MUST produce `RiskLevel.HIGH` with confidence `0.8`.

9.6 A score of 0 MUST produce `RiskLevel.LOW` with confidence `0.9`.

9.7 `assess_risk_level` MUST log a `WARNING` message when the result is `CRITICAL`.

9.8 `assess_risk_level` MUST log an `INFO` message when the result is `HIGH`.

9.9 `assess_risk_level` MUST log a `DEBUG` message when the result is `LOW`.

9.10 The `risk_keywords` field MUST contain all matched keyword strings from the text.

9.11 The `reason` field MUST be a non-empty human-readable string describing the risk assessment outcome.

---

### Requirement 10: Classifier — Single Ticket Classification

**User Story**: As a caller, I want to classify a single `TicketRecord` through the full pipeline in one call, so that I receive a complete `ClassificationResult` without orchestrating each step manually.

#### Acceptance Criteria

10.1 `Classifier.classify_ticket(ticket: TicketRecord) -> ClassificationResult` MUST construct `full_text` as `f"{ticket.subject} {ticket.issue}"`.

10.2 `classify_ticket` MUST call `sanitize_ticket_text(full_text)` to produce `cleaned_text`.

10.3 `classify_ticket` MUST call `classify_request_type(cleaned_text)` and include the result in `ClassificationResult.request_type`.

10.4 `classify_ticket` MUST call `detect_domain(cleaned_text)` and include the result in `ClassificationResult.detected_domain`.

10.5 `classify_ticket` MUST call `classify_product_area(cleaned_text, domain)` using the detected domain and include the result in `ClassificationResult.product_area`.

10.6 `classify_ticket` MUST call `assess_risk_level(cleaned_text)` and include the result in `ClassificationResult.risk`.

10.7 `classify_ticket` MUST store `full_text` in `ClassificationResult.raw_text` and `cleaned_text` in `ClassificationResult.cleaned_text`.

10.8 `classify_ticket` MUST raise `TypeError` if the argument is not a `TicketRecord` instance.

10.9 `classify_ticket` MUST update the internal summary statistics after each classification.

---

### Requirement 11: Classifier — Batch Classification

**User Story**: As a caller processing multiple tickets, I want to classify a list of tickets in a single call, so that I can process an entire loaded dataset without writing a loop.

#### Acceptance Criteria

11.1 `Classifier.classify_batch(tickets_list: list) -> List[ClassificationResult]` MUST call `classify_ticket` for each ticket in `tickets_list` and return the results in the same order.

11.2 `classify_batch` MUST return an empty list when `tickets_list` is empty, without raising.

11.3 `classify_batch` MUST accumulate summary statistics across all tickets in the batch.

---

### Requirement 12: Classifier — Classification Summary

**User Story**: As an operator, I want a summary of all classifications performed since the classifier was initialised, so that I can monitor classification distribution and identify high-risk ticket volumes.

#### Acceptance Criteria

12.1 `Classifier.get_classification_summary() -> dict` MUST return a dict with exactly the keys: `total_classified`, `by_request_type`, `by_risk_level`, `by_domain`, `high_risk_count`.

12.2 `total_classified` MUST equal the total number of tickets classified since the `Classifier` instance was created.

12.3 `by_request_type` MUST be a dict mapping each `RequestType` value string to its count.

12.4 `by_risk_level` MUST be a dict mapping each `RiskLevel` value string to its count.

12.5 `by_domain` MUST be a dict mapping each `Domain` value string to its count.

12.6 `high_risk_count` MUST equal the count of tickets classified as `CRITICAL` or `HIGH` risk.

---

### Requirement 13: Utility Functions

**User Story**: As a developer, I want module-level utility functions for common text-analysis operations, so that I can infer company names, extract keywords, and adjust confidence based on text length without instantiating the Classifier class.

#### Acceptance Criteria

13.1 `infer_company_from_text(text: str) -> Optional[str]` MUST return the display name `"HackerRank"` when HackerRank domain keywords are found in `text`.

13.2 `infer_company_from_text` MUST return the display name `"Claude"` when Claude domain keywords are found in `text`.

13.3 `infer_company_from_text` MUST return the display name `"Visa"` when Visa domain keywords are found in `text`.

13.4 `infer_company_from_text` MUST return `None` when no domain keywords are found.

13.5 `extract_keywords(text: str, keyword_dict: dict) -> dict` MUST return a dict mapping each category key from `keyword_dict` to a list of keywords from that category found in `text` (case-insensitive).

13.6 `extract_keywords` MUST return only categories that have at least one match; categories with no matches MUST be omitted from the result.

13.7 `score_text_length_confidence(text: str) -> float` MUST return `0.7` for text shorter than 50 characters.

13.8 `score_text_length_confidence` MUST return `0.85` for text between 50 and 199 characters (inclusive).

13.9 `score_text_length_confidence` MUST return `1.0` for text of 200 or more characters.

---

### Requirement 14: Test Coverage — Unit Tests

**User Story**: As a developer maintaining the module, I want a comprehensive unit test suite, so that regressions are caught immediately and the module's contract is clearly documented through tests.

#### Acceptance Criteria

14.1 The unit test file `test_classifier.py` MUST contain at least 20 test cases using `pytest`.

14.2 Tests MUST cover `TestEnums` (3 tests): enum values, membership, and string representations for all three enums.

14.3 Tests MUST cover `TestRequestTypeClassification` (6 tests): bug detection, feature_request detection, product_issue detection, invalid/empty text, priority ordering when multiple patterns match, case-insensitivity.

14.4 Tests MUST cover `TestDomainDetection` (6 tests): HackerRank keyword detection, Claude keyword detection, Visa keyword detection, specified domain override with confidence 1.0, unknown domain returns UNKNOWN with confidence 0.3, confidence values.

14.5 Tests MUST cover `TestProductAreaClassification` (7 tests): each domain with matching keywords, fallback to first area when no match, UNKNOWN domain returns "general" with confidence 0.3.

14.6 Tests MUST cover `TestRiskAssessment` (6 tests): CRITICAL (score≥3), HIGH (score=2), HIGH (score=1), LOW (no keywords), correct logging level, confidence values.

14.7 Tests MUST cover `TestClassificationResult` (3 tests): `to_dict()` structure and completeness, `__repr__` output, full pipeline via `classify_ticket`.

14.8 Tests MUST cover `TestBatchClassification` (3 tests): empty batch returns empty list, single ticket batch, multiple tickets with correct summary counts.

14.9 Tests MUST cover `TestUtilityFunctions` (3 tests): `infer_company_from_text` for each domain and None, `extract_keywords` with matching and non-matching categories, `score_text_length_confidence` for all three length bands.

14.10 All 20+ unit tests MUST pass when run with `pytest`.

---

### Requirement 15: Test Coverage — Property-Based Tests

**User Story**: As a developer, I want property-based tests that verify universal invariants across a wide range of generated inputs, so that edge cases not covered by example-based tests are also validated.

#### Acceptance Criteria

15.1 The property test file `test_classifier_properties.py` MUST contain exactly 6 property-based tests using the `hypothesis` library.

15.2 Property 1 MUST verify that every `ClassificationResult` produced by `classify_ticket` has non-None fields and valid enum values for any valid `TicketRecord` input.

15.3 Property 2 MUST verify that all confidence values in a `ClassificationResult` are in `[0.0, 1.0]` with no NaN or infinity, for any valid `TicketRecord` input.

15.4 Property 3 MUST verify that tickets containing at least 3 distinct `RISK_ESCALATION_KEYWORDS` categories always produce `CRITICAL` or `HIGH` risk level.

15.5 Property 4 MUST verify that the returned `area` in `ProductAreaResult` is always a member of `PRODUCT_AREA_MAPPINGS[domain.value]` for known domains, or `"general"` for `Domain.UNKNOWN`.

15.6 Property 5 MUST verify that classifying the same ticket text twice always produces identical `RequestType`, `Domain`, `RiskLevel`, and `area` values (deterministic classification).

15.7 Property 6 MUST verify that `classify_batch([ticket])` produces the same `RequestType`, `Domain`, `RiskLevel`, and `area` as `classify_ticket(ticket)` for any single valid ticket.

15.8 All 6 property tests MUST pass when run with `pytest`.
