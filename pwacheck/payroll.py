"""Certified payroll ingestion module (WH-347 and CSV exports)."""

import csv
import io
import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from .models import PayrollRecord

logger = logging.getLogger(__name__)


def normalize_column_name(col: str) -> str:
    """Normalizes header column names for flexible matching by stripping non-alphanumeric chars."""
    return "".join(c for c in col.lower() if c.isalnum())


def map_row_to_record(row: Dict[str, str], row_idx: int = 0) -> PayrollRecord:
    """Maps a raw CSV dictionary row to a strongly typed PayrollRecord."""
    norm_dict = {normalize_column_name(k): v.strip() for k, v in row.items() if k}

    # Worker ID
    worker_id = (
        norm_dict.get("workerid")
        or norm_dict.get("employeeid")
        or norm_dict.get("workernumber")
        or norm_dict.get("ssn")
        or norm_dict.get("id")
        or f"WKR-{row_idx + 1:03d}"
    )

    # Worker Name
    worker_name = (
        norm_dict.get("workername")
        or norm_dict.get("employeename")
        or norm_dict.get("name")
        or f"Worker {worker_id}"
    )

    # Contractor / Subcontractor
    contractor = (
        norm_dict.get("contractor")
        or norm_dict.get("subcontractor")
        or norm_dict.get("employer")
        or norm_dict.get("company")
        or "Prime Contractor"
    )

    # Reported Trade
    reported_trade = (
        norm_dict.get("reportedtrade")
        or norm_dict.get("trade")
        or norm_dict.get("classification")
        or norm_dict.get("workclassification")
        or norm_dict.get("jobtitle")
        or "Laborer"
    )

    # Actual Trade (for misclassification detection)
    actual_trade = (
        norm_dict.get("actualtrade")
        or norm_dict.get("performedtrade")
        or norm_dict.get("workperformed")
        or None
    )

    # Work Date
    work_date = (
        norm_dict.get("workdate")
        or norm_dict.get("date")
        or norm_dict.get("weekending")
        or norm_dict.get("weekendingdate")
        or "2024-06-01"
    )

    # Hours
    def _parse_float(val: Optional[str], default: float = 0.0) -> float:
        if not val:
            return default
        try:
            return float(val.replace("$", "").replace(",", "").strip())
        except ValueError:
            return default

    reg_hours = _parse_float(
        norm_dict.get("regularhours")
        or norm_dict.get("reghours")
        or norm_dict.get("hoursregular")
        or norm_dict.get("hours")
    )

    ot_hours = _parse_float(
        norm_dict.get("overtimehours")
        or norm_dict.get("othours")
        or norm_dict.get("hoursovertime")
    )

    # Rates paid
    base_paid = _parse_float(
        norm_dict.get("hourlybasepaid")
        or norm_dict.get("baserate")
        or norm_dict.get("hourlyrate")
        or norm_dict.get("rateofpay")
        or norm_dict.get("basepaid")
    )

    fringe_paid = _parse_float(
        norm_dict.get("hourlyfringepaid")
        or norm_dict.get("fringerate")
        or norm_dict.get("fringepaid")
        or norm_dict.get("fringebenefits")
    )

    total_paid_raw = _parse_float(
        norm_dict.get("totalratepaid")
        or norm_dict.get("totalpaid")
        or norm_dict.get("totalrate")
    )
    total_paid = total_paid_raw if total_paid_raw > 0.0 else round(base_paid + fringe_paid, 2)

    # Apprentice status
    app_val = (
        norm_dict.get("isapprentice")
        or norm_dict.get("apprentice")
        or norm_dict.get("apprenticestatus")
        or ""
    ).lower()
    is_apprentice = app_val in ("true", "1", "yes", "y", "t", "apprentice")

    app_prog_id = (
        norm_dict.get("apprenticeprogramid")
        or norm_dict.get("rapprogramid")
        or norm_dict.get("programid")
    )

    app_ratio = _parse_float(
        norm_dict.get("apprenticeratio")
        or norm_dict.get("apprenticeperiodratio")
        or norm_dict.get("periodratio"),
        default=1.0,
    )

    return PayrollRecord(
        worker_id=worker_id,
        worker_name=worker_name,
        contractor=contractor,
        reported_trade=reported_trade,
        actual_trade=actual_trade,
        work_date=work_date,
        regular_hours=reg_hours,
        overtime_hours=ot_hours,
        hourly_base_paid=base_paid,
        hourly_fringe_paid=fringe_paid,
        total_rate_paid=total_paid,
        is_apprentice=is_apprentice,
        apprentice_program_id=app_prog_id,
        apprentice_period_ratio=app_ratio,
    )


def load_certified_payroll_csv(source: Union[str, Path, io.StringIO, io.BytesIO]) -> List[PayrollRecord]:
    """Loads and parses a certified payroll CSV file or stream."""
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        with open(source, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            return [map_row_to_record(row, idx) for idx, row in enumerate(reader) if any(row.values())]
    elif isinstance(source, io.StringIO):
        reader = csv.DictReader(source)
        return [map_row_to_record(row, idx) for idx, row in enumerate(reader) if any(row.values())]
    elif isinstance(source, io.BytesIO):
        text_stream = io.StringIO(source.getvalue().decode("utf-8-sig", errors="ignore"))
        reader = csv.DictReader(text_stream)
        return [map_row_to_record(row, idx) for idx, row in enumerate(reader) if any(row.values())]
    elif isinstance(source, str):
        # Raw CSV text
        text_stream = io.StringIO(source.strip())
        reader = csv.DictReader(text_stream)
        return [map_row_to_record(row, idx) for idx, row in enumerate(reader) if any(row.values())]
    else:
        raise ValueError(f"Unsupported payroll source format: {type(source)}")
