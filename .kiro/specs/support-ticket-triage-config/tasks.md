# Tasks

## Task List

- [x] 1. Create the config.py module skeleton
  - [x] 1.1 Create `config.py` at the project root with a module docstring explaining its purpose
  - [x] 1.2 Add a section comment structure for each of the six configuration sections
  - [x] 1.3 Verify the file is importable with `import config` without errors

- [x] 2. Implement Domain Constants
  - [x] 2.1 Define `DOMAIN_HACKERRANK = "hackerrank"`
  - [x] 2.2 Define `DOMAIN_CLAUDE = "claude"`
  - [x] 2.3 Define `DOMAIN_VISA = "visa"`
  - [x] 2.4 Define `SUPPORTED_DOMAINS = [DOMAIN_HACKERRANK, DOMAIN_CLAUDE, DOMAIN_VISA]`
  - [x] 2.5 Add inline comments explaining the purpose of domain constants

- [x] 3. Implement Risk Escalation Keywords
  - [x] 3.1 Define `RISK_ESCALATION_KEYWORDS` dictionary with `"account_access"` key and relevant keywords (e.g., `"locked"`, `"cannot access"`, `"lost access"`, `"account disabled"`, `"login failed"`)
  - [x] 3.2 Add `"billing_money"` key with relevant keywords (e.g., `"refund"`, `"charge"`, `"payment"`, `"dispute"`, `"overcharged"`, `"invoice"`)
  - [x] 3.3 Add `"security"` key with relevant keywords (e.g., `"fraud"`, `"hacked"`, `"stolen"`, `"compromised"`, `"unauthorized"`, `"breach"`)
  - [x] 3.4 Add `"admin"` key with relevant keywords (e.g., `"admin override"`, `"special permission"`, `"manual intervention"`, `"bypass"`, `"escalate to admin"`)
  - [x] 3.5 Add inline comments explaining each category and its escalation priority
  - [x] 3.6 Add a module-level startup assertion: `assert all(v for v in RISK_ESCALATION_KEYWORDS.values())`

- [x] 4. Implement Request Type Patterns
  - [x] 4.1 Define `REQUEST_TYPE_PATTERNS` dictionary with `"bug"` key and indicator phrases (e.g., `"not working"`, `"broken"`, `"error"`, `"crash"`, `"bug"`, `"fails"`)
  - [x] 4.2 Add `"feature_request"` key with indicator phrases (e.g., `"would like"`, `"please add"`, `"feature request"`, `"enhancement"`, `"suggestion"`, `"could you add"`)
  - [x] 4.3 Add `"product_issue"` key with indicator phrases (e.g., `"issue with"`, `"problem"`, `"unexpected behavior"`, `"not as expected"`, `"confused about"`)
  - [x] 4.4 Add inline comments explaining that patterns are domain-agnostic

- [x] 5. Implement Product Area Mappings
  - [x] 5.1 Define `PRODUCT_AREA_MAPPINGS` dictionary with `"hackerrank"` key and areas (e.g., `"assessments"`, `"coding_challenges"`, `"billing"`, `"account"`, `"integrations"`, `"reporting"`)
  - [x] 5.2 Add `"claude"` key with areas (e.g., `"api"`, `"model_behavior"`, `"billing"`, `"account"`, `"rate_limits"`, `"context_window"`)
  - [x] 5.3 Add `"visa"` key with areas (e.g., `"transactions"`, `"disputes"`, `"account"`, `"fraud"`, `"cards"`, `"payments"`)
  - [x] 5.4 Add inline comments explaining that the first area in each list is the default fallback

- [x] 6. Implement Confidence Thresholds
  - [x] 6.1 Define `CONFIDENCE_MIN: float = 0.6`
  - [x] 6.2 Define `CONFIDENCE_HIGH: float = 0.8`
  - [x] 6.3 Add inline comments explaining the three triage decision branches (route / escalate / out-of-scope)
  - [x] 6.4 Add a module-level startup assertion: `assert 0.0 <= CONFIDENCE_MIN < CONFIDENCE_HIGH <= 1.0`

- [x] 7. Implement Template Responses
  - [x] 7.1 Define `TEMPLATE_RESPONSES` dictionary with `"escalation"` key containing a professional, friendly escalation message with placeholders `{ticket_id}`, `{domain}`, and `{agent_name}`
  - [x] 7.2 Add `"out_of_scope"` key containing a professional, friendly out-of-scope message with placeholders `{ticket_id}` and `{domain}`
  - [x] 7.3 Add inline comments adjacent to each template documenting all required placeholder keys

- [x] 8. Write unit tests for config.py
  - [x] 8.1 Create `test_config.py` using the standard `unittest` or `pytest` framework
  - [x] 8.2 Test that all three domain constants are non-empty strings and members of `SUPPORTED_DOMAINS`
  - [x] 8.3 Test that `SUPPORTED_DOMAINS` contains exactly the three domain constants
  - [x] 8.4 Test that `RISK_ESCALATION_KEYWORDS` has exactly four keys
  - [x] 8.5 Test that `REQUEST_TYPE_PATTERNS` has exactly three keys
  - [x] 8.6 Test that `PRODUCT_AREA_MAPPINGS` has exactly three keys matching `SUPPORTED_DOMAINS`
  - [x] 8.7 Test that `CONFIDENCE_MIN == 0.6`, `CONFIDENCE_HIGH == 0.8`, and `CONFIDENCE_MIN < CONFIDENCE_HIGH`
  - [x] 8.8 Test that both confidence thresholds are within `[0.0, 1.0]`
  - [x] 8.9 Test that `TEMPLATE_RESPONSES` contains `"escalation"` and `"out_of_scope"` keys with non-empty string values
  - [x] 8.10 Test that formatting each template with its documented placeholder keys does not raise an exception
  - [x] 8.11 Test that `classify_request_type` returns `"product_issue"` when given a ticket text with no matching patterns

- [x] 9. Write property-based tests for config.py
  - [x] 9.1 Install `hypothesis` as a dev dependency and create `test_config_properties.py`
  - [x] 9.2 Write a property test (Property 2): for any category key in `RISK_ESCALATION_KEYWORDS`, the keyword list is non-empty — **Feature: support-ticket-triage-config, Property 2: All keyword lists are non-empty**
  - [x] 9.3 Write a property test (Property 3): for any keyword in any risk category, a ticket text containing that keyword causes the category to be detected — **Feature: support-ticket-triage-config, Property 3: Keyword detection is comprehensive**
  - [x] 9.4 Write a property test (Property 4): for any non-empty string input, `classify_request_type` returns a key present in `REQUEST_TYPE_PATTERNS` — **Feature: support-ticket-triage-config, Property 4: Request type classification always returns a valid key**
  - [x] 9.5 Write a property test (Property 5): for any non-empty string and any valid domain, `detect_product_area` returns a member of `PRODUCT_AREA_MAPPINGS[domain]` — **Feature: support-ticket-triage-config, Property 5: Product area detection always returns a valid area**
  - [x] 9.6 Write a property test (Property 6): for any valid placeholder dictionary, formatting each template string does not raise — **Feature: support-ticket-triage-config, Property 6: Template formatting never raises on valid placeholders**
  - [x] 9.7 Write a property test (Property 7): for any request type key, the pattern list is non-empty — **Feature: support-ticket-triage-config, Property 7: All pattern lists are non-empty**
  - [x] 9.8 Write a property test (Property 8): for any domain in `SUPPORTED_DOMAINS`, `PRODUCT_AREA_MAPPINGS[domain]` is a non-empty list — **Feature: support-ticket-triage-config, Property 8: All product area lists are non-empty**

- [x] 10. Verify and finalize
  - [x] 10.1 Run all unit tests and confirm they pass
  - [x] 10.2 Run all property-based tests and confirm they pass
  - [x] 10.3 Verify `config.py` is importable with no errors or warnings
  - [x] 10.4 Review all inline comments for clarity and completeness
