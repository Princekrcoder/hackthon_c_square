from classifier import Classifier
from data_loader import TicketRecord

clf = Classifier()

# Empty batch
results = clf.classify_batch([])
assert results == [], f"Expected [], got {results}"

# Single ticket
t1 = TicketRecord(id=1, issue='The API is broken', subject='API bug', company='claude')
results = clf.classify_batch([t1])
assert len(results) == 1, f"Expected 1 result, got {len(results)}"

# Multiple tickets
t2 = TicketRecord(id=2, issue='I want a new feature', subject='Feature request', company='hackerrank')
t3 = TicketRecord(id=3, issue='account locked fraud hacked admin override', subject='Security', company='visa')
results = clf.classify_batch([t2, t3])
assert len(results) == 2, f"Expected 2 results, got {len(results)}"

summary = clf.get_classification_summary()
assert summary['total_classified'] == 3, f"Expected 3, got {summary['total_classified']}"
assert 'by_request_type' in summary
assert 'by_risk_level' in summary
assert 'by_domain' in summary
assert 'high_risk_count' in summary
assert isinstance(summary['high_risk_count'], int), f"high_risk_count should be int, got {type(summary['high_risk_count'])}"

print('OK', summary)
