"""Form 4255 Part I Column (p) Investment Credit Recapture Risk Analysis."""

from typing import Dict, Any
from .models import Form4255Exposure, CureCalculation


def evaluate_form_4255_recapture(
    project_name: str,
    capacity_mw: float,
    eligible_basis: float,
    cure_calc_standard: CureCalculation,
    cure_calc_intentional: CureCalculation,
    full_credit_rate_pct: float = 30.0,
    base_credit_rate_pct: float = 6.0,
) -> Form4255Exposure:
    """Computes Form 4255 Part I column (p) recapture exposure and cure ROI.
    
    Under IRC Section 48 / 48E, failure to satisfy PWA requirements results in the forfeiture
    of the 5x credit multiplier, recapturing the tax credit from 30% down to the 6% statutory base rate.
    This 24% haircut is reported directly on Form 4255 Part I column (p).
    """
    full_credit = round(eligible_basis * (full_credit_rate_pct / 100.0), 2)
    base_credit = round(eligible_basis * (base_credit_rate_pct / 100.0), 2)
    recapture_exposure = round(full_credit - base_credit, 2)

    cure_cost_std = cure_calc_standard.grand_total_cure_exposure
    cure_cost_int = cure_calc_intentional.grand_total_cure_exposure

    net_savings = round(recapture_exposure - cure_cost_std, 2)
    roi_multiple = round(recapture_exposure / cure_cost_std, 1) if cure_cost_std > 0 else 999.9

    return Form4255Exposure(
        project_name=project_name,
        capacity_mw=capacity_mw,
        eligible_basis=round(eligible_basis, 2),
        full_credit_rate_pct=full_credit_rate_pct,
        base_credit_rate_pct=base_credit_rate_pct,
        full_credit_amount=full_credit,
        base_credit_amount=base_credit,
        recapture_exposure_col_p=recapture_exposure,
        cure_cost_standard=cure_cost_std,
        cure_cost_intentional=cure_cost_int,
        net_savings_from_cure=net_savings,
        roi_multiple=roi_multiple,
    )
