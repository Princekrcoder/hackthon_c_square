# Requirements: Support Ticket Triage Decision Engine

## Introduction

This document defines the functional and non-functional requirements for the `decision_engine.py` module. The module is the production-grade routing layer of the support ticket triage system. It consumes `ClassificationResult` objects from `classifier.py` and applies a deterministic, priority-ordered rule chain to decide whether a ticket should receive an automated reply (`REPLIED`) or be escalated to a human agent (`ESCALATED`). The module integrates with `config.py` (confidence thresholds, template responses), `data_loader.py` (`TicketRecord`), and `classifier.py` (all classification result types). Safety is the primary design constraint: when in doubt, the engine escalates.

---

## Requirements

### Requirement 1: Module Structure and Imports

**User Story**: As a developer integrating the decision engine, I want the module to be importable without side effects and to expose a clean public API, so that I can use it in any Python application without unexpected behaviour.

#### Acceptance Criteria

1.1 The module MUST import only Python standard library modules (`logging`, `enum`, `dataclasses`, `typing`, `statistics`) and the local `config`, `classifier`, and `data_loader` modules.

1.2 The module MUST import the following constants from `config`: `CONFIDENCE_MIN`, `CONFIDENCE_HIGH`, `SUPPORTED_DOMAINS`, `TEMPLATE_RESPONSES`.

1.3 The module MUST import `RequestType`, `RiskLevel`, `Domain`, `ClassificationResult`, `RequestTypeResult`, `ProductAreaResult`, `RiskAssessment` from `classifier`.

1.4 The module MUST import `TicketRecord` from `data_loader`.

1.5 Importing the module MUST NOT produce any side effects beyond configuring the logger and defining module-level names.

---

### Requirement 2: Logging Configuration

**User Story**: As an operator running the decision engine in production, I want structured log output with log levels, so that I can diagnose routing decisions from application logs.

#### Acceptance Criteria

2.1 The module MUST create a logger named `__name__` using `logging.getLogger(__name__)`.

2.2 The logger MUST be set to `INFO` level.

2.3 The module MUST attach a `StreamHandler` (console) to the logger.

2.4 The handler MUST only be added if no handlers are already configured on the logger, guarded by `if not logger.handlers`.

2.5 The log format MUST be `[%(levelname)s] %(message)s`.

---

### Requirement 3: Enums and Constants

**User Story**: As a developer consuming decision results, I want type-safe enum values for triage actions and escalation reasons, so that I can write exhaustive pattern matches without relying on magic strings.

#### Acceptance Criteria

3.1 The module MUST define `TriageAction(Enum)` with members: `REPLIED = "replied"`, `ESCALATED = "escalated"`.

3.2 The module MUST define `EscalationReason(Enum)` with members: `CRITICAL_RISK`, `HIGH_RISK`, `LOW_CONFIDENCE`, `UNSUPPORTED_REQUEST`, `MULTI_ISSUE`, `INVALID_REQUEST`, `UNKNOWN`.

3.3 The module MUST define `ESCALATION_RULE_PRIORITY_ORDER` as a list encoding the priority order of escalation rules, starting with `RiskLevel.CRITICAL` and `RiskLevel.HIGH`, followed by `RequestType.INVALID`.

3.4 The module MUST define `DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS` as a dict with the following structure:
- `"hackerrank"`: `{"billing": 0.95, "account": 0.98, "assessments": 0.8}`
- `"claude"`: `{"api": 0.85, "subscription": 0.95, "account": 0.98}`
- `"visa"`: `{"payments": 0.95, "refunds": 0.98, "disputes": 0.98}`

3.5 All enum classes and constants MUST be importable from the module's public namespace.

---

### Requirement 4: DecisionResult Dataclass

**User Story**: As a downstream consumer of decision results, I want a typed, structured result object carrying the complete output of a triage decision, so that I can access fields with confidence and serialise results for storage or audit.

#### Acceptance Criteria

4.1 The module MUST define a `@dataclass` `DecisionResult` with fields: `action` (`TriageAction`), `confidence` (`float`), `reason` (`EscalationReason`), `reasoning_text` (`str`), `triggered_rules` (`list[str]`), `suggested_response` (`str`), `domain` (`Domain`), `request_type` (`RequestType`), `risk_level` (`RiskLevel`), `audit_trail` (`dict`).

4.2 `DecisionResult` MUST implement `__repr__()` returning a human-readable string representation.

4.3 `DecisionResult` MUST implement `to_dict()` returning a plain `dict` representation of all fields, with enum values serialised to their `.value` strings.

4.4 `DecisionResult` MUST implement `is_safe_to_reply() -> bool` that returns `True` if and only if `action == TriageAction.REPLIED` and `confidence >= CONFIDENCE_HIGH`.

---

### Requirement 5: EscalationRuleChecker Class

**User Story**: As a developer maintaining the decision engine, I want modular, single-responsibility rule evaluators, so that each business rule can be tested and modified independently without affecting other rules.

#### Acceptance Criteria

5.1 The module MUST define an `EscalationRuleChecker` class with exactly 6 methods.

5.2 `check_critical_risk(risk_assessment: RiskAssessment) -> tuple[bool, str | None]` MUST return `(True, "Critical risk detected")` when `risk_assessment.level == RiskLevel.CRITICAL`, and `(False, None)` otherwise.

5.3 `check_high_risk(risk_assessment: RiskAssessment) -> tuple[bool, str | None]` MUST return `(True, reason_str)` when `risk_assessment.level == RiskLevel.HIGH`, where `reason_str` includes the risk assessment reason, and `(False, None)` otherwise.

5.4 `check_invalid_request(request_type_result: RequestTypeResult) -> tuple[bool, str | None]` MUST return `(True, "Invalid/out-of-scope request")` when `request_type_result.type == RequestType.INVALID`, and `(False, None)` otherwise.

5.5 `check_low_confidence(classification_result: ClassificationResult) -> tuple[bool, str | None]` MUST compute the average confidence across `request_type.confidence`, `product_area.confidence`, and `risk.confidence`. It MUST return `(True, f"Low confidence ({avg:.2f})")` when the average is less than `CONFIDENCE_MIN`, and `(False, None)` otherwise.

5.6 `check_domain_specific_thresholds(classification_result: ClassificationResult) -> tuple[bool, str | None]` MUST look up the domain and product area in `DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS`. It MUST return `(True, reason_str)` when the domain and area are both present in the thresholds dict AND the average confidence is below the required threshold. It MUST return `(False, None)` when the domain is not in the thresholds dict, the area is not in the domain's map, or the confidence meets the threshold.

5.7 `check_multi_issue_ticket(ticket_text: str) -> tuple[bool, str | None]` MUST count the number of `"?"` characters in `ticket_text`. It MUST return `(True, "Ticket contains multiple issues")` when the count exceeds 3, and `(False, None)` otherwise.

5.8 All six methods MUST return `(False, None)` for any input that does not trigger the rule, and MUST NOT raise exceptions for expected inputs.

---

### Requirement 6: DecisionEngine — Single Decision

**User Story**: As a support routing system, I want a single `decide()` call to apply all business rules in priority order and return a complete `DecisionResult`, so that routing decisions are deterministic, auditable, and safety-first.

#### Acceptance Criteria

6.1 `DecisionEngine.decide(classification_result: ClassificationResult) -> DecisionResult` MUST apply escalation rules in the following strict priority order: RULE 1 (critical risk), RULE 2 (high risk + low confidence), RULE 3 (invalid request), RULE 4 (low confidence), RULE 5 (domain-specific threshold), RULE 6 (all checks pass), DEFAULT (safety fallback).

6.2 RULE 1: When `risk.level == RiskLevel.CRITICAL`, `decide()` MUST return `DecisionResult` with `action=ESCALATED`, `confidence=1.0`, `reason=EscalationReason.CRITICAL_RISK`, and MUST log a `WARNING` message.

6.3 RULE 2: When `risk.level == RiskLevel.HIGH` AND average confidence < `CONFIDENCE_HIGH`, `decide()` MUST return `DecisionResult` with `action=ESCALATED`, `reason=EscalationReason.HIGH_RISK`, and MUST log an `INFO` message.

6.4 RULE 3: When `request_type.type == RequestType.INVALID`, `decide()` MUST return `DecisionResult` with `action=REPLIED`, `confidence=0.8`, `reason=EscalationReason.INVALID_REQUEST`, and `suggested_response` set to the formatted `out_of_scope` template.

6.5 RULE 4: When average confidence < `CONFIDENCE_MIN`, `decide()` MUST return `DecisionResult` with `action=ESCALATED`, `reason=EscalationReason.LOW_CONFIDENCE`, and MUST log an `INFO` message.

6.6 RULE 5: When the domain-specific threshold check triggers, `decide()` MUST return `DecisionResult` with `action=ESCALATED`, `reason=EscalationReason.UNSUPPORTED_REQUEST`.

6.7 RULE 6: When all checks pass, `decide()` MUST return `DecisionResult` with `action=REPLIED`, `reason=EscalationReason.UNKNOWN`, and MUST log a `DEBUG` message.

6.8 DEFAULT: If no rule fires (safety fallback), `decide()` MUST return `DecisionResult` with `action=ESCALATED`.

6.9 The `triggered_rules` field of every `DecisionResult` MUST contain an ordered list of all rule names that were evaluated before the decision was made.

6.10 The `reasoning_text` field MUST be a non-empty human-readable string explaining the decision.

6.11 The `audit_trail` field MUST be a non-empty dict containing at minimum: `ticket_domain`, `ticket_request_type`, `ticket_risk_level`, `avg_confidence`, `rules_evaluated`, `triggered_rule`, `final_action`, `final_reason`, `decision_confidence`.

6.12 `decide()` MUST update internal statistics counters after each call.

---

### Requirement 7: DecisionEngine — Batch Decisions

**User Story**: As a caller processing multiple classification results, I want to decide on a list of results in a single call, so that I can process an entire classified dataset without writing a loop.

#### Acceptance Criteria

7.1 `DecisionEngine.decide_batch(classification_results_list: list) -> List[DecisionResult]` MUST call `decide()` for each item in `classification_results_list` and return the results in the same order as the input list.

7.2 `decide_batch` MUST return an empty list when `classification_results_list` is empty, without raising.

7.3 `decide_batch` MUST accumulate statistics across all decisions in the batch.

---

### Requirement 8: DecisionEngine — Decision Statistics

**User Story**: As an operator, I want a summary of all decisions made since the engine was initialised, so that I can monitor routing distribution and identify escalation trends.

#### Acceptance Criteria

8.1 `DecisionEngine.get_decision_statistics() -> dict` MUST return a dict with exactly the keys: `total_decisions`, `replied_count`, `escalated_count`, `escalation_rate`, `by_reason`, `critical_risk_count`, `high_risk_count`, `low_confidence_count`.

8.2 `total_decisions` MUST equal the total number of calls to `decide()` since the `DecisionEngine` instance was created.

8.3 `replied_count` MUST equal the number of decisions with `action == TriageAction.REPLIED`.

8.4 `escalated_count` MUST equal the number of decisions with `action == TriageAction.ESCALATED`.

8.5 `escalation_rate` MUST equal `(escalated_count / total_decisions) * 100` when `total_decisions > 0`, and `0.0` when `total_decisions == 0`.

8.6 `by_reason` MUST be a dict mapping each `EscalationReason` value string to its count.

8.7 `critical_risk_count` MUST equal the count of decisions with `reason == EscalationReason.CRITICAL_RISK`.

8.8 `high_risk_count` MUST equal the count of decisions with `reason == EscalationReason.HIGH_RISK`.

8.9 `low_confidence_count` MUST equal the count of decisions with `reason == EscalationReason.LOW_CONFIDENCE`.

---

### Requirement 9: DecisionEngine — Confidence Statistics

**User Story**: As an operator, I want statistical summaries of decision confidence values, so that I can monitor the quality of the classification pipeline over time.

#### Acceptance Criteria

9.1 `DecisionEngine.get_decision_confidence_stats() -> dict` MUST return a dict with exactly the keys: `min_confidence`, `max_confidence`, `avg_confidence`, `median_confidence`, `std_dev`.

9.2 All values MUST be floats.

9.3 When no decisions have been made, all values MUST be `0.0`.

9.4 When at least one decision has been made, `min_confidence` and `max_confidence` MUST reflect the actual minimum and maximum confidence values seen.

9.5 `std_dev` MUST be `0.0` when fewer than 2 decisions have been made (to avoid division-by-zero).

---

### Requirement 10: ResponseRecommendationEngine — Escalation Response

**User Story**: As a support system, I want a formatted escalation response string for escalated tickets, so that submitters receive a professional, personalised acknowledgement.

#### Acceptance Criteria

10.1 `ResponseRecommendationEngine.get_escalation_response(decision_result: DecisionResult, ticket_id: str) -> str` MUST format `TEMPLATE_RESPONSES["escalation"]` with `{ticket_id}`, `{domain}` (from `decision_result.domain.value`), and `{agent_name}` (a domain-appropriate agent name or team name).

10.2 The returned string MUST be non-empty.

10.3 The method MUST NOT raise an exception for any valid `DecisionResult` input.

---

### Requirement 11: ResponseRecommendationEngine — Out-of-Scope Response

**User Story**: As a support system, I want a formatted out-of-scope response string for invalid requests, so that submitters receive a clear, professional explanation that their request is outside the supported scope.

#### Acceptance Criteria

11.1 `ResponseRecommendationEngine.get_out_of_scope_response(decision_result: DecisionResult, ticket_id: str) -> str` MUST format `TEMPLATE_RESPONSES["out_of_scope"]` with `{ticket_id}` and `{domain}` (from `decision_result.domain.value`).

11.2 The returned string MUST be non-empty.

11.3 The method MUST NOT raise an exception for any valid `DecisionResult` input.

---

### Requirement 12: ResponseRecommendationEngine — Safe Reply Guidance

**User Story**: As a support agent, I want contextual guidance for tickets that are safe to reply to automatically, so that the automated response is relevant to the ticket's product area and request type.

#### Acceptance Criteria

12.1 `ResponseRecommendationEngine.get_safe_reply_guidance(decision_result: DecisionResult) -> str` MUST return a non-empty string.

12.2 The returned string MUST include the product area name from `decision_result` (derived from the domain and request type context).

12.3 The returned string MUST include the request type value.

12.4 The returned string MUST include the confidence value.

12.5 The method MUST NOT raise an exception for any valid `DecisionResult` input.

---

### Requirement 13: triage_ticket Integration Function

**User Story**: As a caller, I want a single function that orchestrates the full pipeline from a raw `TicketRecord` to a final response dict, so that I can triage a ticket without manually coordinating the classifier and decision engine.

#### Acceptance Criteria

13.1 `triage_ticket(ticket_record: TicketRecord, classifier: Classifier, decision_engine: DecisionEngine) -> dict` MUST call `classifier.classify_ticket(ticket_record)` to produce a `ClassificationResult`.

13.2 `triage_ticket` MUST call `decision_engine.decide(classification_result)` to produce a `DecisionResult`.

13.3 When `decision_result.action == TriageAction.ESCALATED` and `decision_result.reason != EscalationReason.INVALID_REQUEST`, `triage_ticket` MUST generate the response using `ResponseRecommendationEngine.get_escalation_response`.

13.4 When `decision_result.reason == EscalationReason.INVALID_REQUEST`, `triage_ticket` MUST generate the response using `ResponseRecommendationEngine.get_out_of_scope_response`.

13.5 When `decision_result.action == TriageAction.REPLIED`, `triage_ticket` MUST generate the response using `ResponseRecommendationEngine.get_safe_reply_guidance`.

13.6 `triage_ticket` MUST return a dict with exactly the keys: `classification`, `decision`, `response`, `audit_trail`.

13.7 The `classification` value MUST be the result of `classification_result.to_dict()`.

13.8 The `decision` value MUST be the result of `decision_result.to_dict()`.

13.9 The `response` value MUST be a non-empty string.

13.10 The `audit_trail` value MUST be `decision_result.audit_trail`.

---

### Requirement 14: Test Coverage — Unit Tests

**User Story**: As a developer maintaining the module, I want a comprehensive unit test suite, so that regressions are caught immediately and the module's contract is clearly documented through tests.

#### Acceptance Criteria

14.1 The unit test file `test_decision_engine.py` MUST contain at least 18 test cases using `pytest`.

14.2 Tests MUST cover `TestEscalationRuleChecker` (5 tests): critical risk triggers, high risk triggers, invalid request triggers, low confidence triggers, multi-issue detection.

14.3 Tests MUST cover `TestDecisionEngine` (9 tests): critical always escalates with confidence 1.0, high risk + low confidence escalates, invalid request produces REPLIED, low confidence escalates, high confidence + low risk produces REPLIED, reasoning_text is populated, domain-specific thresholds trigger escalation, batch decisions return correct count, statistics are accurate after multiple decisions.

14.4 Tests MUST cover `TestDecisionResult` (3 tests): `to_dict()` contains all required keys with correct types, `is_safe_to_reply()` returns True only when action is REPLIED and confidence >= CONFIDENCE_HIGH, `__repr__` returns a non-empty string.

14.5 Tests MUST cover `TestResponseRecommendationEngine` (3 tests): escalation response contains ticket_id and domain, out-of-scope response contains ticket_id and domain, safe reply guidance contains product area and request type.

14.6 Tests MUST cover `TestIntegration` (3 tests): full pipeline via `triage_ticket` returns dict with all required keys, a ticket with CRITICAL risk produces ESCALATED decision end-to-end, a ticket with high confidence and low risk produces REPLIED decision end-to-end.

14.7 All 18+ unit tests MUST pass when run with `pytest`.

---

### Requirement 15: Test Coverage — Property-Based Tests

**User Story**: As a developer, I want property-based tests that verify universal invariants across a wide range of generated inputs, so that edge cases not covered by example-based tests are also validated.

#### Acceptance Criteria

15.1 The property test file `test_decision_engine_properties.py` MUST contain exactly 6 property-based tests using the `hypothesis` library.

15.2 Property 1 MUST verify that every `DecisionResult` produced by `decide()` has a valid `TriageAction`, a valid `EscalationReason`, and a `confidence` value in `[0.0, 1.0]`, for any valid `ClassificationResult` input.

15.3 Property 2 MUST verify that any `ClassificationResult` with `risk.level == RiskLevel.CRITICAL` always produces a `DecisionResult` with `action == TriageAction.ESCALATED` and `confidence == 1.0`.

15.4 Property 3 MUST verify that any `ClassificationResult` with `request_type.type == RequestType.INVALID` always produces a `DecisionResult` with `action == TriageAction.REPLIED` and `reason == EscalationReason.INVALID_REQUEST`.

15.5 Property 4 MUST verify that `decide_batch(results)` returns a list of the same length as `results` and that each element corresponds to the same input (order is preserved).

15.6 Property 5 MUST verify that after any sequence of `decide()` calls, `replied_count + escalated_count == total_decisions` and `0 <= escalation_rate <= 100`.

15.7 Property 6 MUST verify that `get_escalation_response`, `get_out_of_scope_response`, and `get_safe_reply_guidance` never raise exceptions and always return non-empty strings for any valid `DecisionResult` input.

15.8 All 6 property tests MUST pass when run with `pytest`.
