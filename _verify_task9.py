from classifier import Classifier, ClassificationResult
from data_loader import TicketRecord

clf = Classifier()
ticket = TicketRecord(id=1, issue='The API is broken and crashes', subject='API bug', company='claude')
result = clf.classify_ticket(ticket)
assert isinstance(result, ClassificationResult), "Result should be ClassificationResult"
assert result.raw_text == 'API bug The API is broken and crashes', f"raw_text mismatch: {result.raw_text!r}"
assert result.cleaned_text != '', "cleaned_text should not be empty"
assert result.request_type is not None, "request_type should not be None"
assert result.risk is not None, "risk should not be None"
assert result.product_area is not None, "product_area should not be None"

# TypeError for non-TicketRecord
try:
    clf.classify_ticket('not a ticket')
    assert False, 'Should have raised TypeError'
except TypeError:
    pass

# Verify statistics are updated
assert clf._total_classified == 1, f"Expected 1, got {clf._total_classified}"
assert clf._by_request_type[result.request_type.type.value] == 1
assert clf._by_risk_level[result.risk.level.value] == 1
assert clf._by_domain[result.detected_domain.value] == 1

print('OK')
