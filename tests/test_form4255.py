"""Unit tests for Form 4255 Part I column (p) ITC recapture exposure."""

import pytest

from pwacheck.form4255 import evaluate_form_4255_recapture
from pwacheck.models import CureCalculation


def test_form4255_recapture_math():
    # 10 MW solar facility with $15M eligible basis
    basis = 15000000.0
    capacity = 10.0

    dummy_cure_std = CureCalculation(
        boc_year=2024,
        total_workers_audited=10,
        underpaid_workers_count=3,
        total_labor_hours=400.0,
        total_shortfall_hours=120.0,
        total_gross_wage_shortfall=6879.20,
        interest_rate_pct=11.0,
        total_interest_due=350.00,
        total_worker_backpay_due=7229.20,
        prevailing_wage_penalty_rate=5000.0,
        prevailing_wage_penalty_total=15000.0,
        apprentice_deficient_hours=40.0,
        apprentice_penalty_rate=50.0,
        apprentice_penalty_total=2000.0,
        total_irs_penalties=17000.0,
        grand_total_cure_exposure=24229.20,
        is_intentional_disregard=False,
    )

    dummy_cure_int = dummy_cure_std.model_copy()
    dummy_cure_int.grand_total_cure_exposure = 70987.60

    exposure = evaluate_form_4255_recapture(
        project_name="Prairie View Solar",
        capacity_mw=capacity,
        eligible_basis=basis,
        cure_calc_standard=dummy_cure_std,
        cure_calc_intentional=dummy_cure_int,
    )

    # 30% credit: $4,500,000
    assert exposure.full_credit_amount == 4500000.0
    # 6% base credit: $900,000
    assert exposure.base_credit_amount == 900000.0
    # Form 4255 Part I col (p) recapture exposure: 24% = $3,600,000
    assert exposure.recapture_exposure_col_p == 3600000.0

    # Net savings: $3,600,000 - $24,229.20 = $3,575,770.80
    assert exposure.net_savings_from_cure == pytest.approx(3575770.80, 0.01)
    # ROI: 3,600,000 / 24,229.20 = ~148.6x
    assert exposure.roi_multiple > 100.0
