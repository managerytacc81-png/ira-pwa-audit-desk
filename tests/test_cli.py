"""Unit tests for Markdown Health-Check Report generator and CLI."""

import pytest
import subprocess
import sys
from pathlib import Path

from pwacheck.wd import load_wage_determination
from pwacheck.payroll import load_certified_payroll_csv
from pwacheck.audit import audit_worker_shortfalls, audit_apprenticeship_compliance
from pwacheck.cure import compute_cure_comparison
from pwacheck.form4255 import evaluate_form_4255_recapture
from pwacheck.reporter import generate_pwa_health_check_report

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_generate_pwa_health_check_report():
    wd = load_wage_determination(FIXTURES_DIR / "sample_wd_IL20240008.json")
    records_mis = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_misclassified.csv")
    records_app = load_certified_payroll_csv(FIXTURES_DIR / "certified_payroll_apprentice_failure.csv")

    shortfalls, summary = audit_worker_shortfalls(records_mis, wd)
    app_audit = audit_apprenticeship_compliance(records_app)
    cure_comp = compute_cure_comparison(shortfalls, app_audit)
    std_cure = cure_comp["standard_cure"]
    int_cure = cure_comp["intentional_disregard"]

    form_4255 = evaluate_form_4255_recapture(
        project_name="Prairie View Solar",
        capacity_mw=10.0,
        eligible_basis=15000000.0,
        cure_calc_standard=std_cure,
        cure_calc_intentional=int_cure,
    )

    report_md = generate_pwa_health_check_report(
        project_name="Prairie View Solar",
        capacity_mw=10.0,
        county="Cook",
        state="IL",
        boc_year=2024,
        eligible_basis=15000000.0,
        wage_determination=wd,
        shortfalls=shortfalls,
        apprentice_audit=app_audit,
        cure_standard=std_cure,
        cure_intentional=int_cure,
        form_4255=form_4255,
    )

    assert "# IRA Prevailing Wage & Apprenticeship (PWA) Compliance Health-Check Report" in report_md
    assert "Prairie View Solar (10.00 MW AC)" in report_md
    assert "Cook County, IL" in report_md
    assert "Executive Summary & Audit Scorecard" in report_md
    assert "Wage Determination Baseline" in report_md
    assert "Per-Worker Prevailing Wage Shortfall Breakdown" in report_md
    assert "Apprenticeship Metrics & Ratio Compliance" in report_md
    assert "Statutory Cure Math & Penalty Exposure" in report_md
    assert "Form 4255 Part I Column (p) Tax Credit Recapture Risk Analysis" in report_md
    assert "$3,600,000.00" in report_md
    assert "The June 2024 Final Regulations Defense (T.D. 9998)" in report_md


def test_cli_audit_execution(tmp_path):
    report_out = tmp_path / "test_report.md"
    cmd = [
        sys.executable,
        "-m",
        "pwacheck",
        "audit",
        "--wd",
        str(FIXTURES_DIR / "sample_wd_IL20240008.json"),
        "--payroll",
        str(FIXTURES_DIR / "certified_payroll_misclassified.csv"),
        "--project",
        "Test Facility Solar",
        "--capacity",
        "5.0",
        "--basis",
        "8000000.0",
        "--report",
        str(report_out),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Loaded WD IL20240008" in res.stdout
    assert "Form 4255 Part I col (p) Recapture Exposure" in res.stdout
    assert report_out.exists()
    assert report_out.stat().st_size > 500


def test_cli_gfe_execution(tmp_path):
    letter_out = tmp_path / "test_letter.md"
    cmd = [
        sys.executable,
        "-m",
        "pwacheck",
        "gfe",
        "--letter",
        "--out",
        str(letter_out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert letter_out.exists()
    assert "FORMAL REQUEST FOR REGISTERED APPRENTICES" in letter_out.read_text()
