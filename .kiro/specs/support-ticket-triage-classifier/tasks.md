# Tasks: Support Ticket Triage Classifier

## Overview

Implementation tasks for `classifier.py` and its test suite. Tasks follow the module structure defined in the design document and map directly to the requirements. Complete tasks in order — later tasks depend on earlier ones.

---

## Tasks

- [x] 1. Create classifier.py with module docstring, imports, and logging configuration
  - Create `classifier.py` with a module-level docstring describing purpose, responsibilities, and typical usage
  - Add standard library imports: `re`, `logging`, `enum`, `dataclasses`, `typing`
  - Import from `config`: `REQUEST_TYPE_PATTERNS`, `RISK_ESCALATION_KEYWORDS`, `PRODUCT_AREA_MAPPINGS`, `SUPPORTED_DOMAINS`
  - Import from `data_loader`: `TicketRecord`, `sanitize_ticket_text`
  - Configure logger named `__name__` at `INFO` level with a `StreamHandler` guarded by `if not logger.handlers`
  - **Requirements**: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4

- [x] 2. Implement enums: RequestType, RiskLevel, Domain
  - Define `RequestType(Enum)` with members `BUG`, `FEATURE_REQUEST`, `PRODUCT_ISSUE`, `INVALID`
  - Define `RiskLevel(Enum)` with members `CRITICAL`, `HIGH`, `LOW`
  - Define `Domain(Enum)` with members `HACKERRANK`, `CLAUDE`, `VISA`, `UNKNOWN`
  - Ensure all three enums are importable from the module's public namespace
  - **Requirements**: 3.1, 3.2, 3.3, 3.4

- [x] 3. Implement result dataclasses: RequestTypeResult, ProductAreaResult, RiskAssessment, ClassificationResult
  - Define `RequestTypeResult` dataclass with fields `type: RequestType`, `confidence: float`, `matched_patterns: list[str]`, and `__repr__`
  - Define `ProductAreaResult` dataclass with fields `area: str`, `domain: Domain`, `confidence: float`, `matched_keywords: list[str]`, and `__repr__`
  - Define `RiskAssessment` dataclass with fields `level: RiskLevel`, `confidence: float`, `risk_keywords: list[str]`, `reason: str`, and `__repr__`
  - Define `ClassificationResult` dataclass with fields `request_type`, `product_area`, `risk`, `detected_domain`, `raw_text`, `cleaned_text`, plus `to_dict()` and `__repr__`
  - `ClassificationResult.to_dict()` MUST serialise all nested result objects to dicts
  - **Requirements**: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6

- [x] 4. Implement PatternMatcher utility class
  - Define `PatternMatcher` class with static method `match_patterns(text, patterns_dict) -> dict`
  - `match_patterns` returns `{matched_categories, match_details, total_matches}` using case-insensitive substring matching
  - `match_patterns` returns `{matched_categories: [], match_details: {}, total_matches: 0}` for empty/falsy text
  - Define static method `score_matches(match_details, patterns_dict) -> float` returning a value in `[0.0, 1.0]`
  - `score_matches` returns `0.0` for empty `match_details` or empty `patterns_dict`
  - **Requirements**: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7

- [x] 5. Implement Classifier.classify_request_type
  - Define `Classifier` class with `classify_request_type(self, ticket_text: str) -> RequestTypeResult`
  - Use `PatternMatcher.match_patterns` against `REQUEST_TYPE_PATTERNS` with case-insensitive matching
  - Return `RequestType.INVALID` with confidence `0.0` for empty/whitespace-only text
  - Return `RequestType.BUG` (confidence 0.9), `FEATURE_REQUEST` (0.85), `PRODUCT_ISSUE` (0.75) based on highest match count
  - Return `RequestType.PRODUCT_ISSUE` with confidence `0.5` when no patterns match
  - Populate `matched_patterns` in the result
  - **Requirements**: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8

- [x] 6. Implement Classifier.detect_domain
  - Define `detect_domain(self, ticket_text: str, specified_domain: Optional[str] = None) -> Tuple[Domain, float]`
  - Return `(Domain[specified_domain.upper()], 1.0)` when `specified_domain` is provided
  - Define internal domain keyword tables: HackerRank (`"assessment"`, `"test"`, `"contest"`, `"hackerrank"`, `"coding challenge"`), Claude (`"claude"`, `"api"`, `"model"`, `"tokens"`, `"conversation"`), Visa (`"visa"`, `"card"`, `"payment"`, `"refund"`, `"transaction"`)
  - Return the domain with the highest keyword match count and confidence `0.85` when at least one keyword matches
  - Return `(Domain.UNKNOWN, 0.3)` when no keywords match
  - **Requirements**: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8

- [x] 7. Implement Classifier.classify_product_area
  - Define `classify_product_area(self, ticket_text: str, domain: Optional[Domain] = None) -> ProductAreaResult`
  - Return `ProductAreaResult("general", Domain.UNKNOWN, 0.3, [])` when `domain` is `None` or `Domain.UNKNOWN`
  - For known domains, scan `ticket_text` against `PRODUCT_AREA_MAPPINGS[domain.value]` with case-insensitive matching (replace underscores with spaces)
  - Return matched area with confidence `0.85` and matched keyword on first match
  - Return first area in mapping with confidence `0.5` and empty `matched_keywords` when no match found
  - **Requirements**: 8.1, 8.2, 8.3, 8.4, 8.5

- [x] 8. Implement Classifier.assess_risk_level
  - Define `assess_risk_level(self, ticket_text: str) -> RiskAssessment`
  - Compute risk score by counting distinct `RISK_ESCALATION_KEYWORDS` categories with at least one matching keyword
  - Score ≥ 3 → `CRITICAL`, confidence `1.0`, log `WARNING`
  - Score = 2 → `HIGH`, confidence `0.95`, log `INFO`
  - Score = 1 → `HIGH`, confidence `0.8`, log `INFO`
  - Score = 0 → `LOW`, confidence `0.9`, log `DEBUG`
  - Populate `risk_keywords` with all matched keyword strings
  - Populate `reason` with a non-empty human-readable description
  - **Requirements**: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11

- [x] 9. Implement Classifier.classify_ticket
  - Define `classify_ticket(self, ticket: TicketRecord) -> ClassificationResult`
  - Raise `TypeError` if argument is not a `TicketRecord` instance
  - Construct `full_text = f"{ticket.subject} {ticket.issue}"`
  - Call `sanitize_ticket_text(full_text)` to produce `cleaned_text`
  - Call all four classification methods and assemble `ClassificationResult`
  - Update internal summary statistics after each classification
  - **Requirements**: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9

- [x] 10. Implement Classifier.classify_batch and get_classification_summary
  - Define `classify_batch(self, tickets_list: list) -> List[ClassificationResult]`
  - Call `classify_ticket` for each ticket and return results in the same order
  - Return empty list for empty input without raising
  - Define `get_classification_summary(self) -> dict` returning `{total_classified, by_request_type, by_risk_level, by_domain, high_risk_count}`
  - `high_risk_count` MUST count both `CRITICAL` and `HIGH` risk tickets
  - Initialise summary counters in `__init__` so they accumulate across multiple `classify_batch` and `classify_ticket` calls
  - **Requirements**: 11.1, 11.2, 11.3, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6

- [x] 11. Implement module-level utility functions
  - Define `infer_company_from_text(text: str) -> Optional[str]` returning display names `"HackerRank"`, `"Claude"`, `"Visa"`, or `None`
  - Define `extract_keywords(text: str, keyword_dict: dict) -> dict` returning matched keywords grouped by category (omit categories with no matches)
  - Define `score_text_length_confidence(text: str) -> float` returning `0.7` for < 50 chars, `0.85` for 50–199 chars, `1.0` for ≥ 200 chars
  - **Requirements**: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9

- [x] 12. Write unit tests in test_classifier.py
  - Create `test_classifier.py` with 20+ pytest test cases organised into 8 test classes
  - [x] 12.1 TestEnums (3 tests): verify enum values, membership, and string representations for `RequestType`, `RiskLevel`, `Domain`
  - [x] 12.2 TestRequestTypeClassification (6 tests): bug detection, feature_request detection, product_issue detection, invalid/empty text, priority ordering, case-insensitivity
  - [x] 12.3 TestDomainDetection (6 tests): HackerRank keywords, Claude keywords, Visa keywords, specified domain override (confidence 1.0), unknown domain (confidence 0.3), confidence values
  - [x] 12.4 TestProductAreaClassification (7 tests): each domain with matching keywords, fallback to first area, UNKNOWN domain returns "general" with confidence 0.3
  - [x] 12.5 TestRiskAssessment (6 tests): CRITICAL (score≥3), HIGH (score=2), HIGH (score=1), LOW (no keywords), logging level, confidence values
  - [x] 12.6 TestClassificationResult (3 tests): `to_dict()` structure, `__repr__`, full pipeline via `classify_ticket`
  - [x] 12.7 TestBatchClassification (3 tests): empty batch, single ticket, multiple tickets with summary
  - [x] 12.8 TestUtilityFunctions (3 tests): `infer_company_from_text`, `extract_keywords`, `score_text_length_confidence`
  - All 20+ tests MUST pass with `pytest`
  - **Requirements**: 14.1–14.10

- [x] 13. Write property-based tests in test_classifier_properties.py
  - Create `test_classifier_properties.py` with 6 hypothesis property tests
  - [x] 13.1 Property 1: Classification result validity — every `ClassificationResult` has non-None fields and valid enum values for any valid `TicketRecord`
  - [x] 13.2 Property 2: Confidence bounds — all confidence values in `[0.0, 1.0]`, no NaN or infinity
  - [x] 13.3 Property 3: Risk detection consistency — tickets with ≥ 3 distinct risk keyword categories always produce `CRITICAL` or `HIGH`
  - [x] 13.4 Property 4: Product area validity — returned area is always a member of `PRODUCT_AREA_MAPPINGS[domain.value]` for known domains, or `"general"` for `UNKNOWN`
  - [x] 13.5 Property 5: Classification consistency — classifying the same text twice produces identical `RequestType`, `Domain`, `RiskLevel`, and `area`
  - [x] 13.6 Property 6: Batch consistency — `classify_batch([ticket])` produces the same result as `classify_ticket(ticket)` for any single ticket
  - All 6 property tests MUST pass with `pytest`
  - **Requirements**: 15.1–15.8
