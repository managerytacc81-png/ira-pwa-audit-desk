"""Unit tests for Apprentice Good Faith Effort packet generator."""

import pytest
from datetime import datetime

from pwacheck.gfe import (
    calculate_business_days,
    generate_rap_request_letter,
    generate_5_day_tracker,
)


def test_calculate_business_days():
    # Thursday -> +5 business days = Friday(1), Mon(2), Tue(3), Wed(4), Thu(5)
    start_thursday = datetime(2024, 5, 2)  # Thursday
    due = calculate_business_days(start_thursday, 5)
    assert due.strftime("%Y-%m-%d") == "2024-05-09"  # Next Thursday


def test_generate_rap_request_letter():
    letter = generate_rap_request_letter(
        contractor_name="Apex Solar EPC",
        contractor_contact_name="Robert Ketler",
        contractor_email="compliance@apexsolar.com",
        contractor_phone="(555) 392-1084",
        project_name="Prairie View Solar",
        facility_location="Morgan County, IL",
        program_name="IBEW Local 134 JATC",
        program_contact_name="Apprenticeship Director",
        program_address="6201 W 115th St, Alsip, IL",
        trade_name="Inside Wireman",
        num_apprentices_needed=4,
        expected_start_date="2024-06-15",
        expected_hours_per_week=40.0,
        hourly_wage_offered=38.00,
        hourly_fringe_offered=24.50,
    )

    # Mandatory elements per Reg. 1.45-8(f)
    assert "FORMAL REQUEST FOR REGISTERED APPRENTICES" in letter
    assert "IRC § 45(b)(8)(D)(ii)" in letter
    assert "Apex Solar EPC" in letter
    assert "Prairie View Solar" in letter
    assert "Morgan County, IL" in letter
    assert "Inside Wireman" in letter
    assert "4" in letter
    assert "$38.00" in letter
    assert "$24.50" in letter
    assert "five (5) business days" in letter
    assert "Good Faith Effort (GFE) Exception" in letter


def test_generate_5_day_tracker():
    requests = [
        {
            "request_id": "REQ-101",
            "program_name": "IBEW Local 134 JATC",
            "trade": "Electrician",
            "request_date": "2024-05-02",
            "delivery_proof": "Email Read Receipt #991",
            "status": "No Response",
        },
        {
            "request_id": "REQ-102",
            "program_name": "Midwest Operating Engineers",
            "trade": "Equipment Operator",
            "request_date": "2024-05-02",
            "delivery_proof": "USPS Cert #7021",
            "status": "Denied",
        },
    ]

    tracker = generate_5_day_tracker(requests, report_date="2024-05-15")
    assert "Registered Apprenticeship Program (RAP) 5-Business-Day Tracker" in tracker
    assert "REQ-101" in tracker
    assert "REQ-102" in tracker
    assert "No Response" in tracker
    assert "Denied" in tracker
    assert "✅ YES (Day 6)" in tracker
    assert "✅ YES (Immediate)" in tracker
    assert "2024-05-09" in tracker  # 5 business days after May 2
