"""Prevailing wage and apprenticeship compliance audit engine."""

from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from .models import (
    WageDetermination,
    PayrollRecord,
    WorkerShortfall,
    DailyRatioCheck,
    ApprenticeAuditResult,
)


def audit_worker_shortfalls(
    payroll_records: List[PayrollRecord],
    wage_determination: WageDetermination,
    annual_interest_rate_pct: float = 11.0,  # Sec 6621 AFR + 6 percentage points
    cure_date_str: Optional[str] = None,
) -> Tuple[List[WorkerShortfall], Dict[str, float]]:
    """Audits certified payroll against wage determination to identify per-worker shortfalls.
    
    Returns:
        List of WorkerShortfall objects and a dictionary of summary metrics.
    """
    cure_date = datetime.strptime(cure_date_str, "%Y-%m-%d").date() if cure_date_str else datetime.now().date()
    worker_buckets = defaultdict(list)

    for rec in payroll_records:
        worker_buckets[rec.worker_id].append(rec)

    shortfall_results: List[WorkerShortfall] = []
    total_shortfall_hours = 0.0
    total_wage_shortfall_dollars = 0.0
    total_interest_dollars = 0.0

    for worker_id, records in worker_buckets.items():
        sample_rec = records[0]
        worker_name = sample_rec.worker_name
        contractor = sample_rec.contractor

        w_total_hours = sum(r.total_hours for r in records)
        w_shortfall_hours = 0.0
        w_gross_shortfall = 0.0
        w_interest = 0.0
        is_misclassified = False
        misclassification_note = None

        # Check for trade misclassification across worker records
        reported_trades = set(r.reported_trade for r in records)
        actual_trades = set(r.actual_trade for r in records if r.actual_trade)

        effective_trade = next(iter(actual_trades)) if actual_trades else next(iter(reported_trades))
        if actual_trades and actual_trades != reported_trades:
            is_misclassified = True
            misclassification_note = f"Reported as '{','.join(reported_trades)}' but performed work of '{','.join(actual_trades)}'"

        for r in records:
            trade_to_evaluate = r.effective_trade()
            wd_class = wage_determination.get_classification(trade_to_evaluate)

            if not wd_class:
                # If trade not explicitly found in WD, fallback to highest base or flag
                req_rate = 50.0  # conservative baseline
            else:
                req_rate = wd_class.total_rate

            # If registered apprentice, rate is adjusted per apprentice period scale
            if r.is_apprentice and r.apprentice_period_ratio > 0.0:
                # Apprentice basic wage rate is prorated, fringe is typically 100% or prorated
                if wd_class:
                    req_rate = round((wd_class.basic_rate * r.apprentice_period_ratio) + wd_class.fringe_rate, 2)

            hourly_diff = req_rate - r.total_rate_paid

            if hourly_diff > 0.001:
                shortfall_for_rec = round(hourly_diff * r.total_hours, 2)
                w_shortfall_hours += r.total_hours
                w_gross_shortfall += shortfall_for_rec

                # Interest calculation: IRC 45(b)(7)(B)(i)(I)(bb)
                try:
                    work_d = datetime.strptime(r.work_date, "%Y-%m-%d").date()
                except Exception:
                    work_d = cure_date

                days_elapsed = max(1, (cure_date - work_d).days)
                # IRC 6621 + 6 points annualized interest compounded or simple daily
                interest_for_rec = round(shortfall_for_rec * (annual_interest_rate_pct / 100.0) * (days_elapsed / 365.0), 2)
                w_interest += interest_for_rec

        if w_gross_shortfall > 0.0 or is_misclassified:
            avg_paid_rate = (
                round(sum(r.total_rate_paid * r.total_hours for r in records) / w_total_hours, 2)
                if w_total_hours > 0 else 0.0
            )
            req_class = wage_determination.get_classification(effective_trade)
            effective_req_rate = req_class.total_rate if req_class else 0.0
            avg_hourly_shortfall = (
                round(w_gross_shortfall / w_shortfall_hours, 2) if w_shortfall_hours > 0 else 0.0
            )

            ws = WorkerShortfall(
                worker_id=worker_id,
                worker_name=worker_name,
                contractor=contractor,
                reported_trade=','.join(reported_trades),
                effective_trade=effective_trade,
                total_hours=round(w_total_hours, 2),
                shortfall_hours=round(w_shortfall_hours, 2),
                required_rate=effective_req_rate,
                paid_rate=avg_paid_rate,
                hourly_shortfall=avg_hourly_shortfall,
                gross_wage_shortfall=round(w_gross_shortfall, 2),
                interest_rate_pct=annual_interest_rate_pct,
                interest_amount=round(w_interest, 2),
                total_correction_due=round(w_gross_shortfall + w_interest, 2),
                is_misclassified=is_misclassified,
                misclassification_note=misclassification_note,
            )
            shortfall_results.append(ws)
            total_shortfall_hours += w_shortfall_hours
            total_wage_shortfall_dollars += w_gross_shortfall
            total_interest_dollars += w_interest

    summary = {
        "total_workers": len(worker_buckets),
        "underpaid_workers": len(shortfall_results),
        "total_shortfall_hours": round(total_shortfall_hours, 2),
        "total_wage_shortfall": round(total_wage_shortfall_dollars, 2),
        "total_interest": round(total_interest_dollars, 2),
        "total_correction": round(total_wage_shortfall_dollars + total_interest_dollars, 2),
    }

    return shortfall_results, summary


def audit_apprenticeship_compliance(
    payroll_records: List[PayrollRecord],
    threshold_pct: float = 15.0,  # 15% for BOC 2024+
    default_daily_ratio: Tuple[int, int] = (1, 1),  # (1 apprentice per 1 journeyworker)
) -> ApprenticeAuditResult:
    """Audits apprentice labor hours, daily apprentice ratios, and contractor participation under IRC 45(b)(8)."""
    total_labor_hours = sum(r.total_hours for r in payroll_records)

    # 1. Daily ratio compliance check
    # Group by (work_date, contractor, trade)
    day_shift_map = defaultdict(lambda: {"journey": 0, "apprentice": 0, "app_hours": 0.0, "journey_hours": 0.0})
    contractor_worker_map = defaultdict(set)
    contractor_apprentice_map = defaultdict(set)

    for r in payroll_records:
        contractor_worker_map[r.contractor].add(r.worker_id)
        if r.is_apprentice:
            contractor_apprentice_map[r.contractor].add(r.worker_id)

        key = (r.work_date, r.contractor, r.effective_trade())
        if r.is_apprentice:
            day_shift_map[key]["apprentice"] += 1
            day_shift_map[key]["app_hours"] += r.total_hours
        else:
            day_shift_map[key]["journey"] += 1
            day_shift_map[key]["journey_hours"] += r.total_hours

    daily_ratio_violations: List[DailyRatioCheck] = []
    disallowed_apprentice_hours = 0.0

    for (work_date, contractor, trade), counts in day_shift_map.items():
        j_count = counts["journey"]
        a_count = counts["apprentice"]

        # Default ratio rule: 1 apprentice per journeyworker
        # If j_count == 0 and a_count > 0, apprentice is unsupervised!
        allowed_app = j_count * default_daily_ratio[0]
        if a_count > allowed_app:
            excess = a_count - allowed_app
            # Prorate disallowed hours
            disallowed_hours = round((excess / a_count) * counts["app_hours"], 2)
            disallowed_apprentice_hours += disallowed_hours
            daily_ratio_violations.append(
                DailyRatioCheck(
                    work_date=work_date,
                    contractor=contractor,
                    trade=trade,
                    journeyworker_count=j_count,
                    apprentice_count=a_count,
                    allowed_apprentice_count=allowed_app,
                    excess_apprentices=excess,
                    is_compliant=False,
                    notes=f"Exceeded daily ratio: {a_count} apprentices with {j_count} journeyworkers ({disallowed_hours} hrs disallowed)",
                )
            )

    # Qualified apprentice hours excluding disallowed ratio hours
    raw_apprentice_hours = sum(r.total_hours for r in payroll_records if r.is_apprentice)
    qualified_apprentice_hours = max(0.0, raw_apprentice_hours - disallowed_apprentice_hours)

    apprentice_pct = round((qualified_apprentice_hours / total_labor_hours * 100.0), 2) if total_labor_hours > 0 else 0.0
    is_pct_compliant = apprentice_pct >= threshold_pct

    target_hours = round(total_labor_hours * (threshold_pct / 100.0), 2)
    deficient_hours = max(0.0, round(target_hours - qualified_apprentice_hours, 2))

    # Contractor participation requirement: each employer with >= 4 workers must have >= 1 apprentice
    c_with_4plus = 0
    c_satisfying = 0
    for contractor, workers in contractor_worker_map.items():
        if len(workers) >= 4:
            c_with_4plus += 1
            if len(contractor_apprentice_map.get(contractor, set())) >= 1:
                c_satisfying += 1

    return ApprenticeAuditResult(
        total_labor_hours=round(total_labor_hours, 2),
        apprentice_hours=round(qualified_apprentice_hours, 2),
        apprentice_percentage=apprentice_pct,
        required_threshold_pct=threshold_pct,
        is_percentage_compliant=is_pct_compliant,
        deficient_labor_hours=deficient_hours,
        contractors_monitored=len(contractor_worker_map),
        contractors_with_4plus_workers=c_with_4plus,
        contractors_satisfying_participation=c_satisfying,
        daily_ratio_violations=daily_ratio_violations,
    )
