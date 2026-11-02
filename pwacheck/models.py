"""Data models for IRA Prevailing Wage & Apprenticeship (PWA) compliance desk."""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class WageClassification(BaseModel):
    """Davis-Bacon Wage Determination classification entry."""
    trade: str
    basic_rate: float = Field(..., description="Hourly basic wage rate in USD")
    fringe_rate: float = Field(default=0.0, description="Hourly fringe benefits in USD")
    total_rate: float = Field(default=0.0, description="Total hourly prevailing wage (basic + fringe)")
    notes: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.total_rate == 0.0:
            self.total_rate = round(self.basic_rate + self.fringe_rate, 2)


class WageDetermination(BaseModel):
    """DOL SAM.gov Wage Determination specification."""
    wd_id: str = Field(..., description="Wage Determination Identifier, e.g. IL20240008")
    revision: int = Field(default=1, description="Revision number")
    state: str = Field(..., description="Two-letter state code, e.g. IL")
    county: str = Field(..., description="County name, e.g. Cook")
    construction_type: str = Field(default="Heavy / Solar", description="Building, Heavy, Highway, Residential")
    published_date: Optional[str] = Field(default=None, description="Publication or revision date (YYYY-MM-DD)")
    classifications: Dict[str, WageClassification] = Field(default_factory=dict)

    def add_classification(self, classification: WageClassification) -> None:
        key = classification.trade.strip().upper()
        self.classifications[key] = classification

    def get_classification(self, trade_name: str) -> Optional[WageClassification]:
        """Lookup classification with normalized matching and trade aliases."""
        if not trade_name:
            return None
        norm = trade_name.strip().upper()
        # Direct match
        if norm in self.classifications:
            return self.classifications[norm]

        # Aliases & common synonyms
        aliases = {
            "ELECTRICIAN": ["INSIDE WIREMAN", "ELECTRICIAN - INSIDE", "JOURNEYMAN ELECTRICIAN", "ELEC"],
            "LABORER": ["COMMON LABORER", "GENERAL LABORER", "CONSTRUCTION LABORER", "LABORER: COMMON OR GENERAL"],
            "IRONWORKER": ["STRUCTURAL IRONWORKER", "REINFORCING IRONWORKER", "IRON WORKER"],
            "POWER EQUIPMENT OPERATOR": ["OPERATING ENGINEER", "EQUIPMENT OPERATOR", "OPERATOR"],
            "CARPENTER": ["COMMERCIAL CARPENTER", "JOURNEYMAN CARPENTER"],
            "SOLAR INSTALLER": ["SOLAR PHOTOVOLTAIC INSTALLER", "PV INSTALLER", "SOLAR TECHNICIAN"],
        }

        # Check if trade_name matches any known alias target
        for std_key, alias_list in aliases.items():
            if norm == std_key or norm in alias_list:
                if std_key in self.classifications:
                    return self.classifications[std_key]
                for a in alias_list:
                    if a in self.classifications:
                        return self.classifications[a]

        # Partial substring match
        for key, val in self.classifications.items():
            if norm in key or key in norm:
                return val

        return None


class PayrollRecord(BaseModel):
    """Certified payroll record (WH-347 style line item)."""
    worker_id: str
    worker_name: str
    contractor: str
    reported_trade: str
    actual_trade: Optional[str] = None
    work_date: str = Field(..., description="Work date (YYYY-MM-DD)")
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    hourly_base_paid: float = 0.0
    hourly_fringe_paid: float = 0.0
    total_rate_paid: float = 0.0
    is_apprentice: bool = False
    apprentice_program_id: Optional[str] = None
    apprentice_period_ratio: float = 1.0  # e.g., 0.60 for 1st stage apprentice

    @property
    def total_hours(self) -> float:
        return round(self.regular_hours + self.overtime_hours, 2)

    def effective_trade(self) -> str:
        return (self.actual_trade or self.reported_trade).strip()


class WorkerShortfall(BaseModel):
    """Worker-level prevailing wage shortfall computation."""
    worker_id: str
    worker_name: str
    contractor: str
    reported_trade: str
    effective_trade: str
    total_hours: float
    shortfall_hours: float
    required_rate: float
    paid_rate: float
    hourly_shortfall: float
    gross_wage_shortfall: float
    interest_rate_pct: float
    interest_amount: float
    total_correction_due: float
    is_misclassified: bool = False
    misclassification_note: Optional[str] = None


class DailyRatioCheck(BaseModel):
    """Daily apprentice-to-journeyworker ratio validation."""
    work_date: str
    contractor: str
    trade: str
    journeyworker_count: int
    apprentice_count: int
    allowed_apprentice_count: int
    excess_apprentices: int
    is_compliant: bool
    notes: Optional[str] = None


class ApprenticeAuditResult(BaseModel):
    """Summary metrics of apprentice utilization under IRC 45(b)(8)."""
    total_labor_hours: float
    apprentice_hours: float
    apprentice_percentage: float
    required_threshold_pct: float = 15.0
    is_percentage_compliant: bool
    deficient_labor_hours: float
    contractors_monitored: int
    contractors_with_4plus_workers: int
    contractors_satisfying_participation: int
    daily_ratio_violations: List[DailyRatioCheck] = Field(default_factory=list)


class CureCalculation(BaseModel):
    """Statutory correction and penalty math per IRC 45(b)(7)(B) & 45(b)(8)(D)."""
    boc_year: int = Field(default=2024, description="Beginning of Construction Year")
    total_workers_audited: int
    underpaid_workers_count: int
    total_labor_hours: float
    total_shortfall_hours: float
    total_gross_wage_shortfall: float
    interest_rate_pct: float
    total_interest_due: float
    total_worker_backpay_due: float

    # Prevailing wage penalty (IRC 45(b)(7)(B)(i)(II) / (iii))
    prevailing_wage_penalty_rate: float
    prevailing_wage_penalty_total: float

    # Apprentice deficiency penalty (IRC 45(b)(8)(D))
    apprentice_deficient_hours: float
    apprentice_penalty_rate: float
    apprentice_penalty_total: float

    total_irs_penalties: float
    grand_total_cure_exposure: float
    is_intentional_disregard: bool = False


class Form4255Exposure(BaseModel):
    """Form 4255 Part I column (p) ITC recapture exposure assessment."""
    project_name: str
    capacity_mw: float
    eligible_basis: float = Field(..., description="Project eligible basis / CapEx in USD")
    full_credit_rate_pct: float = 30.0
    base_credit_rate_pct: float = 6.0
    full_credit_amount: float
    base_credit_amount: float
    recapture_exposure_col_p: float
    cure_cost_standard: float
    cure_cost_intentional: float
    net_savings_from_cure: float
    roi_multiple: float
