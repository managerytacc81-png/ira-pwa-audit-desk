"""Unit tests for prevailing wage and apprenticeship audit engine."""

import pytest
from pathlib import Path

from pwacheck.wd import load_wage_determination
from pwacheck.payroll import load_certified_payroll_csv
from pwacheck.audit import audit_worker_shortfalls, audit_apprenticeship_compliance

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_wd():
    return load_wage_determination(FIXTURES_DIR / "sample_wd_IL20240008.json")


def test_audit_compliant_crew(sample_wd):
    records = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_compliant.csv")
    shortfalls, summary = audit_worker_shortfalls(records, sample_wd, annual_interest_rate_pct=11.0)

    # Compliant crew should have 0 shortfalls
    assert len(shortfalls) == 0
    assert summary["underpaid_workers"] == 0
    assert summary["total_wage_shortfall"] == 0.0
    assert summary["total_correction"] == 0.0

    # Apprenticeship audit
    app_audit = audit_apprenticeship_compliance(records, threshold_pct=15.0)
    assert app_audit.total_labor_hours == 400.0
    assert app_audit.apprentice_hours == 80.0
    assert app_audit.apprentice_percentage == 20.0
    assert app_audit.is_percentage_compliant is True
    assert app_audit.deficient_labor_hours == 0.0
    assert len(app_audit.daily_ratio_violations) == 0


def test_audit_misclassified_crew(sample_wd):
    records = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_misclassified.csv")
    shortfalls, summary = audit_worker_shortfalls(records, sample_wd, annual_interest_rate_pct=11.0)

    # Misclassified crew has 3 underpaid workers: WKR-202, WKR-203, WKR-204
    assert len(shortfalls) == 3
    assert summary["underpaid_workers"] == 3
    assert summary["total_wage_shortfall"] > 0.0

    shortfall_ids = {s.worker_id: s for s in shortfalls}
    assert "WKR-202" in shortfall_ids
    assert "WKR-203" in shortfall_ids
    assert "WKR-204" in shortfall_ids

    # WKR-202 was reported as Laborer but performed Electrician
    w202 = shortfall_ids["WKR-202"]
    assert w202.is_misclassified is True
    assert "Electrician" in w202.misclassification_note
    # Required is $94.50, paid $35.00 -> $59.50 * 40 = $2,380.00
    assert w202.gross_wage_shortfall == pytest.approx(2380.00, 0.01)

    # WKR-203 was reported as Laborer but performed Electrician
    w203 = shortfall_ids["WKR-203"]
    assert w203.is_misclassified is True
    # Required is $94.50, paid $30.00 -> $64.50 * 40 = $2,580.00
    assert w203.gross_wage_shortfall == pytest.approx(2580.00, 0.01)

    # WKR-204 was Ironworker paid $50 vs $97.98 -> $47.98 * 40 = $1,919.20
    w204 = shortfall_ids["WKR-204"]
    assert w204.gross_wage_shortfall == pytest.approx(1919.20, 0.01)


def test_audit_apprentice_failure_crew(sample_wd):
    records = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_apprentice_failure.csv")

    app_audit = audit_apprenticeship_compliance(records, threshold_pct=15.0)

    # Total hours: 380 + 20 + 10 + 10 = 400 hours
    assert app_audit.total_labor_hours == 400.0

    # Check daily ratio violation: 2 apprentices unsupervised on 2024-06-04
    assert len(app_audit.daily_ratio_violations) == 1
    viol = app_audit.daily_ratio_violations[0]
    assert viol.work_date == "2024-06-04"
    assert viol.excess_apprentices == 2
    assert viol.journeyworker_count == 0

    # Unsupervised apprentice hours (20 hrs) are disallowed from qualifying hours
    # Raw apprentice hours = 40 hrs; qualified = 40 - 20 = 20 hrs
    assert app_audit.apprentice_hours == 20.0
    assert app_audit.apprentice_percentage == 5.0
    assert app_audit.is_percentage_compliant is False

    # Required 15% of 400 = 60 hours. Deficient = 60 - 20 = 40 hours
    assert app_audit.deficient_labor_hours == 40.0
