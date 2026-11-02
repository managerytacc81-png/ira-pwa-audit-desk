"""pwacheck — IRA Prevailing Wage & Apprenticeship Compliance Toolkit."""

__version__ = "1.0.0"

from .models import (
    WageClassification,
    WageDetermination,
    PayrollRecord,
    WorkerShortfall,
    DailyRatioCheck,
    ApprenticeAuditResult,
    CureCalculation,
    Form4255Exposure,
)
from .wd import load_wage_determination, fetch_sam_gov_wd, parse_wd_text, parse_wd_json
from .payroll import load_certified_payroll_csv
from .audit import audit_worker_shortfalls, audit_apprenticeship_compliance
from .cure import compute_ira_cure, compute_cure_comparison
from .form4255 import evaluate_form_4255_recapture
from .reporter import generate_pwa_health_check_report
from .gfe import generate_rap_request_letter, generate_5_day_tracker

__all__ = [
    "WageClassification",
    "WageDetermination",
    "PayrollRecord",
    "WorkerShortfall",
    "DailyRatioCheck",
    "ApprenticeAuditResult",
    "CureCalculation",
    "Form4255Exposure",
    "load_wage_determination",
    "fetch_sam_gov_wd",
    "parse_wd_text",
    "parse_wd_json",
    "load_certified_payroll_csv",
    "audit_worker_shortfalls",
    "audit_apprenticeship_compliance",
    "compute_ira_cure",
    "compute_cure_comparison",
    "evaluate_form_4255_recapture",
    "generate_pwa_health_check_report",
    "generate_rap_request_letter",
    "generate_5_day_tracker",
]
