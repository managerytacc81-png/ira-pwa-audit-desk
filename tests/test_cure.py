"""Unit tests for IRA cure math per Treasury Decision 9998 and IRC 45(b)(7)(B) & 45(b)(8)(D)."""

import pytest
from pathlib import Path

from pwacheck.wd import load_wage_determination
from pwacheck.payroll import load_certified_payroll_csv
from pwacheck.audit import audit_worker_shortfalls, audit_apprenticeship_compliance
from pwacheck.cure import compute_ira_cure, compute_cure_comparison

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_standard_cure_calculation():
    wd = load_wage_determination(FIXTURES_DIR / "sample_wd_IL20240008.json")
    records_mis = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_misclassified.csv")
    records_app = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_apprentice_failure.csv")

    shortfalls, _ = audit_worker_shortfalls(records_mis, wd, annual_interest_rate_pct=11.0)
    app_audit = audit_apprenticeship_compliance(records_app, threshold_pct=15.0)

    # Standard cure
    cure = compute_ira_cure(
        shortfalls=shortfalls,
        apprentice_audit=app_audit,
        boc_year=2024,
        interest_rate_pct=11.0,
        is_intentional_disregard=False,
    )

    # 3 underpaid workers
    assert cure.underpaid_workers_count == 3
    # Prevailing wage penalty: 3 * $5,000 = $15,000
    assert cure.prevailing_wage_penalty_rate == 5000.0
    assert cure.prevailing_wage_penalty_total == 15000.0

    # Apprentice deficiency: 40 deficient hours * $50/hr = $2,000
    assert cure.apprentice_deficient_hours == 40.0
    assert cure.apprentice_penalty_rate == 50.0
    assert cure.apprentice_penalty_total == 2000.0

    # Total IRS penalties = $15,000 + $2,000 = $17,000
    assert cure.total_irs_penalties == 17000.0

    # Worker backpay = gross shortfall + interest
    assert cure.total_worker_backpay_due == pytest.approx(
        cure.total_gross_wage_shortfall + cure.total_interest_due, 0.01
    )

    assert cure.grand_total_cure_exposure == pytest.approx(
        cure.total_worker_backpay_due + cure.total_irs_penalties, 0.01
    )


def test_intentional_disregard_cure_calculation():
    wd = load_wage_determination(FIXTURES_DIR / "sample_wd_IL20240008.json")
    records_mis = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_misclassified.csv")
    records_app = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_apprentice_failure.csv")

    shortfalls, _ = audit_worker_shortfalls(records_mis, wd, annual_interest_rate_pct=11.0)
    app_audit = audit_apprenticeship_compliance(records_app, threshold_pct=15.0)

    # Intentional disregard cure
    cure_int = compute_ira_cure(
        shortfalls=shortfalls,
        apprentice_audit=app_audit,
        boc_year=2024,
        interest_rate_pct=11.0,
        is_intentional_disregard=True,
    )

    # Prevailing wage penalty triples to $10,000 per worker: 3 * $10,000 = $30,000
    assert cure_int.prevailing_wage_penalty_rate == 10000.0
    assert cure_int.prevailing_wage_penalty_total == 30000.0

    # Apprentice deficiency penalty 10x to $500 per deficient hour: 40 * $500 = $20,000
    assert cure_int.apprentice_penalty_rate == 500.0
    assert cure_int.apprentice_penalty_total == 20000.0

    # Total IRS penalties = $30,000 + $20,000 = $50,000
    assert cure_int.total_irs_penalties == 50000.0

    # Worker backpay triples: shortfall * 3 + interest
    expected_backpay = (cure_int.total_gross_wage_shortfall * 3.0) + cure_int.total_interest_due
    assert cure_int.total_worker_backpay_due == pytest.approx(expected_backpay, 0.01)


def test_cure_comparison():
    wd = load_wage_determination(FIXTURES_DIR / "sample_wd_IL20240008.json")
    records_mis = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_misclassified.csv")
    records_app = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_apprentice_failure.csv")

    shortfalls, _ = audit_worker_shortfalls(records_mis, wd)
    app_audit = audit_apprenticeship_compliance(records_app)

    comp = compute_cure_comparison(shortfalls, app_audit)
    assert "standard_cure" in comp
    assert "intentional_disregard" in comp
    assert comp["intentional_disregard"].grand_total_cure_exposure > comp["standard_cure"].grand_total_cure_exposure
