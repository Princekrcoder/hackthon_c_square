from classifier import Classifier, Domain
from config import PRODUCT_AREA_MAPPINGS
clf = Classifier()
# UNKNOWN domain
r = clf.classify_product_area('anything', domain=None)
assert r.area == 'general' and r.confidence == 0.3, f"Failed: {r}"
# Known domain with match
r2 = clf.classify_product_area('I have a billing issue', domain=Domain.HACKERRANK)
assert r2.area == 'billing' and r2.confidence == 0.85, f"Failed: {r2}"
# Known domain no match - fallback to first area
r3 = clf.classify_product_area('random text', domain=Domain.CLAUDE)
assert r3.area == PRODUCT_AREA_MAPPINGS['claude'][0], f"Failed area: {r3}"
assert r3.confidence == 0.5, f"Failed confidence: {r3}"
assert r3.matched_keywords == [], f"Failed keywords: {r3}"
print('OK')
