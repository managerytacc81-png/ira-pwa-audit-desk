"""Client-ready Markdown PWA Compliance Health-Check Report Generator."""

from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import (
    WageDetermination,
    WorkerShortfall,
    ApprenticeAuditResult,
    CureCalculation,
    Form4255Exposure,
)


def generate_pwa_health_check_report(
    project_name: str,
    capacity_mw: float,
    county: str,
    state: str,
    boc_year: int,
    eligible_basis: float,
    wage_determination: WageDetermination,
    shortfalls: List[WorkerShortfall],
    apprentice_audit: ApprenticeAuditResult,
    cure_standard: CureCalculation,
    cure_intentional: CureCalculation,
    form_4255: Form4255Exposure,
    report_date: Optional[str] = None,
    auditor_name: str = "Robert Ketler, PWA Compliance Audit Desk",
) -> str:
    """Generates an executive-ready, legally defensible Markdown PWA Compliance Health-Check Report."""
    r_date = report_date or datetime.now().strftime("%B %d, %Y")

    # Determine status
    is_compliant = (len(shortfalls) == 0) and apprentice_audit.is_percentage_compliant and (len(apprentice_audit.daily_ratio_violations) == 0)
    status_badge = "🟢 FULLY COMPLIANT" if is_compliant else "🔴 CURE ACTION REQUIRED (STATUTORY EXPOSURE)"

    report = f"""# IRA Prevailing Wage & Apprenticeship (PWA) Compliance Health-Check Report
**Facility:** {project_name} ({capacity_mw:.2f} MW AC) | **Location:** {county} County, {state}  
**Audit Report Date:** {r_date} | **Lead Auditor:** {auditor_name}  
**Compliance Status:** **{status_badge}**  
**Statutory Framework:** Internal Revenue Code (IRC) §§ 45(b)(7), 45(b)(8), 48(a)(9), 48E & Treasury Decision 9998 (89 FR 53184)  

---

## 1. Executive Summary & Audit Scorecard

This Health-Check Report provides an autonomous forensic audit of certified construction payrolls for the **{project_name}** project against applicable Department of Labor (DOL) Davis-Bacon Wage Determinations and IRS Prevailing Wage and Apprenticeship (PWA) statutory standards.

Under the Inflation Reduction Act of 2022 (IRA), claiming the **30% full investment tax credit (ITC)** requires satisfying strict prevailing wage and apprenticeship requirements. Failure to comply or cure underpayments triggers severe per-worker statutory penalties and results in **Form 4255 Part I Column (p) recapture of the 5x credit multiplier**, dropping the tax credit to the 6% statutory base rate.

### Audit Scorecard
| Metric | Audit Finding | Statutory Mandate | Compliance Status |
|:---|:---:|:---:|:---:|
| **Prevailing Wage Compliance** | {len(shortfalls)} Underpaid Workers | 100% of Laborers & Mechanics Paid >= WD Total Rate | {"✅ Compliant" if len(shortfalls) == 0 else "❌ Non-Compliant"} |
| **Gross Wage Shortfall** | ${cure_standard.total_gross_wage_shortfall:,.2f} | $0.00 Shortfall | {"✅ None" if cure_standard.total_gross_wage_shortfall == 0 else "⚠️ Correction Due"} |
| **Apprentice Labor Share** | {apprentice_audit.apprentice_percentage:.1f}% ({apprentice_audit.apprentice_hours:,.1f} hrs) | >= {apprentice_audit.required_threshold_pct:.1f}% for BOC {boc_year}+ | {"✅ Met" if apprentice_audit.is_percentage_compliant else "❌ Deficient"} |
| **Deficient Apprentice Hours** | {apprentice_audit.deficient_labor_hours:,.1f} Hours | 0.0 Hours Deficient | {"✅ None" if apprentice_audit.deficient_labor_hours == 0 else "⚠️ Penalty Due"} |
| **Daily Apprentice Ratio** | {len(apprentice_audit.daily_ratio_violations)} Shift Violations | Full Adherence to Registered Program Ratios | {"✅ Compliant" if len(apprentice_audit.daily_ratio_violations) == 0 else "❌ Ratio Exceeded"} |
| **Contractor Participation** | {apprentice_audit.contractors_satisfying_participation}/{apprentice_audit.contractors_with_4plus_workers} Qualified Employers | 1+ Apprentice per Employer with >= 4 Workers | {"✅ Compliant" if apprentice_audit.contractors_satisfying_participation >= apprentice_audit.contractors_with_4plus_workers else "⚠️ Incomplete"} |
| **Form 4255 Recapture Risk** | ${form_4255.recapture_exposure_col_p:,.2f} | $0.00 Recapture (5x Multiplier Secured) | {"✅ Zero Risk" if is_compliant else "🚨 Critical Exposure"} |

---

## 2. Wage Determination Baseline

The certified payroll records were evaluated against DOL Wage Determination **{wage_determination.wd_id}** (Revision {wage_determination.revision}):
* **Jurisdiction:** {wage_determination.county} County, {wage_determination.state}
* **Construction Type:** {wage_determination.construction_type}
* **Publication Date:** {wage_determination.published_date or "Current Edition"}

### Applicable Davis-Bacon Prevailing Wage Rates
| Classification / Trade | Basic Hourly Rate ($/hr) | Fringe Benefits ($/hr) | Total Prevailing Rate ($/hr) |
|:---|:---:|:---:|:---:|
"""
    for trade, wc in sorted(wage_determination.classifications.items()):
        report += f"| **{wc.trade}** | ${wc.basic_rate:.2f} | ${wc.fringe_rate:.2f} | **${wc.total_rate:.2f}** |\n"

    report += f"""
---

## 3. Certified Payroll Audit Findings

A total of **{cure_standard.total_labor_hours:,.1f} labor hours** across **{cure_standard.total_workers_audited if cure_standard.total_workers_audited > 0 else len(shortfalls)} workers** were examined.
"""

    if not shortfalls:
        report += "\n> [!NOTE] All workers were compensated at or above the required basic wage and fringe benefit rates. Zero prevailing wage shortfalls identified.\n"
    else:
        report += f"""
### Per-Worker Prevailing Wage Shortfall Breakdown
| Worker ID | Name | Contractor | Effective Trade | Audited Hours | Shortfall Hours | Paid Rate | Required Rate | Wage Shortfall | Sec 6621+6% Interest | Total Correction Due | Misclassified? |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
        for s in shortfalls:
            mis_flag = "⚠️ YES" if s.is_misclassified else "No"
            report += f"| {s.worker_id} | {s.worker_name} | {s.contractor} | {s.effective_trade} | {s.total_hours:.1f} | {s.shortfall_hours:.1f} | ${s.paid_rate:.2f} | ${s.required_rate:.2f} | ${s.gross_wage_shortfall:,.2f} | ${s.interest_amount:,.2f} | **${s.total_correction_due:,.2f}** | {mis_flag} |\n"

        misclassified_workers = [s for s in shortfalls if s.is_misclassified]
        if misclassified_workers:
            report += "\n### Classification Integrity Findings\n"
            for m in misclassified_workers:
                report += f"* **Worker {m.worker_id} ({m.worker_name}):** {m.misclassification_note}. Under 29 CFR Part 5 and T.D. 9998, misclassifying skilled electricians or mechanics as general laborers to pay lower wage rates constitutes a primary trigger for IRS intentional disregard penalties.\n"

    report += f"""
---

## 4. Apprenticeship Metrics & Ratio Compliance (IRC § 45(b)(8))

For facilities beginning construction in **{boc_year}**, IRC § 45(b)(8)(A) establishes a **{apprentice_audit.required_threshold_pct:.1f}% qualified apprentice labor-hour threshold**.

### Apprentice Utilization Table
| Metric | Value | Statutory Requirement | Status |
|:---|:---:|:---:|:---:|
| **Total Project Labor Hours** | {apprentice_audit.total_labor_hours:,.1f} hrs | Total across all contractors | Baseline |
| **Qualified Apprentice Hours** | {apprentice_audit.apprentice_hours:,.1f} hrs | DOL Office of Apprenticeship Registered Programs | Audited |
| **Actual Apprentice Percentage** | **{apprentice_audit.apprentice_percentage:.2f}%** | **>= {apprentice_audit.required_threshold_pct:.1f}%** | {"✅ Pass" if apprentice_audit.is_percentage_compliant else "❌ Deficient"} |
| **Deficient Labor Hours** | **{apprentice_audit.deficient_labor_hours:,.1f} hrs** | 0.0 Deficient Hours | {"✅ Pass" if apprentice_audit.deficient_labor_hours == 0 else "⚠️ Cure Penalty Required"} |

"""

    if apprentice_audit.daily_ratio_violations:
        report += "### Daily Apprentice-to-Journeyworker Ratio Violations\n"
        report += "| Work Date | Contractor | Trade | Journeyworkers | Apprentices | Allowed Max | Excess Apprentices | Findings Note |\n"
        report += "|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|\n"
        for d in apprentice_audit.daily_ratio_violations:
            report += f"| {d.work_date} | {d.contractor} | {d.trade} | {d.journeyworker_count} | {d.apprentice_count} | {d.allowed_apprentice_count} | {d.excess_apprentices} | {d.notes} |\n"
        report += "\n> [!CAUTION] Under Reg. § 1.45-8(d), apprentice hours worked in excess of registered program daily ratios do NOT count toward the 15% labor-hour requirement and must be re-rated and paid at full journeyman prevailing rates.\n"

    report += f"""
---

## 5. Statutory Cure Math & Penalty Exposure

To cure non-compliance under IRC § 45(b)(7)(B) and § 45(b)(8)(D), the taxpayer must execute statutory corrections within the applicable cure window:

### IRC Cure Computation
| Statutory Component | Standard Cure (Timely Self-Correction) | Intentional Disregard Exposure |
|:---|:---:|:---:|
| **Worker Back Pay (Gross Shortfall)** | ${cure_standard.total_gross_wage_shortfall:,.2f} | ${cure_intentional.total_gross_wage_shortfall * 3:,.2f} *(3x Shortfall)* |
| **Interest Due to Workers (Sec 6621 + 6%)** | ${cure_standard.total_interest_due:,.2f} | ${cure_intentional.total_interest_due:,.2f} |
| **Total Worker Back Pay Due** | **${cure_standard.total_worker_backpay_due:,.2f}** | **${cure_intentional.total_worker_backpay_due:,.2f}** |
| **Prevailing Wage IRS Penalty** | ${cure_standard.prevailing_wage_penalty_total:,.2f} *(${cure_standard.prevailing_wage_penalty_rate:,.0f}/worker)* | ${cure_intentional.prevailing_wage_penalty_total:,.2f} *(${cure_intentional.prevailing_wage_penalty_rate:,.0f}/worker)* |
| **Apprenticeship IRS Penalty** | ${cure_standard.apprentice_penalty_total:,.2f} *(${cure_standard.apprentice_penalty_rate:,.0f}/def-hr)* | ${cure_intentional.apprentice_penalty_total:,.2f} *(${cure_intentional.apprentice_penalty_rate:,.0f}/def-hr)* |
| **Total IRS Statutory Penalties** | **${cure_standard.total_irs_penalties:,.2f}** | **${cure_intentional.total_irs_penalties:,.2f}** |
| **GRAND TOTAL CURE EXPOSURE** | **${cure_standard.grand_total_cure_exposure:,.2f}** | **${cure_intentional.grand_total_cure_exposure:,.2f}** |

---

## 6. Form 4255 Part I Column (p) Tax Credit Recapture Risk Analysis

Under Internal Revenue Code Section 48 / Section 48E, failure to satisfy PWA requirements results in the complete loss of the **5x credit multiplier**, reducing the credit from **30%** to the **6% base rate**.

This forfeiture is reportable directly on **IRS Form 4255 (Recapture of Investment Credit) Part I, Column (p)**.

### Investment Credit Recapture Profile
* **Project Eligible Basis / CapEx:** ${form_4255.eligible_basis:,.2f}
* **Claimed 30% Full Tax Credit (with PWA Multiplier):** ${form_4255.full_credit_amount:,.2f}
* **Statutory 6% Base Credit (PWA Non-Compliant):** ${form_4255.base_credit_amount:,.2f}
* **Form 4255 Part I Column (p) Recapture Exposure:** **${form_4255.recapture_exposure_col_p:,.2f}**

### Return on Compliance Investment (ROI)
* **Cost to Execute Standard Statutory Cure:** ${form_4255.cure_cost_standard:,.2f}
* **Net Value Protected / Tax Savings:** **${form_4255.net_savings_from_cure:,.2f}**
* **Compliance ROI Multiple:** **{form_4255.roi_multiple:.1f}x**

> [!IMPORTANT] Executing a timely statutory cure costing **${form_4255.cure_cost_standard:,.2f}** preserves **${form_4255.recapture_exposure_col_p:,.2f}** in clean energy tax credits—a return of **{form_4255.roi_multiple:.1f} to 1**.

---

## 7. The June 2024 Final Regulations Defense (T.D. 9998)

Treasury Decision 9998 (promulgated June 25, 2024; 89 FR 53184) established critical procedural safeguards for developers and asset owners:

1. **Rebuttable Presumption Against Intentional Disregard (Reg. § 1.45-7(c)(6)):**
   Taxpayers who implement ongoing quarterly certified payroll audits and cure underpayments within 30 days of discovery establish a formal rebuttable presumption of **no intentional disregard**. This shields the project from:
   * Doubled prevailing wage penalties ($10,000 vs $5,000 per worker)
   * Ten-fold apprenticeship penalties ($500 vs $50 per deficient hour)
   * Tripled worker back-pay damages (3x shortfall)
   * The catastrophic loss of the 5x credit multiplier on Form 4255.

2. **Good Faith Effort (GFE) Exception (Reg. § 1.45-8(f)):**
   Apprenticeship deficiency penalties do not apply if the taxpayer or its contractors submitted written requests to Registered Apprenticeship Programs in the geographic area and were denied or received no response within **5 business days**.

---

## 8. Strategic Action Plan & Cure Roadmap

1. **Issue Worker Back-Pay Checks:** Remit ${cure_standard.total_worker_backpay_due:,.2f} to the {len(shortfalls)} affected workers, including accrued Section 6621 interest.
2. **Obtain Form 1099/W-2 Proof of Payment:** Secure signed worker receipts and proof of electronic deposit.
3. **Execute Form 4255 / IRS Cure Filing:** Report and pay the statutory IRS penalty of ${cure_standard.total_irs_penalties:,.2f} concurrently with the annual federal income tax return.
4. **Deploy Apprentice Good Faith Effort Packet:** For future phases, submit RAP request letters 5 business days in advance to secure statutory GFE safe-harbor protection.
5. **Implement Quarterly Verification Cadence:** Institutionalize quarterly certified payroll reviews across all EPC subcontractors prior to mechanical completion.

---
*Report generated autonomously by pwacheck v1.0.0 — IRA PWA Compliance Audit Desk.*
"""
    return report
