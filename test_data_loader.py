"""
test_data_loader.py — Unit tests for data_loader.py

Covers:
  Section 2: CSVValidator tests (2.1 – 2.7)
  Section 3: TicketRecord tests (3.1 – 3.5)
  Section 4: DataLoader tests  (4.1 – 4.9)
  Section 5: Utility function tests (5.1 – 5.5)
"""

import csv
import os
import pytest
from pathlib import Path

import config
from data_loader import (
    CSVValidator,
    DataLoader,
    TicketRecord,
    CSVParseError,
    DataValidationError,
    ConfigurationError,
    load_tickets,
    normalize_company,
    sanitize_ticket_text,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_csv(tmp_path: Path, rows: list[dict], filename: str = "tickets.csv") -> Path:
    """Helper: write a list-of-dicts to a CSV file and return its path."""
    if not rows:
        raise ValueError("rows must be non-empty to infer fieldnames")
    path = tmp_path / filename
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def valid_config():
    """Return the imported config module."""
    return config


@pytest.fixture
def sample_csv_path(tmp_path):
    """Temporary CSV with 5 valid tickets across all three domains."""
    rows = [
        {"Issue": "Assessment not loading", "Subject": "Assessment bug", "Company": "hackerrank"},
        {"Issue": "API rate limit exceeded", "Subject": "Rate limit", "Company": "claude"},
        {"Issue": "Transaction declined", "Subject": "Payment issue", "Company": "visa"},
        {"Issue": "Billing question", "Subject": "Invoice", "Company": "hackerrank"},
        {"Issue": "Model response quality", "Subject": "Model behavior", "Company": "claude"},
    ]
    return _write_csv(tmp_path, rows)


# ---------------------------------------------------------------------------
# Section 2: CSVValidator Tests
# ---------------------------------------------------------------------------


class TestCSVValidator:
    """Tests for CSVValidator structural and row-level validation."""

    def test_validator_valid_header(self, valid_config):
        """2.1 — Validator accepts a header containing all required columns."""
        validator = CSVValidator(valid_config)
        # Should not raise
        validator.validate_header(["Issue", "Subject", "Company"])

    def test_validator_missing_column(self, valid_config):
        """2.2 — Validator raises CSVParseError when 'Issue' column is absent."""
        validator = CSVValidator(valid_config)
        with pytest.raises(CSVParseError, match="Issue"):
            validator.validate_header(["Subject", "Company"])

    def test_validator_extra_columns(self, valid_config):
        """2.3 — Validator accepts headers with extra columns beyond the required set."""
        validator = CSVValidator(valid_config)
        # Extra columns like 'Response', 'Status' should be silently accepted
        validator.validate_header(["Issue", "Subject", "Company", "Response", "Status"])

    def test_validator_valid_company(self, valid_config):
        """2.4 — Validator accepts each of the three supported domain values."""
        validator = CSVValidator(valid_config)
        assert validator.validate_company("hackerrank") == "hackerrank"
        assert validator.validate_company("claude") == "claude"
        assert validator.validate_company("visa") == "visa"
        # Case-insensitive
        assert validator.validate_company("HackerRank") == "hackerrank"
        assert validator.validate_company("VISA") == "visa"

    def test_validator_invalid_company(self, valid_config):
        """2.5 — Validator raises DataValidationError for an unsupported company."""
        validator = CSVValidator(valid_config)
        with pytest.raises(DataValidationError, match="not a supported domain"):
            validator.validate_company("InvalidCorp")

    def test_validator_empty_issue(self, valid_config):
        """2.6 — Validator raises DataValidationError when 'Issue' is empty."""
        validator = CSVValidator(valid_config)
        row = {"Issue": "   ", "Subject": "Some subject", "Company": ""}
        with pytest.raises(DataValidationError, match="Issue"):
            validator.validate_row(1, row, ["Issue", "Subject", "Company"])

    def test_validator_none_company(self, valid_config):
        """2.7 — Validator accepts None, empty string, and 'None' for Company."""
        validator = CSVValidator(valid_config)
        assert validator.validate_company("") is None
        assert validator.validate_company("None") is None
        assert validator.validate_company(None) is None


# ---------------------------------------------------------------------------
# Section 3: TicketRecord Tests
# ---------------------------------------------------------------------------


class TestTicketRecord:
    """Tests for the TicketRecord dataclass."""

    def test_ticket_creation(self):
        """3.1 — TicketRecord is created with correct field values."""
        ticket = TicketRecord(id=1, issue="Test issue")
        assert ticket.id == 1
        assert ticket.issue == "Test issue"
        assert ticket.subject == ""
        assert ticket.company is None

    def test_ticket_negative_id(self):
        """3.2 — TicketRecord raises ValueError for a negative id."""
        with pytest.raises(ValueError, match="positive integer"):
            TicketRecord(id=-1, issue="Some issue")

    def test_ticket_zero_id(self):
        """3.2 (edge) — TicketRecord raises ValueError for id=0."""
        with pytest.raises(ValueError, match="positive integer"):
            TicketRecord(id=0, issue="Some issue")

    def test_ticket_empty_issue(self):
        """3.3 — TicketRecord raises ValueError for an empty issue string."""
        with pytest.raises(ValueError, match="non-empty string"):
            TicketRecord(id=1, issue="")

    def test_ticket_whitespace_only_issue(self):
        """3.3 (edge) — TicketRecord raises ValueError for whitespace-only issue."""
        with pytest.raises(ValueError, match="non-empty string"):
            TicketRecord(id=1, issue="   ")

    def test_ticket_clean(self):
        """3.4 — clean() returns a new record with normalised whitespace."""
        ticket = TicketRecord(id=1, issue="  hello   world  ", subject="  sub  ")
        cleaned = ticket.clean()
        assert cleaned.issue == "hello world"
        assert cleaned.subject == "sub"
        assert cleaned.id == 1
        assert cleaned.company is None

    def test_ticket_to_dict(self):
        """3.5 — to_dict() returns a dict with all four expected keys."""
        ticket = TicketRecord(id=2, issue="API broken", subject="API", company="claude")
        d = ticket.to_dict()
        assert d == {"id": 2, "issue": "API broken", "subject": "API", "company": "claude"}
        assert set(d.keys()) == {"id", "issue", "subject", "company"}


# ---------------------------------------------------------------------------
# Section 4: DataLoader Tests
# ---------------------------------------------------------------------------


class TestDataLoader:
    """Tests for the DataLoader class."""

    def test_loader_init_file_not_found(self):
        """4.1 — DataLoader raises ConfigurationError for a non-existent file."""
        with pytest.raises(ConfigurationError, match="not found"):
            DataLoader("/nonexistent/path/tickets.csv")

    def test_loader_init_valid_file(self, sample_csv_path):
        """4.2 — DataLoader initialises successfully with a valid CSV file."""
        loader = DataLoader(sample_csv_path)
        assert loader.csv_file_path == sample_csv_path
        assert loader.tickets == []
        assert loader.total_rows == 0

    def test_load_valid_csv(self, sample_csv_path):
        """4.3 — load() returns 5 TicketRecord objects from a 5-row CSV."""
        loader = DataLoader(sample_csv_path)
        tickets = loader.load()
        assert len(tickets) == 5
        assert all(isinstance(t, TicketRecord) for t in tickets)

    def test_load_csv_with_validation_errors_strict_false(self, tmp_path):
        """4.4 — strict=False: 3 valid + 2 invalid rows → 3 tickets, 2 errors."""
        rows = [
            {"Issue": "Valid issue 1", "Subject": "S1", "Company": "hackerrank"},
            {"Issue": "",              "Subject": "S2", "Company": "claude"},      # empty issue
            {"Issue": "Valid issue 3", "Subject": "S3", "Company": "visa"},
            {"Issue": "Valid issue 4", "Subject": "S4", "Company": "hackerrank"},
            {"Issue": "   ",           "Subject": "S5", "Company": ""},            # whitespace issue
        ]
        path = _write_csv(tmp_path, rows)
        loader = DataLoader(path)
        tickets = loader.load(strict=False)
        assert len(tickets) == 3
        assert len(loader.errors) == 2

    def test_load_csv_with_validation_errors_strict_true(self, tmp_path):
        """4.5 — strict=True: raises DataValidationError on the first bad row."""
        rows = [
            {"Issue": "Valid issue", "Subject": "S1", "Company": "hackerrank"},
            {"Issue": "",            "Subject": "S2", "Company": "claude"},  # bad row
        ]
        path = _write_csv(tmp_path, rows)
        loader = DataLoader(path)
        with pytest.raises(DataValidationError):
            loader.load(strict=True)

    def test_get_statistics(self, tmp_path):
        """4.6 — get_statistics() returns correct counts and 80% success rate."""
        rows = [
            {"Issue": "Issue 1", "Subject": "S1", "Company": "hackerrank"},
            {"Issue": "Issue 2", "Subject": "S2", "Company": "claude"},
            {"Issue": "Issue 3", "Subject": "S3", "Company": "visa"},
            {"Issue": "Issue 4", "Subject": "S4", "Company": "hackerrank"},
            {"Issue": "",        "Subject": "S5", "Company": "claude"},  # invalid
        ]
        path = _write_csv(tmp_path, rows)
        loader = DataLoader(path)
        loader.load(strict=False)
        stats = loader.get_statistics()
        assert stats["total_rows_read"] == 5
        assert stats["valid_tickets_loaded"] == 4
        assert stats["error_count"] == 1
        assert stats["success_rate"] == pytest.approx(80.0)

    def test_filter_by_company(self, tmp_path):
        """4.7 — filter_by_company() returns only matching tickets."""
        rows = [
            {"Issue": "HR issue 1",  "Subject": "", "Company": "hackerrank"},
            {"Issue": "HR issue 2",  "Subject": "", "Company": "hackerrank"},
            {"Issue": "Claude issue","Subject": "", "Company": "claude"},
            {"Issue": "No company",  "Subject": "", "Company": ""},
        ]
        path = _write_csv(tmp_path, rows)
        loader = DataLoader(path)
        loader.load()

        hr_tickets = loader.filter_by_company("hackerrank")
        assert len(hr_tickets) == 2
        assert all(t.company == "hackerrank" for t in hr_tickets)

        none_tickets = loader.filter_by_company(None)
        assert len(none_tickets) == 1
        assert none_tickets[0].company is None

    def test_get_ticket_by_id(self, sample_csv_path):
        """4.8 — get_ticket_by_id() returns the correct ticket or None."""
        loader = DataLoader(sample_csv_path)
        loader.load()
        ticket = loader.get_ticket_by_id(1)
        assert ticket is not None
        assert ticket.id == 1

        missing = loader.get_ticket_by_id(999)
        assert missing is None

    def test_to_dict_list(self, tmp_path):
        """4.9 — to_dict_list() returns a list of dicts with the correct keys."""
        rows = [
            {"Issue": "Issue A", "Subject": "SA", "Company": "hackerrank"},
            {"Issue": "Issue B", "Subject": "SB", "Company": "claude"},
            {"Issue": "Issue C", "Subject": "SC", "Company": "visa"},
        ]
        path = _write_csv(tmp_path, rows)
        loader = DataLoader(path)
        loader.load()
        result = loader.to_dict_list()
        assert len(result) == 3
        for d in result:
            assert set(d.keys()) == {"id", "issue", "subject", "company"}


# ---------------------------------------------------------------------------
# Section 5: Utility Function Tests
# ---------------------------------------------------------------------------


class TestUtilityFunctions:
    """Tests for module-level utility functions."""

    def test_load_tickets_convenience(self, sample_csv_path):
        """5.1 — load_tickets() returns the same result as DataLoader().load()."""
        tickets = load_tickets(sample_csv_path)
        assert isinstance(tickets, list)
        assert len(tickets) == 5
        assert all(isinstance(t, TicketRecord) for t in tickets)

    def test_normalize_company_valid(self):
        """5.2 — normalize_company() returns canonical domain for valid inputs."""
        assert normalize_company("HackerRank") == "hackerrank"
        assert normalize_company("claude") == "claude"
        assert normalize_company("VISA") == "visa"
        assert normalize_company("HACKERRANK") == "hackerrank"
        assert normalize_company("Claude") == "claude"

    def test_normalize_company_invalid(self):
        """5.3 — normalize_company() returns None for unrecognised company names."""
        assert normalize_company("InvalidCorp") is None
        assert normalize_company("") is None
        assert normalize_company("   ") is None

    def test_normalize_company_none(self):
        """5.4 — normalize_company() returns None for None and the string 'None'."""
        assert normalize_company("None") is None
        assert normalize_company(None) is None

    def test_sanitize_ticket_text_whitespace(self):
        """5.5 — sanitize_ticket_text() collapses internal whitespace."""
        assert sanitize_ticket_text("  hello   world  ") == "hello world"

    def test_sanitize_ticket_text_newlines(self):
        """5.5 — sanitize_ticket_text() normalises line endings."""
        result = sanitize_ticket_text("line1\r\nline2\rline3")
        assert "\r" not in result
        assert result == "line1\nline2\nline3"

    def test_sanitize_ticket_text_empty(self):
        """5.5 (edge) — sanitize_ticket_text() handles empty string."""
        assert sanitize_ticket_text("") == ""

    def test_sanitize_ticket_text_tabs(self):
        """5.5 (edge) — sanitize_ticket_text() collapses tabs to single space."""
        assert sanitize_ticket_text("col1\t\tcol2") == "col1 col2"
