"""Quick smoke test for Task 4: EscalationRuleChecker"""
from decision_engine import EscalationRuleChecker, DOMAIN_SPECIFIC_ESCALATION_THRESHOLDS
from classifier import (
    RiskAssessment, RiskLevel, RequestTypeResult, RequestType,
    ClassificationResult, ProductAreaResult, Domain
)
from config import CONFIDENCE_MIN

checker = EscalationRuleChecker()

# ---- check_critical_risk ----
ra_critical = RiskAssessment(level=RiskLevel.CRITICAL, confidence=1.0, risk_keywords=[], reason="test")
ra_high = RiskAssessment(level=RiskLevel.HIGH, confidence=0.95, risk_keywords=[], reason="high reason")
ra_low = RiskAssessment(level=RiskLevel.LOW, confidence=0.9, risk_keywords=[], reason="low reason")

assert checker.check_critical_risk(ra_critical) == (True, "Critical risk detected"), "FAIL: critical risk"
assert checker.check_critical_risk(ra_high) == (False, None), "FAIL: high should not trigger critical"
assert checker.check_critical_risk(ra_low) == (False, None), "FAIL: low should not trigger critical"
print("check_critical_risk: OK")

# ---- check_high_risk ----
triggered, reason = checker.check_high_risk(ra_high)
assert triggered is True, "FAIL: high risk should trigger"
assert "high reason" in reason, f"FAIL: reason should include risk reason, got: {reason}"
assert checker.check_high_risk(ra_low) == (False, None), "FAIL: low should not trigger high"
assert checker.check_high_risk(ra_critical) == (False, None), "FAIL: critical should not trigger high"
print("check_high_risk: OK")

# ---- check_invalid_request ----
rt_invalid = RequestTypeResult(type=RequestType.INVALID, confidence=0.0, matched_patterns=[])
rt_bug = RequestTypeResult(type=RequestType.BUG, confidence=0.9, matched_patterns=[])
assert checker.check_invalid_request(rt_invalid) == (True, "Invalid/out-of-scope request"), "FAIL: invalid"
assert checker.check_invalid_request(rt_bug) == (False, None), "FAIL: bug should not trigger invalid"
print("check_invalid_request: OK")

# ---- check_low_confidence ----
clf_low = ClassificationResult(
    request_type=RequestTypeResult(type=RequestType.BUG, confidence=0.5, matched_patterns=[]),
    product_area=ProductAreaResult(area="billing", domain=Domain.HACKERRANK, confidence=0.5, matched_keywords=[]),
    risk=RiskAssessment(level=RiskLevel.LOW, confidence=0.5, risk_keywords=[], reason=""),
    detected_domain=Domain.HACKERRANK,
    raw_text="test",
    cleaned_text="test",
)
triggered, reason = checker.check_low_confidence(clf_low)
assert triggered is True, f"FAIL: avg=0.5 < CONFIDENCE_MIN={CONFIDENCE_MIN} should trigger"
assert "0.50" in reason, f"FAIL: reason should include avg, got: {reason}"

clf_high = ClassificationResult(
    request_type=RequestTypeResult(type=RequestType.BUG, confidence=0.9, matched_patterns=[]),
    product_area=ProductAreaResult(area="billing", domain=Domain.HACKERRANK, confidence=0.85, matched_keywords=[]),
    risk=RiskAssessment(level=RiskLevel.LOW, confidence=0.9, risk_keywords=[], reason=""),
    detected_domain=Domain.HACKERRANK,
    raw_text="test",
    cleaned_text="test",
)
assert checker.check_low_confidence(clf_high) == (False, None), "FAIL: high conf should not trigger"
print("check_low_confidence: OK")

# ---- check_domain_specific_thresholds ----
# hackerrank/billing threshold is 0.95, avg=(0.9+0.85+0.9)/3 ≈ 0.883 → should trigger
triggered, reason = checker.check_domain_specific_thresholds(clf_high)
assert triggered is True, f"FAIL: hackerrank/billing avg~0.88 < 0.95 should trigger, got {triggered}"
assert "hackerrank/billing" in reason, f"FAIL: reason should mention domain/area, got: {reason}"

# Unknown domain → should not trigger
clf_unknown = ClassificationResult(
    request_type=RequestTypeResult(type=RequestType.BUG, confidence=0.5, matched_patterns=[]),
    product_area=ProductAreaResult(area="billing", domain=Domain.UNKNOWN, confidence=0.5, matched_keywords=[]),
    risk=RiskAssessment(level=RiskLevel.LOW, confidence=0.5, risk_keywords=[], reason=""),
    detected_domain=Domain.UNKNOWN,
    raw_text="test",
    cleaned_text="test",
)
assert checker.check_domain_specific_thresholds(clf_unknown) == (False, None), "FAIL: unknown domain"

# hackerrank/assessments threshold is 0.8, avg=(0.9+0.85+0.9)/3 ≈ 0.883 → should NOT trigger
clf_assessments = ClassificationResult(
    request_type=RequestTypeResult(type=RequestType.BUG, confidence=0.9, matched_patterns=[]),
    product_area=ProductAreaResult(area="assessments", domain=Domain.HACKERRANK, confidence=0.85, matched_keywords=[]),
    risk=RiskAssessment(level=RiskLevel.LOW, confidence=0.9, risk_keywords=[], reason=""),
    detected_domain=Domain.HACKERRANK,
    raw_text="test",
    cleaned_text="test",
)
assert checker.check_domain_specific_thresholds(clf_assessments) == (False, None), "FAIL: assessments avg>0.8 should not trigger"

# Area not in domain map → should not trigger
clf_no_area = ClassificationResult(
    request_type=RequestTypeResult(type=RequestType.BUG, confidence=0.5, matched_patterns=[]),
    product_area=ProductAreaResult(area="general", domain=Domain.HACKERRANK, confidence=0.5, matched_keywords=[]),
    risk=RiskAssessment(level=RiskLevel.LOW, confidence=0.5, risk_keywords=[], reason=""),
    detected_domain=Domain.HACKERRANK,
    raw_text="test",
    cleaned_text="test",
)
assert checker.check_domain_specific_thresholds(clf_no_area) == (False, None), "FAIL: area not in map"
print("check_domain_specific_thresholds: OK")

# ---- check_multi_issue_ticket ----
assert checker.check_multi_issue_ticket("What? Why? How? When?") == (True, "Ticket contains multiple issues"), "FAIL: 4 questions"
assert checker.check_multi_issue_ticket("What? Why? How?") == (False, None), "FAIL: 3 questions should not trigger"
assert checker.check_multi_issue_ticket("") == (False, None), "FAIL: empty string"
assert checker.check_multi_issue_ticket("No questions here") == (False, None), "FAIL: no questions"
assert checker.check_multi_issue_ticket("A? B? C? D? E?") == (True, "Ticket contains multiple issues"), "FAIL: 5 questions"
print("check_multi_issue_ticket: OK")

print("\nAll Task 4 checks passed!")
