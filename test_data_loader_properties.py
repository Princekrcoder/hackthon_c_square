"""
test_data_loader_properties.py — Property-based tests for data_loader.py

Uses the hypothesis library to verify universal invariants of the data loading
module across a wide range of generated inputs.

Properties tested:
  Property 1: Ticket record round-trip serialization
  Property 2: Text sanitization never increases length
  Property 3: Company normalization is idempotent
  Property 4: Loader statistics maintain invariants
  Property 5: Filtering is non-generative
"""

import csv
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import config
from data_loader import (
    TicketRecord,
    DataLoader,
    normalize_company,
    sanitize_ticket_text,
)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Strategy: positive integer IDs in a reasonable range
positive_ids = st.integers(min_value=1, max_value=10_000)

# Strategy: non-empty issue strings (printable text, at least one non-space char)
non_empty_issues = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),  # exclude surrogates
    min_size=1,
).filter(lambda s: s.strip() != "")

# Strategy: valid domain strings (canonical lowercase)
valid_domains = st.sampled_from(config.SUPPORTED_DOMAINS)

# Strategy: optional company (None or a valid domain)
optional_company = st.one_of(st.none(), valid_domains)


# ---------------------------------------------------------------------------
# Property 1: Ticket record round-trip serialization
# Feature: support-ticket-triage-data-loader
# ---------------------------------------------------------------------------


@given(ticket_id=positive_ids, issue=non_empty_issues)
@settings(max_examples=300)
def test_property_1_ticket_round_trip_serialization(ticket_id, issue):
    """
    Feature: support-ticket-triage-data-loader
    Property 1: Ticket record round-trip serialization

    For any valid (id, issue) pair, a TicketRecord can be created, serialised
    to a dict via to_dict(), and the dict values must match the original fields.
    The round-trip must not raise any exception.
    """
    ticket = TicketRecord(id=ticket_id, issue=issue)
    d = ticket.to_dict()

    # The dict must contain all four expected keys
    assert set(d.keys()) == {"id", "issue", "subject", "company"}

    # Values must match the original record
    assert d["id"] == ticket_id
    assert d["issue"] == issue
    assert d["subject"] == ""
    assert d["company"] is None

    # Re-creating from the dict must produce an equivalent record
    reconstructed = TicketRecord(
        id=d["id"],
        issue=d["issue"],
        subject=d["subject"],
        company=d["company"],
    )
    assert reconstructed.id == ticket.id
    assert reconstructed.issue == ticket.issue
    assert reconstructed.subject == ticket.subject
    assert reconstructed.company == ticket.company


# ---------------------------------------------------------------------------
# Property 2: Text sanitization never increases length
# Feature: support-ticket-triage-data-loader
# ---------------------------------------------------------------------------


@given(text=st.text())
@settings(max_examples=500)
def test_property_2_sanitization_never_increases_length(text):
    """
    Feature: support-ticket-triage-data-loader
    Property 2: Text sanitization never increases length

    For any string input, sanitize_ticket_text() must return a string whose
    length is less than or equal to the length of the input. Sanitization can
    only remove or collapse characters — it must never add new ones.
    """
    result = sanitize_ticket_text(text)
    assert len(result) <= len(text), (
        f"sanitize_ticket_text({text!r}) returned a longer string: "
        f"{len(result)} > {len(text)}"
    )


# ---------------------------------------------------------------------------
# Property 3: Company normalization is idempotent
# Feature: support-ticket-triage-data-loader
# ---------------------------------------------------------------------------


@given(company=st.one_of(
    st.none(),
    st.just(""),
    st.just("None"),
    valid_domains,
    st.text(min_size=1, max_size=30),
))
@settings(max_examples=300)
def test_property_3_company_normalization_is_idempotent(company):
    """
    Feature: support-ticket-triage-data-loader
    Property 3: Company normalization is idempotent

    Applying normalize_company() twice must produce the same result as
    applying it once. That is:
        normalize_company(normalize_company(x)) == normalize_company(x)
    for any input x.
    """
    first = normalize_company(company)
    second = normalize_company(first)
    assert first == second, (
        f"normalize_company is not idempotent for input {company!r}: "
        f"first={first!r}, second={second!r}"
    )


# ---------------------------------------------------------------------------
# Property 4: Loader statistics maintain invariants
# Feature: support-ticket-triage-data-loader
# ---------------------------------------------------------------------------


@given(
    valid_count=st.integers(min_value=0, max_value=20),
    invalid_count=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100)
def test_property_4_statistics_invariants(valid_count, invalid_count):
    """
    Feature: support-ticket-triage-data-loader
    Property 4: Statistics maintain invariants

    For any combination of valid and invalid rows in a CSV:
    - valid_tickets_loaded <= total_rows_read
    - error_count == total_rows_read - valid_tickets_loaded
    - 0.0 <= success_rate <= 100.0
    """
    assume(valid_count + invalid_count > 0)  # need at least one row

    # Build rows: valid rows have a non-empty Issue; invalid rows have empty Issue
    rows = []
    for i in range(valid_count):
        rows.append({
            "Issue": f"Valid issue {i + 1}",
            "Subject": f"Subject {i + 1}",
            "Company": config.SUPPORTED_DOMAINS[i % len(config.SUPPORTED_DOMAINS)],
        })
    for j in range(invalid_count):
        rows.append({
            "Issue": "",  # will fail validation
            "Subject": f"Bad subject {j + 1}",
            "Company": "",
        })

    # Write to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    ) as fh:
        tmp_path = fh.name
        writer = csv.DictWriter(fh, fieldnames=["Issue", "Subject", "Company"])
        writer.writeheader()
        writer.writerows(rows)

    try:
        loader = DataLoader(tmp_path)
        loader.load(strict=False)
        stats = loader.get_statistics()

        total = stats["total_rows_read"]
        valid = stats["valid_tickets_loaded"]
        errors = stats["error_count"]
        rate = stats["success_rate"]

        assert valid <= total, f"valid ({valid}) > total ({total})"
        assert errors == total - valid, (
            f"error_count ({errors}) != total - valid ({total - valid})"
        )
        assert 0.0 <= rate <= 100.0, f"success_rate {rate} out of [0, 100]"

    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Property 5: Filtering is non-generative
# Feature: support-ticket-triage-data-loader
# ---------------------------------------------------------------------------


@given(
    ticket_count=st.integers(min_value=1, max_value=20),
    filter_domain=st.one_of(st.none(), valid_domains),
)
@settings(max_examples=100)
def test_property_5_filtering_is_non_generative(ticket_count, filter_domain):
    """
    Feature: support-ticket-triage-data-loader
    Property 5: Filtering is non-generative

    For any loaded dataset and any filter value:
    - All tickets in the filtered result must match the filter condition.
    - The filtered count must be <= the total loaded count.
    - No new tickets are created by filtering.
    """
    # Build a CSV with tickets assigned to domains in round-robin fashion
    domains_cycle = config.SUPPORTED_DOMAINS + [None]  # include None (no company)
    rows = []
    for i in range(ticket_count):
        domain = domains_cycle[i % len(domains_cycle)]
        rows.append({
            "Issue": f"Issue {i + 1}",
            "Subject": f"Subject {i + 1}",
            "Company": domain if domain is not None else "",
        })

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    ) as fh:
        tmp_path = fh.name
        writer = csv.DictWriter(fh, fieldnames=["Issue", "Subject", "Company"])
        writer.writeheader()
        writer.writerows(rows)

    try:
        loader = DataLoader(tmp_path)
        loader.load(strict=False)

        total_loaded = len(loader.tickets)
        filtered = loader.filter_by_company(filter_domain)

        # Filtered count must not exceed total
        assert len(filtered) <= total_loaded, (
            f"filter_by_company({filter_domain!r}) returned {len(filtered)} tickets "
            f"but only {total_loaded} were loaded"
        )

        # Every returned ticket must match the filter condition
        for ticket in filtered:
            assert ticket.company == filter_domain, (
                f"Ticket {ticket.id} has company={ticket.company!r} "
                f"but filter was {filter_domain!r}"
            )

        # Filtered tickets must be a subset of the loaded tickets (by id)
        loaded_ids = {t.id for t in loader.tickets}
        for ticket in filtered:
            assert ticket.id in loaded_ids, (
                f"Filtered ticket id={ticket.id} is not in the loaded set"
            )

    finally:
        os.unlink(tmp_path)
