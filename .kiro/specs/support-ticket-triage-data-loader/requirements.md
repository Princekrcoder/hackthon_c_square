# Requirements: Support Ticket Triage Data Loader

## Introduction

This document defines the functional and non-functional requirements for the `data_loader.py` module. The module provides production-grade CSV ingestion and validation for support ticket data, integrating with the existing `config.py` configuration module.

---

## Requirements

### Requirement 1: Module Structure and Imports

**User Story**: As a developer integrating the data loader, I want the module to be importable without side effects and to expose a clean public API, so that I can use it in any Python application without unexpected behaviour.

#### Acceptance Criteria

1.1 The module MUST include a docstring explaining its purpose, responsibilities, and typical usage.

1.2 The module MUST import only Python standard library modules (`csv`, `os`, `sys`, `pathlib`, `logging`, `re`, `dataclasses`, `typing`) and the local `config` module.

1.3 The module MUST import the following constants from `config`: `SUPPORTED_DOMAINS`, `CONFIDENCE_MIN`, `CONFIDENCE_HIGH`, `DOMAIN_HACKERRANK`, `DOMAIN_CLAUDE`, `DOMAIN_VISA`, `RISK_ESCALATION_KEYWORDS`, `REQUEST_TYPE_PATTERNS`, `PRODUCT_AREA_MAPPINGS`, `TEMPLATE_RESPONSES`.

1.4 Importing the module MUST NOT produce any side effects beyond configuring the logger and defining module-level names.

---

### Requirement 2: Logging Configuration

**User Story**: As an operator running the data loader in production, I want structured log output with timestamps and log levels, so that I can diagnose loading issues from application logs.

#### Acceptance Criteria

2.1 The module MUST create a logger named `__name__` using `logging.getLogger(__name__)`.

2.2 The logger MUST be set to `INFO` level.

2.3 The module MUST attach a `StreamHandler` (console) with the format `[%(asctime)s] [%(levelname)s] %(message)s`.

2.4 The handler MUST only be added if no handlers are already configured on the logger, to prevent duplicate output when the module is imported multiple times.

---

### Requirement 3: Custom Exception Hierarchy

**User Story**: As a caller of the data loader, I want specific exception types for different failure modes, so that I can handle file-not-found, parse errors, and validation errors independently.

#### Acceptance Criteria

3.1 The module MUST define `DataLoadError(Exception)` as the base exception for all module-level failures.

3.2 The module MUST define `CSVParseError(DataLoadError)` for structural CSV failures (e.g., missing required columns, empty file).

3.3 The module MUST define `DataValidationError(DataLoadError)` for row-level data rule violations.

3.4 The module MUST define `ConfigurationError(DataLoadError)` for loader misconfiguration (e.g., file not found).

3.5 All four exception classes MUST be importable from the module's public namespace.

---

### Requirement 4: TicketRecord Dataclass

**User Story**: As a downstream consumer of loaded tickets, I want a typed, validated data object for each ticket, so that I can access fields with confidence that they meet invariants.

#### Acceptance Criteria

4.1 The module MUST define a `@dataclass` class `TicketRecord` with fields: `id: int`, `issue: str`, `subject: str = ""`, `company: Optional[str] = None`.

4.2 `TicketRecord.__post_init__` MUST raise `ValueError` if `id` is not a positive integer (i.e., `id <= 0` or not an `int`).

4.3 `TicketRecord.__post_init__` MUST raise `ValueError` if `issue` is empty or whitespace-only.

4.4 `TicketRecord.clean()` MUST return a new `TicketRecord` with all text fields whitespace-normalised using `sanitize_ticket_text()`, leaving `id` and `company` unchanged.

4.5 `TicketRecord.to_dict()` MUST return a plain `dict` with exactly the keys `id`, `issue`, `subject`, `company` and their corresponding values.

4.6 `TicketRecord.__repr__()` MUST return a human-readable string including `id`, `company`, and a truncated preview of `issue` (max 50 characters).

---

### Requirement 5: CSVValidator — Header Validation

**User Story**: As a data loader, I want to detect missing required columns immediately when opening a CSV, so that I fail fast with a clear error before processing any rows.

#### Acceptance Criteria

5.1 `CSVValidator.validate_header(fieldnames)` MUST raise `CSVParseError` if `fieldnames` is `None` (empty file with no header row).

5.2 `validate_header` MUST raise `CSVParseError` listing the missing column names if any of `Issue`, `Subject`, or `Company` are absent from `fieldnames`.

5.3 `validate_header` MUST accept headers that contain extra columns beyond the required set without raising.

5.4 `validate_header` MUST log an `INFO` message confirming successful header validation.

---

### Requirement 6: CSVValidator — Row Validation

**User Story**: As a data loader, I want each row validated against field-level rules before creating a TicketRecord, so that only clean, conformant data enters the system.

#### Acceptance Criteria

6.1 `CSVValidator.validate_row(row_num, row_data, fieldnames)` MUST raise `DataValidationError` if the `Issue` field is empty or whitespace-only after stripping.

6.2 `validate_row` MUST strip leading/trailing whitespace from the `Issue` field in the returned cleaned dict.

6.3 `validate_row` MUST strip leading/trailing whitespace from the `Subject` field; a missing or `None` subject MUST be normalised to an empty string.

6.4 `validate_row` MUST delegate `Company` validation to `validate_company()` and store the result in the returned cleaned dict.

6.5 `validate_row` MUST return a cleaned copy of `row_data` (not mutate the original).

---

### Requirement 7: CSVValidator — Company Validation

**User Story**: As a data loader, I want company values normalised to canonical domain identifiers, so that downstream consumers receive consistent, lowercase domain strings.

#### Acceptance Criteria

7.1 `CSVValidator.validate_company(company_value)` MUST return `None` for `None` input.

7.2 `validate_company` MUST return `None` for an empty string or the literal string `"None"` (case-insensitive).

7.3 `validate_company` MUST perform a case-insensitive match against `SUPPORTED_DOMAINS` and return the canonical lowercase domain string on a match (e.g., `"HackerRank"` → `"hackerrank"`).

7.4 `validate_company` MUST raise `DataValidationError` if the value is non-empty, non-`"None"`, and does not match any supported domain.

---

### Requirement 8: DataLoader — Initialisation

**User Story**: As a caller, I want the DataLoader to verify the CSV file exists at construction time, so that I receive a clear error immediately rather than at load time.

#### Acceptance Criteria

8.1 `DataLoader.__init__(csv_file_path, cfg=None)` MUST raise `ConfigurationError` if `csv_file_path` does not exist on disk.

8.2 `DataLoader.__init__` MUST resolve the path using `pathlib.Path` and store it as `self.csv_file_path`.

8.3 `DataLoader.__init__` MUST initialise `self.tickets`, `self.errors` as empty lists and `self.total_rows`, `self.valid_rows` as zero.

8.4 `DataLoader.__init__` MUST accept an optional `cfg` parameter (configuration module); if `None`, it MUST default to the imported `config` module.

8.5 `DataLoader.__init__` MUST log an `INFO` message confirming successful initialisation.

---

### Requirement 9: DataLoader — Load

**User Story**: As a caller, I want to load all valid tickets from a CSV file with configurable error tolerance, so that I can choose between strict validation (fail fast) and lenient loading (skip bad rows).

#### Acceptance Criteria

9.1 `DataLoader.load(strict=False)` MUST reset `self.tickets`, `self.errors`, `self.total_rows`, and `self.valid_rows` at the start of each call, so that `load()` is idempotent and can be called multiple times.

9.2 `load` MUST open the CSV file with UTF-8 encoding and use `csv.DictReader` for parsing.

9.3 `load` MUST call `CSVValidator.validate_header()` before processing any rows; a `CSVParseError` MUST propagate to the caller regardless of `strict` mode.

9.4 For each data row, `load` MUST call `CSVValidator.validate_row()` and, on success, create a `TicketRecord` with `id` equal to the 1-based row number.

9.5 When `strict=False` and a row fails validation, `load` MUST log a warning, append an error detail dict `{row, error, raw_data}` to `self.errors`, and continue processing remaining rows.

9.6 When `strict=True` and a row fails validation, `load` MUST immediately raise `DataValidationError` without returning partial results.

9.7 `load` MUST return the list of successfully loaded `TicketRecord` objects.

9.8 After loading, `self.total_rows` MUST equal the total number of data rows in the CSV, and `self.valid_rows` MUST equal `len(self.tickets)`.

---

### Requirement 10: DataLoader — Statistics

**User Story**: As an operator, I want a summary of the most recent load operation, so that I can monitor data quality and identify problematic CSV files.

#### Acceptance Criteria

10.1 `DataLoader.get_statistics()` MUST return a dict with exactly the keys: `total_rows_read`, `valid_tickets_loaded`, `error_count`, `success_rate`, `errors`.

10.2 `total_rows_read` MUST equal `self.total_rows`.

10.3 `valid_tickets_loaded` MUST equal `self.valid_rows`.

10.4 `error_count` MUST equal `len(self.errors)`.

10.5 `success_rate` MUST equal `(valid_tickets_loaded / max(1, total_rows_read)) * 100`, expressed as a float in the range `[0.0, 100.0]`.

10.6 `errors` MUST be the list of error detail dicts accumulated during the most recent `load()` call.

---

### Requirement 11: DataLoader — Filtering and Lookup

**User Story**: As a downstream consumer, I want to query loaded tickets by company or by ID, so that I can route tickets to the correct domain handler without re-reading the CSV.

#### Acceptance Criteria

11.1 `DataLoader.filter_by_company(company)` MUST return a list of all loaded `TicketRecord` objects whose `company` field equals the given value (including `None`).

11.2 `filter_by_company` MUST return an empty list if no tickets match; it MUST NOT raise.

11.3 `DataLoader.get_ticket_by_id(ticket_id)` MUST return the first `TicketRecord` whose `id` equals `ticket_id`, or `None` if not found.

11.4 `DataLoader.to_dict_list()` MUST return a list of dicts produced by calling `to_dict()` on each loaded ticket, in load order.

---

### Requirement 12: Utility Functions

**User Story**: As a developer, I want module-level convenience functions for common operations, so that I can load tickets, normalise company names, and clean text without instantiating classes directly.

#### Acceptance Criteria

12.1 `load_tickets(csv_path, cfg=None, strict=False)` MUST create a `DataLoader`, call `load()`, and return the resulting list of `TicketRecord` objects.

12.2 `normalize_company(company_str)` MUST return `None` for `None`, empty string, or the literal `"None"`.

12.3 `normalize_company` MUST return the canonical lowercase domain string for a case-insensitive match against `SUPPORTED_DOMAINS`.

12.4 `normalize_company` MUST return `None` for unrecognised values without raising an exception.

12.5 `normalize_company` MUST be idempotent: `normalize_company(normalize_company(x)) == normalize_company(x)` for all inputs.

12.6 `sanitize_ticket_text(text)` MUST strip leading/trailing whitespace from the input.

12.7 `sanitize_ticket_text` MUST normalise line endings to `\n` (converting `\r\n` and `\r`).

12.8 `sanitize_ticket_text` MUST collapse runs of horizontal whitespace (spaces and tabs) within each line to a single space.

12.9 `sanitize_ticket_text` MUST return an empty string for empty or falsy input.

12.10 `sanitize_ticket_text` MUST return a string whose length is less than or equal to the length of the input (never increases length).

---

### Requirement 13: Test Coverage — Unit Tests

**User Story**: As a developer maintaining the module, I want a comprehensive unit test suite, so that regressions are caught immediately and the module's contract is clearly documented through tests.

#### Acceptance Criteria

13.1 The unit test file `test_data_loader.py` MUST contain at least 16 test cases using `pytest`.

13.2 Tests MUST cover `CSVValidator`: valid header, missing column, extra columns, valid company (all three domains + case variants), invalid company, empty issue, None/empty/`"None"` company.

13.3 Tests MUST cover `TicketRecord`: creation with defaults, negative id, zero id, empty issue, whitespace-only issue, `clean()`, `to_dict()`.

13.4 Tests MUST cover `DataLoader`: file not found, valid init, load valid CSV, load with errors strict=False, load with errors strict=True, `get_statistics()`, `filter_by_company()`, `get_ticket_by_id()`, `to_dict_list()`.

13.5 Tests MUST cover utility functions: `load_tickets()` convenience, `normalize_company()` valid/invalid/None, `sanitize_ticket_text()` whitespace/newlines/empty/tabs.

13.6 All 16+ unit tests MUST pass when run with `pytest`.

---

### Requirement 14: Test Coverage — Property-Based Tests

**User Story**: As a developer, I want property-based tests that verify universal invariants across a wide range of generated inputs, so that edge cases not covered by example-based tests are also validated.

#### Acceptance Criteria

14.1 The property test file `test_data_loader_properties.py` MUST contain exactly 5 property-based tests using the `hypothesis` library.

14.2 Property 1 MUST verify that `TicketRecord → to_dict() → reconstruct` preserves all field values for any valid `(id, issue)` pair.

14.3 Property 2 MUST verify that `len(sanitize_ticket_text(s)) <= len(s)` for any string `s`.

14.4 Property 3 MUST verify that `normalize_company` is idempotent for any input.

14.5 Property 4 MUST verify that loader statistics satisfy: `valid <= total`, `errors == total - valid`, `0 <= success_rate <= 100` for any combination of valid and invalid rows.

14.6 Property 5 MUST verify that `filter_by_company()` is non-generative: filtered count ≤ total, all filtered tickets match the condition, and filtered tickets are a subset of loaded tickets by id.

14.7 All 5 property tests MUST pass when run with `pytest`.
