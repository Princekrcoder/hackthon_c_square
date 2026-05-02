# Tasks: Support Ticket Triage Data Loader

## Overview

Implementation tasks for the `data_loader.py` module and its test suite. Tasks are ordered by dependency: core data structures first, then validation, then the loader orchestrator, then utilities, then tests.

---

## Task List

- [x] 1. Implement module scaffold and logging configuration
  - [x] 1.1 Write module docstring covering purpose, responsibilities, and typical usage
  - [x] 1.2 Add all standard library imports: `csv`, `os`, `sys`, `re`, `logging`, `pathlib`, `dataclasses`, `typing`
  - [x] 1.3 Import all required constants from `config`: `SUPPORTED_DOMAINS`, `CONFIDENCE_MIN`, `CONFIDENCE_HIGH`, `DOMAIN_HACKERRANK`, `DOMAIN_CLAUDE`, `DOMAIN_VISA`, `RISK_ESCALATION_KEYWORDS`, `REQUEST_TYPE_PATTERNS`, `PRODUCT_AREA_MAPPINGS`, `TEMPLATE_RESPONSES`
  - [x] 1.4 Create logger with `logging.getLogger(__name__)`, set level to `INFO`
  - [x] 1.5 Attach `StreamHandler` with format `[%(asctime)s] [%(levelname)s] %(message)s`, guarded by `if not logger.handlers`

- [x] 2. Define custom exception hierarchy
  - [x] 2.1 Define `DataLoadError(Exception)` as the base exception class
  - [x] 2.2 Define `CSVParseError(DataLoadError)` for structural CSV failures
  - [x] 2.3 Define `DataValidationError(DataLoadError)` for row-level validation failures
  - [x] 2.4 Define `ConfigurationError(DataLoadError)` for loader misconfiguration

- [x] 3. Implement `TicketRecord` dataclass
  - [x] 3.1 Define `@dataclass TicketRecord` with fields: `id: int`, `issue: str`, `subject: str = ""`, `company: Optional[str] = None`
  - [x] 3.2 Implement `__post_init__` raising `ValueError` for non-positive `id` and empty/whitespace `issue`
  - [x] 3.3 Implement `clean()` returning a new `TicketRecord` with all text fields passed through `sanitize_ticket_text()`
  - [x] 3.4 Implement `to_dict()` returning `{"id": ..., "issue": ..., "subject": ..., "company": ...}`
  - [x] 3.5 Implement `__repr__()` showing `id`, `company`, and a ≤50-char preview of `issue`

- [x] 4. Implement `CSVValidator` class
  - [x] 4.1 Define `CSVValidator.__init__(self, cfg=None)` storing config module (defaulting to imported `config`)
  - [x] 4.2 Implement `validate_header(fieldnames)`: raise `CSVParseError` for `None` fieldnames or missing required columns; log `INFO` on success
  - [x] 4.3 Implement `validate_row(row_num, row_data, fieldnames)`: validate `Issue` non-empty, strip `Subject`, delegate `Company` to `validate_company()`; return cleaned dict
  - [x] 4.4 Implement `validate_company(company_value)`: return `None` for `None`/empty/`"None"`; case-insensitive match against `SUPPORTED_DOMAINS`; raise `DataValidationError` for unrecognised values

- [x] 5. Implement `DataLoader` class
  - [x] 5.1 Implement `__init__(csv_file_path, cfg=None)`: resolve path with `pathlib.Path`, raise `ConfigurationError` if not found, initialise state attributes, log `INFO`
  - [x] 5.2 Implement `load(strict=False)`: reset state, open CSV with UTF-8 encoding, validate header, iterate rows, create `TicketRecord` per valid row, handle errors per `strict` flag, return ticket list
  - [x] 5.3 Implement `get_statistics()`: return dict with `total_rows_read`, `valid_tickets_loaded`, `error_count`, `success_rate`, `errors`
  - [x] 5.4 Implement `filter_by_company(company)`: return list of tickets matching `company` (including `None`)
  - [x] 5.5 Implement `get_ticket_by_id(ticket_id)`: return matching `TicketRecord` or `None`
  - [x] 5.6 Implement `to_dict_list()`: return `[t.to_dict() for t in self.tickets]`

- [x] 6. Implement module-level utility functions
  - [x] 6.1 Implement `load_tickets(csv_path, cfg=None, strict=False)`: create `DataLoader`, call `load()`, return result
  - [x] 6.2 Implement `normalize_company(company_str)`: return `None` for `None`/empty/`"None"`; case-insensitive match against `SUPPORTED_DOMAINS`; return `None` (not raise) for unrecognised values
  - [x] 6.3 Implement `sanitize_ticket_text(text)`: strip outer whitespace, normalise line endings to `\n`, collapse internal horizontal whitespace per line

- [x] 7. Write unit tests (`test_data_loader.py`)
  - [x] 7.1 Write `TestCSVValidator` tests: valid header (2.1), missing column (2.2), extra columns (2.3), valid company all domains + case variants (2.4), invalid company (2.5), empty issue (2.6), None/empty/`"None"` company (2.7)
  - [x] 7.2 Write `TestTicketRecord` tests: creation with defaults (3.1), negative id (3.2), zero id (3.2 edge), empty issue (3.3), whitespace-only issue (3.3 edge), `clean()` (3.4), `to_dict()` (3.5)
  - [x] 7.3 Write `TestDataLoader` tests: file not found (4.1), valid init (4.2), load valid CSV (4.3), load with errors strict=False (4.4), load with errors strict=True (4.5), `get_statistics()` (4.6), `filter_by_company()` (4.7), `get_ticket_by_id()` (4.8), `to_dict_list()` (4.9)
  - [x] 7.4 Write `TestUtilityFunctions` tests: `load_tickets()` convenience (5.1), `normalize_company()` valid (5.2), invalid (5.3), None (5.4), `sanitize_ticket_text()` whitespace (5.5), newlines (5.5), empty (5.5 edge), tabs (5.5 edge)
  - [x] 7.5 Run `pytest test_data_loader.py` and confirm all 16+ tests pass

- [x] 8. Write property-based tests (`test_data_loader_properties.py`)
  - [x] 8.1 Write Property 1: ticket round-trip serialization — `TicketRecord → to_dict() → reconstruct` preserves all fields (300 examples)
  - [x] 8.2 Write Property 2: sanitization never increases length — `len(sanitize_ticket_text(s)) <= len(s)` for any string (500 examples)
  - [x] 8.3 Write Property 3: company normalization is idempotent — `normalize_company(normalize_company(x)) == normalize_company(x)` (300 examples)
  - [x] 8.4 Write Property 4: statistics invariants — `valid <= total`, `errors == total - valid`, `0 <= success_rate <= 100` for any valid/invalid row combination (100 examples)
  - [x] 8.5 Write Property 5: filtering is non-generative — filtered count ≤ total, all filtered match condition, filtered are subset of loaded by id (100 examples)
  - [x] 8.6 Run `pytest test_data_loader_properties.py` and confirm all 5 property tests pass

- [x] 9. Final verification
  - [x] 9.1 Confirm `data_loader.py` is importable without errors: `python -c "import data_loader"`
  - [x] 9.2 Run full test suite `pytest test_data_loader.py test_data_loader_properties.py -v` and confirm all tests pass
  - [x] 9.3 Verify module integrates with `config.py` by running `load_tickets("inputs/sample_support_tickets.csv")` and confirming tickets are returned
