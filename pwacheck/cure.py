"""Statutory IRA cure math engine per Treasury Decision 9998 and IRC 45(b)(7)(B) & 45(b)(8)(D)."""

from typing import List, Dict, Any, Tuple
from .models import WorkerShortfall, ApprenticeAuditResult, CureCalculation


def compute_ira_cure(
    shortfalls: List[WorkerShortfall],
    apprentice_audit: ApprenticeAuditResult,
    boc_year: int = 2024,
    interest_rate_pct: float = 11.0,  # Sec 6621 Federal Short-term Rate + 6 percentage points
    is_intentional_disregard: bool = False,
) -> CureCalculation:
    """Computes statutory cure amounts and IRS penalties exactly per T.D. 9998 / IRC 45(b)(7)(B) & 45(b)(8)(D).
    
    Prevailing Wage (IRC 45(b)(7)(B)):
      - Correction to Worker: Shortfall + Interest (Sec 6621 + 6pts)
        [If intentional disregard: Shortfall * 3 + Interest]
      - IRS Penalty: $5,000 per underpaid worker per year ($10,000 if intentional disregard)
      
    Apprenticeship (IRC 45(b)(8)(D)):
      - Deficiency Penalty: $50 per deficient labor hour ($500 if intentional disregard)
      - Statutory Labor Hour Threshold: 15% for BOC 2024+
    """
    total_shortfall_hours = sum(s.shortfall_hours for s in shortfalls)
    total_gross_wage_shortfall = sum(s.gross_wage_shortfall for s in shortfalls)
    total_interest_due = sum(s.interest_amount for s in shortfalls)
    underpaid_workers_count = len(shortfalls)

    # Worker correction due
    if is_intentional_disregard:
        total_worker_backpay_due = round((total_gross_wage_shortfall * 3.0) + total_interest_due, 2)
        pw_penalty_rate = 10000.0
        app_penalty_rate = 500.0
    else:
        total_worker_backpay_due = round(total_gross_wage_shortfall + total_interest_due, 2)
        pw_penalty_rate = 5000.0
        app_penalty_rate = 50.0

    # Prevailing wage penalty total
    pw_penalty_total = round(underpaid_workers_count * pw_penalty_rate, 2)

    # Apprenticeship penalty total
    deficient_hours = apprentice_audit.deficient_labor_hours
    app_penalty_total = round(deficient_hours * app_penalty_rate, 2)

    total_irs_penalties = round(pw_penalty_total + app_penalty_total, 2)
    grand_total = round(total_worker_backpay_due + total_irs_penalties, 2)

    return CureCalculation(
        boc_year=boc_year,
        total_workers_audited=shortfalls[0].total_hours if shortfalls else 0,  # updated by caller
        underpaid_workers_count=underpaid_workers_count,
        total_labor_hours=apprentice_audit.total_labor_hours,
        total_shortfall_hours=round(total_shortfall_hours, 2),
        total_gross_wage_shortfall=round(total_gross_wage_shortfall, 2),
        interest_rate_pct=interest_rate_pct,
        total_interest_due=round(total_interest_due, 2),
        total_worker_backpay_due=total_worker_backpay_due,
        prevailing_wage_penalty_rate=pw_penalty_rate,
        prevailing_wage_penalty_total=pw_penalty_total,
        apprentice_deficient_hours=round(deficient_hours, 2),
        apprentice_penalty_rate=app_penalty_rate,
        apprentice_penalty_total=app_penalty_total,
        total_irs_penalties=total_irs_penalties,
        grand_total_cure_exposure=grand_total,
        is_intentional_disregard=is_intentional_disregard,
    )


def compute_cure_comparison(
    shortfalls: List[WorkerShortfall],
    apprentice_audit: ApprenticeAuditResult,
    boc_year: int = 2024,
    interest_rate_pct: float = 11.0,
) -> Dict[str, CureCalculation]:
    """Computes side-by-side standard cure vs intentional disregard exposure.
    
    Highlights the massive financial shielding delivered by quarterly certified payroll
    reviews under the June 2024 final regulations (T.D. 9998, Reg. 1.45-7(c)(6)).
    """
    standard = compute_ira_cure(
        shortfalls, apprentice_audit, boc_year, interest_rate_pct, is_intentional_disregard=False
    )
    intentional = compute_ira_cure(
        shortfalls, apprentice_audit, boc_year, interest_rate_pct, is_intentional_disregard=True
    )
    return {
        "standard_cure": standard,
        "intentional_disregard": intentional,
    }
