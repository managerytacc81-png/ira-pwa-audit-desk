"""Apprentice Good Faith Effort (GFE) packet generator per IRC 45(b)(8)(D)(ii) & Reg. 1.45-8(f)."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


def calculate_business_days(start_date: datetime, num_days: int = 5) -> datetime:
    """Adds a given number of business days (skipping weekends)."""
    current = start_date
    added = 0
    while added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday to Friday
            added += 1
    return current


def generate_rap_request_letter(
    contractor_name: str,
    contractor_contact_name: str,
    contractor_email: str,
    contractor_phone: str,
    project_name: str,
    facility_location: str,
    program_name: str,
    program_contact_name: str,
    program_address: str,
    trade_name: str,
    num_apprentices_needed: int,
    expected_start_date: str,
    expected_hours_per_week: float = 40.0,
    hourly_wage_offered: float = 35.00,
    hourly_fringe_offered: float = 18.50,
    letter_date: Optional[str] = None,
) -> str:
    """Generates a formal RAP Request Letter satisfying all mandatory criteria under Reg. 1.45-8(f)."""
    l_date = letter_date or datetime.now().strftime("%B %d, %Y")

    letter = f"""# FORMAL REQUEST FOR REGISTERED APPRENTICES
**Pursuant to IRC § 45(b)(8)(D)(ii) and Treasury Regulation § 1.45-8(f)**

**Date:** {l_date}  
**Via:** Electronic Mail with Read Receipt & Certified Mail, Return Receipt Requested  

**TO:**  
{program_contact_name}  
{program_name}  
{program_address}  

**FROM:**  
{contractor_contact_name}  
{contractor_name}  
Email: {contractor_email} | Phone: {contractor_phone}  

---

**SUBJECT: Request for Qualified Apprentices — {project_name} ({facility_location})**

Dear {program_contact_name}:

This letter constitutes a formal written request by **{contractor_name}** for qualified apprentices registered with **{program_name}** to perform construction labor on the **{project_name}** facility located in **{facility_location}**, in strict accordance with the apprenticeship provisions of Internal Revenue Code (IRC) § 45(b)(8) and Treasury Regulation § 1.45-8(f) (T.D. 9998).

### 1. Project & Labor Specification
* **Facility / Project Name:** {project_name}
* **Project Location:** {facility_location}
* **Apprenticeable Craft / Trade:** {trade_name}
* **Number of Qualified Apprentices Requested:** {num_apprentices_needed}
* **Anticipated Work Start Date:** {expected_start_date}
* **Expected Hours Per Week:** {expected_hours_per_week} hours per apprentice
* **Total Estimated Labor Duration:** Project construction period

### 2. Prevailing Wage & Benefits Commitment
Apprentices dispatched under this request will receive wages and bona fide fringe benefits in full compliance with the applicable Davis-Bacon Wage Determination published by the U.S. Department of Labor:
* **Hourly Base Wage:** ${hourly_wage_offered:.2f} / hour (or the applicable apprentice stage percentage of the journeyworker basic rate)
* **Hourly Fringe Benefits:** ${hourly_fringe_offered:.2f} / hour
* **Total Prevailing Hourly Rate:** ${hourly_wage_offered + hourly_fringe_offered:.2f} / hour

### 3. Affirmative Equal Opportunity Commitment
{contractor_name} is an equal opportunity employer and agrees to employ apprentices in complete compliance with the standards, rules, and ratio requirements of the Registered Apprenticeship Program, as well as all applicable federal, state, and local non-discrimination and affirmative action mandates.

### 4. Statutory 5-Business-Day Response Notice
Under Treasury Regulation § 1.45-8(f)(1)(ii), your program has **five (5) business days** from the date of receipt of this request to respond in writing indicating whether you can dispatch the requested number of qualified apprentices.

If this request is denied in whole or in part, or if no written response is received within five (5) business days, {contractor_name} and the project taxpayer will rely upon this record to establish the statutory **Good Faith Effort (GFE) Exception** pursuant to IRC § 45(b)(8)(D)(ii), exempting the facility from apprenticeship deficiency penalties.

Please confirm receipt of this request immediately and deliver your response to:
* **Attn:** {contractor_contact_name}
* **Email:** {contractor_email}
* **Direct Phone:** {contractor_phone}

Respectfully submitted,

____________________________________________  
**{contractor_contact_name}**  
{contractor_name}  
Authorized Compliance Officer  
"""
    return letter


def generate_5_day_tracker(
    requests: List[Dict[str, Any]],
    report_date: Optional[str] = None,
) -> str:
    """Generates a Markdown 5-Business-Day RAP Response Tracker Table and audit audit log."""
    r_date = report_date or datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# Registered Apprenticeship Program (RAP) 5-Business-Day Tracker",
        f"**Audit Status Date:** {r_date} | **Statutory Authority:** IRC § 45(b)(8)(D)(ii) & Reg. § 1.45-8(f)",
        "",
        "| Request ID | Program Name | Trade | Request Date | Delivery Proof | 5-Day Deadline | Status | GFE Exception Triggered? | Validity Expiration |",
        "|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for req in requests:
        req_id = req.get("request_id", "REQ-001")
        program = req.get("program_name", "Local JATC")
        trade = req.get("trade", "Electrician")
        req_date_str = req.get("request_date", "2024-05-01")
        delivery_proof = req.get("delivery_proof", "Email Read Receipt #9948")
        status = req.get("status", "No Response").strip()

        try:
            req_dt = datetime.strptime(req_date_str, "%Y-%m-%d")
        except Exception:
            req_dt = datetime.now()

        deadline_dt = calculate_business_days(req_dt, 5)
        deadline_str = deadline_dt.strftime("%Y-%m-%d")

        # Reg 1.45-8(f)(2): valid for 120 days from request, or 365 days if no response
        if status.lower() in ("no response", "unanswered"):
            validity_days = 365
            gfe_triggered = "✅ YES (Day 6)"
        elif status.lower() in ("denied", "partially denied"):
            validity_days = 120
            gfe_triggered = "✅ YES (Immediate)"
        elif status.lower() in ("accepted", "fulfilled"):
            validity_days = 120
            gfe_triggered = "N/A (Dispatched)"
        else:
            validity_days = 120
            gfe_triggered = "⏳ Pending"

        exp_dt = req_dt + timedelta(days=validity_days)
        exp_str = exp_dt.strftime("%Y-%m-%d")

        lines.append(
            f"| {req_id} | {program} | {trade} | {req_date_str} | {delivery_proof} | {deadline_str} | **{status}** | {gfe_triggered} | {exp_str} |"
        )

    lines.extend([
        "",
        "> [!IMPORTANT] Statutory Compliance Guidance (Treasury Decision 9998):",
        "> 1. **5-Business-Day Clock:** The 5-day window begins on the first business day following verifiable receipt (certified mail return receipt or email server read receipt).",
        "> 2. **Substantive Denial Rule:** A denial qualifies for GFE *only* if the contractor agreed to the program's standard terms. Denials caused by refusal to pay customary sponsor fees or sign standard apprentice agreements do not qualify.",
        "> 3. **Renewal Mandate:** If apprentices remain deficient after the validity window (120 days for denials; 365 days for non-response), the request must be renewed in writing.",
    ])

    return "\n".join(lines)
