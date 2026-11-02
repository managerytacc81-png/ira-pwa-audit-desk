"""Unit tests for certified payroll ingestion."""

import pytest
from pathlib import Path

from pwacheck.payroll import (
    load_certified_payroll_csv,
    normalize_column_name,
    map_row_to_record,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_normalize_column_name():
    assert normalize_column_name("Worker ID") == "workerid"
    assert normalize_column_name("Hourly Base Paid ($)") == "hourlybasepaid"
    assert normalize_column_name("Is_Apprentice?") == "isapprentice"


def test_load_compliant_payroll_fixture():
    csv_path = FIXTURES_DIR / "certified_payroll_compliant.csv"
    records = load_certified_payroll_csv(csv_path)

    assert len(records) == 10
    total_hours = sum(r.total_hours for r in records)
    assert total_hours == 400.0

    apprentices = [r for r in records if r.is_apprentice]
    assert len(apprentices) == 2
    for a in apprentices:
        assert a.apprentice_program_id == "RAP-IL-134-2023"
        assert a.apprentice_period_ratio == 0.60


def test_load_payroll_with_dirty_numbers():
    raw_csv = """worker_id,worker_name,trade,hours,rate_of_pay,fringe_rate,apprentice
W1,Alice,Electrician,40.0,"$55.00","$40.00",True
W2,Bob,Laborer,35.5,"$48.50","$30.00",0
"""
    records = load_certified_payroll_csv(raw_csv)
    assert len(records) == 2
    assert records[0].hourly_base_paid == 55.00
    assert records[0].hourly_fringe_paid == 40.00
    assert records[0].total_rate_paid == 95.00
    assert records[0].is_apprentice is True
    assert records[1].is_apprentice is False
