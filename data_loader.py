"""
data_loader.py — Support Ticket CSV Data Loading Module

This module provides production-grade loading and validation of support ticket
data from CSV files. It integrates with config.py to validate company/domain
values against the configured supported domains.

Responsibilities:
- Parse CSV files containing support ticket records
- Validate CSV structure (required columns) and row-level data
- Normalize and clean field values (whitespace, company names)
- Expose a clean TicketRecord dataclass for downstream consumers
- Provide both a full DataLoader class and a convenience load_tickets() function

Typical usage:
    from data_loader import load_tickets

    tickets = load_tickets("inputs/sample_support_tickets.csv")
    for ticket in tickets:
        print(ticket.id, ticket.company, ticket.issue[:60])

Design principles:
- Fail fast on structural errors (missing columns, bad file path)
- Tolerate row-level errors by default (strict=False) — log and continue
- All public APIs are type-annotated
- No third-party runtime dependencies beyond the standard library
"""

# ---------------------------------------------------------------------------
# Section 1: Imports
# ---------------------------------------------------------------------------

import csv
import os
import sys
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import config
from config import (
    SUPPORTED_DOMAINS,
    CONFIDENCE_MIN,
    CONFIDENCE_HIGH,
    DOMAIN_HACKERRANK,
    DOMAIN_CLAUDE,
    DOMAIN_VISA,
    RISK_ESCALATION_KEYWORDS,
    REQUEST_TYPE_PATTERNS,
    PRODUCT_AREA_MAPPINGS,
    TEMPLATE_RESPONSES,
)

# ---------------------------------------------------------------------------
# Section 2: Logging Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add a handler if none are configured yet (avoids duplicate output when
# the module is imported multiple times or used inside a larger application).
if not logger.handlers:
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(logging.DEBUG)
    _formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    _console_handler.setFormatter(_formatter)
    logger.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# Section 3: Custom Exceptions
# ---------------------------------------------------------------------------


class DataLoadError(Exception):
    """Base exception for all data loading failures in this module."""


class CSVParseError(DataLoadError):
    """Raised when the CSV file cannot be parsed (e.g. missing required columns)."""


class DataValidationError(DataLoadError):
    """Raised when a row fails data validation rules."""


class ConfigurationError(DataLoadError):
    """Raised when the loader is misconfigured (e.g. file not found)."""


# ---------------------------------------------------------------------------
# Section 4: TicketRecord Dataclass
# ---------------------------------------------------------------------------


@dataclass
class TicketRecord:
    """Represents a single validated support ticket loaded from CSV.

    Attributes:
        id:      Positive integer row identifier (1-based).
        issue:   The full text of the support issue (non-empty).
        subject: Optional short subject line (may be empty string).
        company: Normalised domain identifier or None if unspecified.
    """

    id: int
    issue: str
    subject: str = ""
    company: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate field invariants immediately after construction.

        Raises:
            ValueError: If id is not a positive integer.
            ValueError: If issue is empty or whitespace-only.
        """
        if not isinstance(self.id, int) or self.id <= 0:
            raise ValueError(
                f"TicketRecord.id must be a positive integer, got {self.id!r}"
            )
        if not isinstance(self.issue, str) or not self.issue.strip():
            raise ValueError(
                f"TicketRecord.issue must be a non-empty string, got {self.issue!r}"
            )

    def clean(self) -> "TicketRecord":
        """Return a new TicketRecord with all text fields whitespace-normalised.

        Normalisation rules:
        - Strip leading/trailing whitespace
        - Collapse internal runs of whitespace to a single space
        - Normalise line endings to \\n

        Returns:
            A new TicketRecord with cleaned field values.
        """
        return TicketRecord(
            id=self.id,
            issue=sanitize_ticket_text(self.issue),
            subject=sanitize_ticket_text(self.subject),
            company=self.company,
        )

    def to_dict(self) -> dict:
        """Serialise this record to a plain dictionary.

        Returns:
            Dict with keys: id, issue, subject, company.
        """
        return {
            "id": self.id,
            "issue": self.issue,
            "subject": self.subject,
            "company": self.company,
        }

    def __repr__(self) -> str:
        """Human-readable representation for debugging."""
        company_str = self.company or "unspecified"
        issue_preview = self.issue[:50] + "..." if len(self.issue) > 50 else self.issue
        return (
            f"TicketRecord(id={self.id}, company={company_str!r}, "
            f"issue={issue_preview!r})"
        )


# ---------------------------------------------------------------------------
# Section 5: CSVValidator Class
# ---------------------------------------------------------------------------

# The three columns that every supported-ticket CSV must contain.
REQUIRED_COLUMNS = {"Issue", "Subject", "Company"}


class CSVValidator:
    """Validates CSV structure and individual row content.

    Validation is split into two levels:
    1. Structural — the header must contain all required columns.
    2. Row-level  — each row must satisfy field-level rules.
    """

    def __init__(self, cfg=None) -> None:
        """Initialise the validator.

        Args:
            cfg: Configuration module to use for domain lookups.
                 Defaults to the imported config module.
        """
        self.config = cfg if cfg is not None else config

    # ------------------------------------------------------------------
    # Method 1: validate_header
    # ------------------------------------------------------------------

    def validate_header(self, fieldnames: list) -> None:
        """Assert that the CSV header contains all required columns.

        Extra columns beyond the required set are silently accepted.

        Args:
            fieldnames: List of column names returned by csv.DictReader.

        Raises:
            CSVParseError: If any required column is absent.
        """
        if fieldnames is None:
            raise CSVParseError("CSV file appears to be empty — no header row found.")

        present = set(fieldnames)
        missing = REQUIRED_COLUMNS - present
        if missing:
            raise CSVParseError(
                f"CSV is missing required column(s): {sorted(missing)}. "
                f"Found columns: {sorted(present)}"
            )
        logger.info("Header validated: %s", list(fieldnames))

    # ------------------------------------------------------------------
    # Method 2: validate_row
    # ------------------------------------------------------------------

    def validate_row(self, row_num: int, row_data: dict, fieldnames: list) -> dict:
        """Validate and clean a single CSV row.

        Validation rules:
        - 'Issue' must be non-empty after stripping whitespace.
        - 'Subject' is optional (may be empty).
        - 'Company' must be None, empty, or a recognised domain.

        Args:
            row_num:    1-based row number (used in error messages).
            row_data:   Dict of {column: value} from csv.DictReader.
            fieldnames: Full list of column names (for context).

        Returns:
            A cleaned copy of row_data with normalised field values.

        Raises:
            DataValidationError: If any validation rule is violated.
        """
        cleaned = dict(row_data)

        # --- Validate 'Issue' ---
        issue_raw = row_data.get("Issue", "")
        if not issue_raw or not issue_raw.strip():
            raise DataValidationError(
                f"Row {row_num}: 'Issue' field is empty or whitespace-only."
            )
        cleaned["Issue"] = issue_raw.strip()

        # --- Validate 'Subject' (optional) ---
        subject_raw = row_data.get("Subject", "") or ""
        cleaned["Subject"] = subject_raw.strip()

        # --- Validate 'Company' ---
        company_raw = row_data.get("Company", "") or ""
        cleaned["Company"] = self.validate_company(company_raw)

        logger.debug("Row %d validated", row_num)
        return cleaned

    # ------------------------------------------------------------------
    # Method 3: validate_company
    # ------------------------------------------------------------------

    def validate_company(self, company_value: str) -> Optional[str]:
        """Normalise and validate a company value from the CSV.

        Logic:
        - Empty string or the literal string "None" → returns None.
        - Otherwise strips whitespace and performs a case-insensitive
          lookup against SUPPORTED_DOMAINS.
        - Returns the canonical lowercase domain string on match.
        - Raises DataValidationError if no match is found.

        Args:
            company_value: Raw string value from the 'Company' CSV column.

        Returns:
            Canonical domain string (e.g. "hackerrank") or None.

        Raises:
            DataValidationError: If the value is non-empty and not a
                recognised domain.
        """
        if company_value is None:
            return None

        stripped = company_value.strip()

        # Treat empty string or the literal word "None" as absent
        if stripped == "" or stripped.lower() == "none":
            return None

        # Case-insensitive match against supported domains
        lower = stripped.lower()
        for domain in self.config.SUPPORTED_DOMAINS:
            if lower == domain.lower():
                return domain  # return the canonical lowercase value

        raise DataValidationError(
            f"Company value {stripped!r} is not a supported domain. "
            f"Supported domains: {self.config.SUPPORTED_DOMAINS}"
        )


# ---------------------------------------------------------------------------
# Section 6: DataLoader Class
# ---------------------------------------------------------------------------


class DataLoader:
    """Load and validate support tickets from a CSV file.

    Attributes:
        csv_file_path: Resolved Path to the CSV file.
        tickets:       List of successfully loaded TicketRecord objects.
        total_rows:    Total number of data rows encountered.
        valid_rows:    Number of rows that passed validation.
        errors:        List of error detail dicts for failed rows.
    """

    def __init__(self, csv_file_path, cfg=None) -> None:
        """Initialise the loader and verify the file exists.

        Args:
            csv_file_path: Path-like or string path to the CSV file.
            cfg:           Configuration module (defaults to imported config).

        Raises:
            ConfigurationError: If csv_file_path does not exist.
        """
        path = Path(csv_file_path)
        if not path.exists():
            raise ConfigurationError(
                f"CSV file not found: {csv_file_path!r}. "
                "Please verify the path and try again."
            )

        self.csv_file_path: Path = path
        self.config = cfg if cfg is not None else config
        self.validator = CSVValidator(self.config)

        self.tickets: list[TicketRecord] = []
        self.total_rows: int = 0
        self.valid_rows: int = 0
        self.errors: list[dict] = []

        logger.info("DataLoader initialized for %s", self.csv_file_path)

    # ------------------------------------------------------------------
    # Method 1: load
    # ------------------------------------------------------------------

    def load(self, strict: bool = False) -> list[TicketRecord]:
        """Load and validate all tickets from the CSV file.

        Args:
            strict: If True, raise DataValidationError on the first bad row.
                    If False (default), log a warning and continue.

        Returns:
            List of validated TicketRecord objects.

        Raises:
            CSVParseError:       If the header is invalid.
            DataValidationError: If strict=True and any row fails validation.
        """
        # Reset state so load() can be called multiple times safely
        self.tickets = []
        self.total_rows = 0
        self.valid_rows = 0
        self.errors = []

        logger.info("Loading tickets from %s...", self.csv_file_path)

        with open(self.csv_file_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)

            # Structural validation — fail fast on bad header
            self.validator.validate_header(reader.fieldnames)

            for row_num, row in enumerate(reader, start=1):
                self.total_rows += 1
                try:
                    cleaned = self.validator.validate_row(
                        row_num, row, reader.fieldnames
                    )
                    ticket = TicketRecord(
                        id=row_num,
                        issue=cleaned["Issue"],
                        subject=cleaned.get("Subject", ""),
                        company=cleaned.get("Company"),
                    )
                    self.tickets.append(ticket)
                    self.valid_rows += 1

                except DataValidationError as exc:
                    if strict:
                        raise
                    error_detail = {
                        "row": row_num,
                        "error": str(exc),
                        "raw_data": dict(row),
                    }
                    self.errors.append(error_detail)
                    logger.warning("Row %d skipped: %s", row_num, exc)

        logger.info(
            "Loaded %d/%d valid tickets", self.valid_rows, self.total_rows
        )
        if self.errors and not strict:
            logger.warning("%d rows had validation issues", len(self.errors))

        return self.tickets

    # ------------------------------------------------------------------
    # Method 2: get_statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """Return a summary of the most recent load() call.

        Returns:
            Dict with keys:
                total_rows_read      — int
                valid_tickets_loaded — int
                error_count          — int
                success_rate         — float (0–100)
                errors               — list of error detail dicts
        """
        return {
            "total_rows_read": self.total_rows,
            "valid_tickets_loaded": self.valid_rows,
            "error_count": len(self.errors),
            "success_rate": (self.valid_rows / max(1, self.total_rows)) * 100,
            "errors": self.errors,
        }

    # ------------------------------------------------------------------
    # Method 3: filter_by_company
    # ------------------------------------------------------------------

    def filter_by_company(self, company: Optional[str]) -> list[TicketRecord]:
        """Return all loaded tickets whose company matches the given value.

        Args:
            company: Domain string (e.g. "hackerrank") or None to match
                     tickets with no company assigned.

        Returns:
            List of matching TicketRecord objects (may be empty).
        """
        matches = [t for t in self.tickets if t.company == company]
        logger.info("Found %d tickets for company %r", len(matches), company)
        return matches

    # ------------------------------------------------------------------
    # Method 4: get_ticket_by_id
    # ------------------------------------------------------------------

    def get_ticket_by_id(self, ticket_id: int) -> Optional[TicketRecord]:
        """Look up a single ticket by its integer ID.

        Args:
            ticket_id: The id field of the desired TicketRecord.

        Returns:
            The matching TicketRecord, or None if not found.
        """
        for ticket in self.tickets:
            if ticket.id == ticket_id:
                logger.debug("Ticket id=%d found", ticket_id)
                return ticket
        logger.debug("Ticket id=%d not found", ticket_id)
        return None

    # ------------------------------------------------------------------
    # Method 5: to_dict_list
    # ------------------------------------------------------------------

    def to_dict_list(self) -> list[dict]:
        """Serialise all loaded tickets to a list of plain dicts.

        Returns:
            List of dicts, each with keys: id, issue, subject, company.
        """
        return [ticket.to_dict() for ticket in self.tickets]


# ---------------------------------------------------------------------------
# Section 7: Utility Functions
# ---------------------------------------------------------------------------


def load_tickets(
    csv_path,
    cfg=None,
    strict: bool = False,
) -> list[TicketRecord]:
    """Convenience function: create a DataLoader, load, and return tickets.

    Args:
        csv_path: Path-like or string path to the CSV file.
        cfg:      Configuration module (defaults to imported config).
        strict:   If True, raise on the first validation error.

    Returns:
        List of validated TicketRecord objects.

    Raises:
        ConfigurationError:  If the file does not exist.
        CSVParseError:       If the header is invalid.
        DataValidationError: If strict=True and any row fails validation.
    """
    loader = DataLoader(csv_path, cfg=cfg)
    return loader.load(strict=strict)


def normalize_company(company_str) -> Optional[str]:
    """Normalise a raw company string to a canonical domain identifier.

    Logic:
    - None, empty string, or the literal "None" → returns None.
    - Strips whitespace, then performs a case-insensitive match against
      SUPPORTED_DOMAINS.
    - Returns the canonical domain string on match (e.g. "hackerrank").
    - Returns None if no match is found (does NOT raise).

    Args:
        company_str: Raw company value (string or None).

    Returns:
        Canonical domain string or None.
    """
    if company_str is None:
        return None

    stripped = str(company_str).strip()
    if stripped == "" or stripped.lower() == "none":
        return None

    lower = stripped.lower()
    for domain in SUPPORTED_DOMAINS:
        if lower == domain.lower():
            return domain

    return None  # unrecognised — return None rather than raising


def sanitize_ticket_text(text: str) -> str:
    """Clean ticket text for downstream processing.

    Transformations applied (in order):
    1. Strip leading/trailing whitespace.
    2. Normalise line endings to \\n (handles \\r\\n and \\r).
    3. Collapse runs of horizontal whitespace (spaces/tabs) within each
       line to a single space.

    Args:
        text: Raw ticket text string.

    Returns:
        Cleaned string. Empty input returns an empty string.
    """
    if not text:
        return ""

    # Strip outer whitespace
    result = text.strip()

    # Normalise line endings: \r\n → \n, then \r → \n
    result = result.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse internal horizontal whitespace on each line
    lines = result.split("\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
    result = "\n".join(lines)

    return result
