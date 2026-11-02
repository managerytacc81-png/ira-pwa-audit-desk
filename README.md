# IRA PWA Compliance Audit Desk (`pwacheck`)

[![CI Tests](https://img.shields.io/badge/pytest-100%25%20passed-brightgreen.svg)]()
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)]()
[![Treasury Decision](https://img.shields.io/badge/IRS%20Regs-T.D.%209998%20%7C%2089%20FR%2053184-orange.svg)]()
[![Statutory Framework](https://img.shields.io/badge/IRC-%C2%A7%C2%A7%2045(b)(7)%20%7C%2045(b)(8)%20%7C%2048(a)(9)-purple.svg)]()

Production-grade forensic compliance verification toolkit for the **Inflation Reduction Act (IRA) Prevailing Wage and Apprenticeship (PWA)** requirements under Internal Revenue Code (IRC) §§ 45(b)(7), 45(b)(8), 48(a)(9), 48E, and Treasury Decision 9998 (89 FR 53184, June 25, 2024).

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Data Ingestion
        A1[SAM.gov DOL Wage Determination<br/>API URL / PDF / TXT / JSON] --> B1[pwacheck.wd<br/>Davis-Bacon Rate Parser]
        A2[Certified Payroll Exports<br/>WH-347 / CSV / Subcontractor] --> B2[pwacheck.payroll<br/>Record Ingestion Engine]
    end

    subgraph Forensic Audit Engine
        B1 --> C1[pwacheck.audit]
        B2 --> C1
        C1 --> D1[Per-Worker Wage Shortfalls<br/>Basic + Fringe Gap Identification]
        C1 --> D2[Misclassification Detector<br/>Electrician/Laborer Trade Integrity]
        C1 --> D3[Apprenticeship Metrics<br/>15% Threshold & Daily Ratio Audits]
    end

    subgraph Statutory Math & Exposure
        D1 --> E1[pwacheck.cure<br/>T.D. 9998 / IRC 45(b)(7)(B) Math]
        D2 --> E1
        D3 --> E1
        E1 --> F1[Sec 6621 + 6% Interest<br/>+ $5,000 / $10,000 PW Penalties<br/>+ $50 / $500 Deficient Hour Penalties]
        E1 --> F2[pwacheck.form4255<br/>Part I Col p Recapture Risk]
    end

    subgraph Defense & Output Deliverables
        F1 --> G1[pwacheck.reporter<br/>PWA Health-Check Report]
        F2 --> G1
        H1[pwacheck.gfe<br/>Good Faith Effort Generator] --> G2[RAP 5-Day Request Letter<br/>& Audit Trail Tracker]
```

---

## Statutory & Regulatory Framework

Under the IRA, clean energy generation (solar, wind, battery storage, clean hydrogen) eligible for the 30% full Investment Tax Credit (ITC) faces immediate forfeiture of the **5x credit multiplier** if prevailing wage and apprenticeship requirements are violated.

| Statutory Domain | Governing Law | Compliance Mandate | Non-Compliance / Audit Disallowance Penalty |
|:---|:---|:---|:---|
| **Prevailing Wage (PW)** | IRC § 45(b)(7)(A) | 100% of laborers and mechanics paid >= Davis-Bacon basic rate + bona fide fringe benefits | Recapture of 5x credit down to 6% base rate on Form 4255 Part I col (p) |
| **PW Statutory Cure** | IRC § 45(b)(7)(B)(i) | Timely payment of back-pay shortfall + interest at IRC § 6621 (Federal Short-term Rate + 6 percentage points) | IRS penalty of **$5,000 per underpaid worker per year** (Standard) |
| **PW Intentional Disregard** | IRC § 45(b)(7)(B)(iii) | Unremedied classification fraud or willful disregard of certified payroll standards | Worker backpay **triples (3x shortfall)** + IRS penalty doubles to **$10,000 per worker** |
| **Apprenticeship Labor Hours** | IRC § 45(b)(8)(A) | Qualified apprentices perform >= **15.0%** of total labor hours (for BOC 2024+) | IRS penalty of **$50 per deficient labor hour** ($500/hr if intentional disregard) |
| **Apprenticeship Daily Ratio** | IRC § 45(b)(8)(B) | Strict compliance with registered apprenticeship program daily apprentice-to-journeyworker ratios | Excess apprentice hours disqualified from 15% threshold; journeyworker prevailing rates due |
| **Contractor Participation** | IRC § 45(b)(8)(C) | Each contractor/subcontractor with 4+ workers must employ 1+ qualified apprentice | Penalty exposure under deficiency calculations |
| **Good Faith Effort (GFE)** | IRC § 45(b)(8)(D)(ii) | Written apprentice request submitted to local Registered Apprenticeship Program (RAP) | Full penalty exemption if denied or **unanswered after 5 business days** |

### The June 2024 Final Regulations Defense (T.D. 9998)
Under Treasury Regulation § 1.45-7(c)(6), taxpayers who establish **routine quarterly certified payroll reviews** and self-cure discovered shortfalls within 30 days establish a formal rebuttable presumption of **NO intentional disregard**. This shields developers from:
* The $10,000/worker penalty
* The $500/deficient-hour penalty
* The loss of the 5x tax credit multiplier on Form 4255.

---

## Key Capabilities

1. **DOL Wage Determination Ingestion (`pwacheck.wd`)**:
   - Automated fetching from SAM.gov via the official EDMS download URL pattern:
     `https://sam.gov/api/prod/edms/v2/wage-determination-download?wageDeterminations=<ID>&rev=<N>`
   - Direct text, JSON, and PDF parsing with trade alias fuzzy matching (e.g. "Inside Wireman" -> "Electrician").
2. **Certified Payroll Forensic Audit (`pwacheck.payroll`, `pwacheck.audit`)**:
   - Parses WH-347 and CSV certified payroll exports from prime EPCs and lower-tier subcontractors.
   - Detects worker underpayments (basic wage and fringe benefits shortfall).
   - Detects trade misclassifications (e.g., workers performing electrical cable pulling classified as general laborers).
3. **Exact Statutory Cure Math (`pwacheck.cure`)**:
   - Computes back pay shortfall + IRC § 6621 interest (+6 percentage points).
   - Calculates standard vs. intentional disregard penalties.
4. **Form 4255 Part I Column (p) Recapture Risk (`pwacheck.form4255`)**:
   - Quantifies the dollar value of the 5x multiplier haircut (24% of project eligible basis).
   - Demonstrates the return on compliance investment (ROI) of proactive cure.
5. **Client-Ready Report Generator (`pwacheck.reporter`)**:
   - Generates executive-ready, legally defensible Markdown audit reports with scorecard, worker shortfall findings, and cure roadmap.
6. **Apprentice Good Faith Effort (GFE) Suite (`pwacheck.gfe`)**:
   - Generates formal RAP Request Letters complying with all mandatory disclosures under Reg. § 1.45-8(f).
   - Generates 5-Business-Day response tracking tables and expiration calendars (120-day / 365-day validity windows).

---

## Installation

```bash
# Clone the repository
git clone https://github.com/managerytacc81-png/ira-pwa-audit-desk.git
cd ira-pwa-audit-desk

# Install in editable mode
pip install -e .
```

---

## Command Line Usage

### 1. Execute Full Forensic PWA Audit
```bash
pwacheck audit \
  --wd fixtures/sample_wd_IL20240008.json \
  --payroll fixtures/certified_payroll_misclassified.csv \
  --project "Prairie View Solar Farm" \
  --capacity 10.0 \
  --basis 15000000 \
  --boc-year 2024 \
  --report output/PWA_Health_Check_Report.md
```

### 2. Generate Apprentice Good Faith Effort Request Letter
```bash
pwacheck gfe \
  --letter \
  --contractor "Summit Ridge Energy EPC" \
  --project "Montgomery Solar IL 1" \
  --location "Montgomery County, IL" \
  --program "IBEW Local 134 JATC" \
  --trade "Inside Wireman" \
  --needed 4 \
  --start-date "2024-08-01" \
  --out output/RAP_Request_Letter.md
```

### 3. Generate 5-Business-Day Response Tracker
```bash
pwacheck gfe \
  --tracker \
  --out output/RAP_5_Day_Tracker.md
```

---

## Python API Example

```python
from pwacheck.wd import load_wage_determination
from pwacheck.payroll import load_certified_payroll_csv
from pwacheck.audit import audit_worker_shortfalls, audit_apprenticeship_compliance
from pwacheck.cure import compute_cure_comparison
from pwacheck.form4255 import evaluate_form_4255_recapture
from pwacheck.reporter import generate_pwa_health_check_report

# 1. Load Wage Determination & Certified Payroll
wd = load_wage_determination("fixtures/sample_wd_IL20240008.txt")
records = load_certified_payroll_csv("fixtures/certified_payroll_misclassified.csv")

# 2. Audit Shortfalls & Apprentice Ratios
shortfalls, summary = audit_worker_shortfalls(records, wd, annual_interest_rate_pct=11.0)
app_audit = audit_apprenticeship_compliance(records, threshold_pct=15.0)

# 3. Compute Cure Math
cure_comp = compute_cure_comparison(shortfalls, app_audit, boc_year=2024)

# 4. Form 4255 Part I Col (p) Recapture Risk
form_4255 = evaluate_form_4255_recapture(
    project_name="Prairie View Solar",
    capacity_mw=10.0,
    eligible_basis=15000000.0,
    cure_calc_standard=cure_comp["standard_cure"],
    cure_calc_intentional=cure_comp["intentional_disregard"],
)

# 5. Generate Client-Ready Report
report = generate_pwa_health_check_report(
    project_name="Prairie View Solar",
    capacity_mw=10.0,
    county="Cook",
    state="IL",
    boc_year=2024,
    eligible_basis=15000000.0,
    wage_determination=wd,
    shortfalls=shortfalls,
    apprentice_audit=app_audit,
    cure_standard=cure_comp["standard_cure"],
    cure_intentional=cure_comp["intentional_disregard"],
    form_4255=form_4255,
)
print(f"Audit completed: {len(shortfalls)} underpaid workers. Form 4255 exposure: ${form_4255.recapture_exposure_col_p:,.2f}")
```

---

## Test Verification

Run the comprehensive unit test suite:
```bash
pytest -v
```

All 22 unit tests verify:
- Compliant crews (0 shortfalls, >= 15% apprentice hours)
- Misclassified crews (trade mismatch detection, shortfall hours, underpayment dollar math)
- Apprentice failure crews (daily ratio violations, deficient hours calculation)
- T.D. 9998 cure math (Sec 6621+6% interest, $5,000/$10,000 penalties, $50/$500 apprentice penalties)
- Form 4255 Part I column (p) ITC recapture exposure (24% basis reduction)
- PDF and SAM.gov WD text parsing
- 5-business-day Good Faith Effort calculations

---

## License

Proprietary Commercial Delivery — IRA PWA Compliance Audit Desk.
