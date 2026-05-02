# Tasks: Support Ticket Triage Decision Engine

## Overview

Implementation tasks for `decision_engine.py` and its test suite. Tasks are ordered so that each section builds on the previous one. All tasks reference the requirements in `requirements.md` and the design in `design.md`.

---

## Task List

- [x] 1 Set up module skeleton, imports, and logging
  - [x] 1.1 Create `decision_engine.py` with module-level docstring explaining purpose, responsibilities, and typical usage
  - [x] 1.2 Add Section 1 imports: `logging`, `enum`, `dataclasses`, `typing`, `statistics`
  - [x] 1.3 Add Section 2 imports from `config`: `CONFIDENCE_MIN`, `CONFIDENCE_HIGH`, `SUPPORTED_DOMAINS`, `TEMPLATE_RESPONSES`
  - [x] 1.4 Add imports from `classifier`: `RequestType`, `RiskLevel`, `Domain`, `ClassificationResult`, `RequestTypeResult`, `ProductAreaResult`, `RiskAssessment`
  - [x] 1.5 Add import of `TicketRecord` from `data_loader`
  - [x] 1.6 Configure logger: `logging.getLogger(__name__)`, set to `INFO`, attach `StreamHandler` guarded by `if not logger.handlers`, format `[%(levelname)s] %(message)s`

- [x] 2 Implement enums and module-level constants
  - [x] 2.1 Define `TriageAction(Enum)` with members `REPLIED = "replied"` and `ESCALATED = "escalated"`
  - [x] 2.2 Define `EscalationReason(Enum)` with members: `CRITICAL_RISK`, `HIGH_RISK`, `LOW_CONFIDENCE`, `UNSUPPORTED_REQUEST`, `MULTI_ISSUE`, `INVALID_REQUEST`, `UNKNOWN`
  - [x] 2.3 Define `ESCALATION_RULE_PRIORITY_ORDER` list with `RiskLevel.CRITICAL`, `RiskLevel.HIGH`, `RequestType.INVALID` and remaining entries
  - [x] 2.4 Define `DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS` dict with hackerrank, claude, and visa entries as specified in Requirement 3.4

- [x] 3 Implement DecisionResult dataclass
  - [x] 3.1 Define `@dataclass DecisionResult` with all 10 fields: `action`, `confidence`, `reason`, `reasoning_text`, `triggered_rules`, `suggested_response`, `domain`, `request_type`, `risk_level`, `audit_trail`
  - [x] 3.2 Implement `__repr__()` returning a human-readable string
  - [x] 3.3 Implement `to_dict()` returning a plain dict with all fields; enum values serialised to `.value` strings
  - [x] 3.4 Implement `is_safe_to_reply() -> bool` returning `True` iff `action == TriageAction.REPLIED` and `confidence >= CONFIDENCE_HIGH`

- [x] 4 Implement EscalationRuleChecker class
  - [x] 4.1 Define `EscalationRuleChecker` class
  - [x] 4.2 Implement `check_critical_risk(risk_assessment) -> tuple[bool, str | None]`: return `(True, "Critical risk detected")` for `CRITICAL`, else `(False, None)`
  - [x] 4.3 Implement `check_high_risk(risk_assessment) -> tuple[bool, str | None]`: return `(True, reason)` for `HIGH`, else `(False, None)`
  - [x] 4.4 Implement `check_invalid_request(request_type_result) -> tuple[bool, str | None]`: return `(True, "Invalid/out-of-scope request")` for `INVALID`, else `(False, None)`
  - [x] 4.5 Implement `check_low_confidence(classification_result) -> tuple[bool, str | None]`: compute average of `request_type.confidence`, `product_area.confidence`, `risk.confidence`; return `(True, f"Low confidence ({avg:.2f})")` if avg < `CONFIDENCE_MIN`, else `(False, None)`
  - [x] 4.6 Implement `check_domain_specific_thresholds(classification_result) -> tuple[bool, str | None]`: look up domain and area in `DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS`; return `(True, reason)` if threshold not met, else `(False, None)`
  - [x] 4.7 Implement `check_multi_issue_ticket(ticket_text) -> tuple[bool, str | None]`: count `"?"` characters; return `(True, "Ticket contains multiple issues")` if count > 3, else `(False, None)`

- [-] 5 Implement DecisionEngine class
  - [ ] 5.1 Define `DecisionEngine` class with `__init__` initialising all statistics counters: `_total_decisions`, `_replied_count`, `_escalated_count`, `_by_reason`, `_confidence_values` list, and per-reason counters
  - [ ] 5.2 Implement `decide(classification_result) -> DecisionResult` with the full 6-rule priority chain plus DEFAULT safety fallback as specified in Requirements 6.1–6.12
  - [ ] 5.3 Ensure RULE 1 (critical risk) logs `WARNING`, RULE 2 (high risk) logs `INFO`, RULE 4 (low confidence) logs `INFO`, RULE 6 (all pass) logs `DEBUG`
  - [ ] 5.4 Ensure every `DecisionResult` from `decide()` has a populated `triggered_rules` list, non-empty `reasoning_text`, and complete `audit_trail` dict with all required keys
  - [ ] 5.5 Implement `decide_batch(classification_results_list) -> List[DecisionResult]`: call `decide()` for each item, return results in input order, return `[]` for empty input
  - [ ] 5.6 Implement `get_decision_statistics() -> dict` with keys: `total_decisions`, `replied_count`, `escalated_count`, `escalation_rate`, `by_reason`, `critical_risk_count`, `high_risk_count`, `low_confidence_count`
  - [ ] 5.7 Implement `get_decision_confidence_stats() -> dict` with keys: `min_confidence`, `max_confidence`, `avg_confidence`, `median_confidence`, `std_dev`; return all `0.0` when no decisions made; use `statistics` stdlib for computations

- [ ] 6 Implement ResponseRecommendationEngine class
  - [ ] 6.1 Define `ResponseRecommendationEngine` class
  - [ ] 6.2 Implement `get_escalation_response(decision_result, ticket_id) -> str`: format `TEMPLATE_RESPONSES["escalation"]` with `{ticket_id}`, `{domain}` (from `decision_result.domain.value`), `{agent_name}` (domain-appropriate team name); return non-empty string; never raise
  - [ ] 6.3 Implement `get_out_of_scope_response(decision_result, ticket_id) -> str`: format `TEMPLATE_RESPONSES["out_of_scope"]` with `{ticket_id}` and `{domain}`; return non-empty string; never raise
  - [ ] 6.4 Implement `get_safe_reply_guidance(decision_result) -> str`: build guidance string including product area, request type value, and confidence; return non-empty string; never raise

- [ ] 7 Implement triage_ticket integration function
  - [ ] 7.1 Define module-level `triage_ticket(ticket_record, classifier, decision_engine) -> dict`
  - [ ] 7.2 Step 1: call `classifier.classify_ticket(ticket_record)` to get `ClassificationResult`
  - [ ] 7.3 Step 2: call `decision_engine.decide(classification_result)` to get `DecisionResult`
  - [ ] 7.4 Step 3: select response generator based on action and reason (escalation → `get_escalation_response`, invalid → `get_out_of_scope_response`, replied → `get_safe_reply_guidance`)
  - [ ] 7.5 Step 4: return dict with keys `classification`, `decision`, `response`, `audit_trail` as specified in Requirements 13.6–13.10

- [ ] 8 Write unit tests (test_decision_engine.py)
  - [ ] 8.1 Create `test_decision_engine.py` with pytest imports and all required test class stubs
  - [ ] 8.2 Implement `TestEscalationRuleChecker` (5 tests): critical risk triggers, high risk triggers, invalid request triggers, low confidence triggers (avg < CONFIDENCE_MIN), multi-issue detection (> 3 question marks)
  - [ ] 8.3 Implement `TestDecisionEngine` (9 tests): critical always escalates with confidence=1.0, high risk + low confidence escalates, invalid request produces REPLIED with INVALID_REQUEST reason, low confidence escalates, high confidence + low risk produces REPLIED, reasoning_text is non-empty, domain-specific threshold triggers escalation, batch returns correct count in order, statistics are accurate after multiple decisions
  - [ ] 8.4 Implement `TestDecisionResult` (3 tests): `to_dict()` contains all 10 required keys with correct types, `is_safe_to_reply()` returns True only when action=REPLIED and confidence>=CONFIDENCE_HIGH, `__repr__` returns non-empty string
  - [ ] 8.5 Implement `TestResponseRecommendationEngine` (3 tests): escalation response contains ticket_id and domain, out-of-scope response contains ticket_id and domain, safe reply guidance contains product area and request type
  - [ ] 8.6 Implement `TestIntegration` (3 tests): `triage_ticket` returns dict with all 4 required keys, critical risk ticket escalates end-to-end, high-confidence low-risk ticket replies end-to-end
  - [ ] 8.7 Run `pytest test_decision_engine.py -v` and confirm all 18+ tests pass

- [ ] 9 Write property-based tests (test_decision_engine_properties.py)
  - [ ] 9.1 Create `test_decision_engine_properties.py` with hypothesis imports and strategy helpers for generating valid `ClassificationResult` objects
  - [ ] 9.2 Implement Property 1: every `DecisionResult` has valid `TriageAction`, valid `EscalationReason`, and `confidence` in `[0.0, 1.0]` for any valid `ClassificationResult`
  - [ ] 9.3 Implement Property 2: any `ClassificationResult` with `risk.level == RiskLevel.CRITICAL` always produces `action == ESCALATED` and `confidence == 1.0`
  - [ ] 9.4 Implement Property 3: any `ClassificationResult` with `request_type.type == RequestType.INVALID` always produces `action == REPLIED` and `reason == INVALID_REQUEST`
  - [ ] 9.5 Implement Property 4: `decide_batch(results)` returns a list of the same length as `results` with order preserved
  - [ ] 9.6 Implement Property 5: after any sequence of `decide()` calls, `replied_count + escalated_count == total_decisions` and `0 <= escalation_rate <= 100`
  - [ ] 9.7 Implement Property 6: `get_escalation_response`, `get_out_of_scope_response`, and `get_safe_reply_guidance` never raise and always return non-empty strings for any valid `DecisionResult`
  - [ ] 9.8 Run `pytest test_decision_engine_properties.py -v` and confirm all 6 property tests pass
