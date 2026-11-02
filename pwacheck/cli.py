"""Command Line Interface for pwacheck."""

import sys
import json
import argparse
from pathlib import Path

from .wd import load_wage_determination, fetch_sam_gov_wd
from .payroll import load_certified_payroll_csv
from .audit import audit_worker_shortfalls, audit_apprenticeship_compliance
from .cure import compute_ira_cure, compute_cure_comparison
from .form4255 import evaluate_form_4255_recapture
from .reporter import generate_pwa_health_check_report
from .gfe import generate_rap_request_letter, generate_5_day_tracker


def run_audit(args) -> int:
    """Executes a full PWA compliance audit."""
    print(f"Loading wage determination from: {args.wd}...")
    wd = load_wage_determination(args.wd)
    print(f"  Loaded WD {wd.wd_id} (Rev {wd.revision}, {wd.county} County, {wd.state}) with {len(wd.classifications)} classifications.")

    print(f"Loading certified payroll from: {args.payroll}...")
    payroll = load_certified_payroll_csv(args.payroll)
    print(f"  Loaded {len(payroll)} payroll records across {sum(r.total_hours for r in payroll):,.1f} total hours.")

    print("Auditing prevailing wage classifications and rates...")
    shortfalls, summary = audit_worker_shortfalls(payroll, wd, annual_interest_rate_pct=args.interest_rate)
    print(f"  Found {len(shortfalls)} underpaid workers with ${summary['total_wage_shortfall']:,.2f} gross wage shortfall.")

    print("Auditing apprentice utilization and daily ratios...")
    app_audit = audit_apprenticeship_compliance(payroll, threshold_pct=args.threshold)
    print(f"  Apprentice hours: {app_audit.apprentice_hours:,.1f} ({app_audit.apprentice_percentage:.1f}%), threshold: {app_audit.required_threshold_pct}%, deficient: {app_audit.deficient_labor_hours:,.1f} hrs.")

    print("Computing statutory cure math and IRS penalties...")
    cure_comp = compute_cure_comparison(shortfalls, app_audit, boc_year=args.boc_year, interest_rate_pct=args.interest_rate)
    std_cure = cure_comp["standard_cure"]
    int_cure = cure_comp["intentional_disregard"]
    std_cure.total_workers_audited = summary["total_workers"]
    int_cure.total_workers_audited = summary["total_workers"]

    print(f"  Standard Cure Due: ${std_cure.grand_total_cure_exposure:,.2f} (Worker backpay: ${std_cure.total_worker_backpay_due:,.2f}, IRS penalties: ${std_cure.total_irs_penalties:,.2f})")
    print(f"  Intentional Disregard Exposure: ${int_cure.grand_total_cure_exposure:,.2f}")

    print("Evaluating Form 4255 Part I column (p) ITC recapture exposure...")
    f4255 = evaluate_form_4255_recapture(
        project_name=args.project,
        capacity_mw=args.capacity,
        eligible_basis=args.basis,
        cure_calc_standard=std_cure,
        cure_calc_intentional=int_cure,
    )
    print(f"  Form 4255 Part I col (p) Recapture Exposure: ${f4255.recapture_exposure_col_p:,.2f}")
    print(f"  Net Savings from Proactive Cure: ${f4255.net_savings_from_cure:,.2f} ({f4255.roi_multiple:.1f}x ROI)")

    if args.report:
        report_md = generate_pwa_health_check_report(
            project_name=args.project,
            capacity_mw=args.capacity,
            county=args.county or wd.county,
            state=args.state or wd.state,
            boc_year=args.boc_year,
            eligible_basis=args.basis,
            wage_determination=wd,
            shortfalls=shortfalls,
            apprentice_audit=app_audit,
            cure_standard=std_cure,
            cure_intentional=int_cure,
            form_4255=f4255,
        )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_md, encoding="utf-8")
        print(f"\n[OK] Client-Ready PWA Compliance Health-Check Report saved to: {report_path.resolve()}")

    if args.json:
        res = {
            "project": args.project,
            "wd_id": wd.wd_id,
            "summary": summary,
            "apprentice_audit": app_audit.model_dump(),
            "cure_standard": std_cure.model_dump(),
            "cure_intentional": int_cure.model_dump(),
            "form_4255": f4255.model_dump(),
            "shortfalls": [s.model_dump() for s in shortfalls],
        }
        print(json.dumps(res, indent=2))

    return 0


def run_gfe(args) -> int:
    """Generates Apprentice Good Faith Effort packet."""
    if args.letter:
        letter = generate_rap_request_letter(
            contractor_name=args.contractor,
            contractor_contact_name=args.contact,
            contractor_email=args.email,
            contractor_phone=args.phone,
            project_name=args.project,
            facility_location=args.location,
            program_name=args.program,
            program_contact_name=args.program_contact,
            program_address=args.program_address,
            trade_name=args.trade,
            num_apprentices_needed=args.needed,
            expected_start_date=args.start_date,
            expected_hours_per_week=args.hours,
            hourly_wage_offered=args.wage,
            hourly_fringe_offered=args.fringe,
        )
        if args.out:
            Path(args.out).write_text(letter, encoding="utf-8")
            print(f"[OK] RAP Request Letter saved to: {args.out}")
        else:
            print(letter)

    if args.tracker:
        sample_requests = [
            {
                "request_id": "RAP-REQ-001",
                "program_name": args.program or "IBEW Local 134 JATC",
                "trade": args.trade or "Electrician",
                "request_date": "2024-05-01",
                "delivery_proof": "Email Read Receipt #4812 & USPS Cert #7021",
                "status": "No Response",
            },
            {
                "request_id": "RAP-REQ-002",
                "program_name": "Midwest Operating Engineers Apprenticeship",
                "trade": "Equipment Operator",
                "request_date": "2024-05-03",
                "delivery_proof": "USPS Certified Mail #7022-9182",
                "status": "Denied",
            },
        ]
        tracker = generate_5_day_tracker(sample_requests)
        if args.out:
            Path(args.out).write_text(tracker, encoding="utf-8")
            print(f"[OK] 5-Day Tracker saved to: {args.out}")
        else:
            print(tracker)

    return 0


def main():
    parser = argparse.ArgumentParser(prog="pwacheck", description="IRA Prevailing Wage & Apprenticeship Compliance Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: audit
    p_audit = subparsers.add_parser("audit", help="Run forensic certified payroll compliance audit")
    p_audit.add_argument("--wd", required=True, help="Wage determination file path (.txt, .json, .pdf) or SAM.gov ID")
    p_audit.add_argument("--payroll", required=True, help="Certified payroll CSV file")
    p_audit.add_argument("--project", default="Prairie View Solar", help="Project name")
    p_audit.add_argument("--capacity", type=float, default=10.0, help="Project capacity in MW")
    p_audit.add_argument("--basis", type=float, default=15000000.0, help="Eligible basis / CapEx in USD")
    p_audit.add_argument("--boc-year", type=int, default=2024, help="Beginning of Construction year")
    p_audit.add_argument("--threshold", type=float, default=15.0, help="Apprentice hours threshold percentage")
    p_audit.add_argument("--county", default=None, help="Project county override")
    p_audit.add_argument("--state", default=None, help="Project state override")
    p_audit.add_argument("--interest-rate", type=float, default=11.0, help="IRC 6621 interest rate percentage")
    p_audit.add_argument("--report", default=None, help="Path to write client-ready Markdown report")
    p_audit.add_argument("--json", action="store_true", help="Output audit results as JSON")

    # Subcommand: gfe
    p_gfe = subparsers.add_parser("gfe", help="Generate Apprentice Good Faith Effort packet")
    p_gfe.add_argument("--letter", action="store_true", help="Generate RAP Request Letter")
    p_gfe.add_argument("--tracker", action="store_true", help="Generate 5-Business-Day Tracker")
    p_gfe.add_argument("--contractor", default="Apex Clean Energy EPC", help="Contractor company name")
    p_gfe.add_argument("--contact", default="Robert Ketler", help="Contractor contact name")
    p_gfe.add_argument("--email", default="compliance@apexepc.com", help="Contractor email")
    p_gfe.add_argument("--phone", default="(555) 392-1084", help="Contractor phone")
    p_gfe.add_argument("--project", default="Prairie View Solar Farm", help="Project name")
    p_gfe.add_argument("--location", default="Morgan County, IL", help="Project location")
    p_gfe.add_argument("--program", default="IBEW Local 134 JATC", help="Registered Apprenticeship Program name")
    p_gfe.add_argument("--program-contact", default="Apprenticeship Coordinator", help="Program contact person")
    p_gfe.add_argument("--program-address", default="6201 W. 115th St, Alsip, IL 60803", help="Program mailing address")
    p_gfe.add_argument("--trade", default="Inside Wireman / Electrician", help="Trade name")
    p_gfe.add_argument("--needed", type=int, default=4, help="Number of apprentices needed")
    p_gfe.add_argument("--start-date", default="2024-06-15", help="Work start date")
    p_gfe.add_argument("--hours", type=float, default=40.0, help="Hours per week")
    p_gfe.add_argument("--wage", type=float, default=38.00, help="Hourly base rate offered")
    p_gfe.add_argument("--fringe", type=float, default=24.50, help="Hourly fringe rate offered")
    p_gfe.add_argument("--out", default=None, help="Output file path")

    args = parser.parse_args()
    if args.command == "audit":
        sys.exit(run_audit(args))
    elif args.command == "gfe":
        sys.exit(run_gfe(args))


if __name__ == "__main__":
    main()
