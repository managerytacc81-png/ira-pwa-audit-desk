"""Wage Determination ingestion and Davis-Bacon rate table parser.

Supports SAM.gov API download URL pattern:
https://sam.gov/api/prod/edms/v2/wage-determination-download?wageDeterminations=<ID>&rev=<N>
as well as local PDF, TXT, and JSON wage determinations.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import requests

from .models import WageClassification, WageDetermination

logger = logging.getLogger(__name__)

SAM_GOV_DOWNLOAD_URL = "https://sam.gov/api/prod/edms/v2/wage-determination-download"


def build_sam_gov_url(wd_id: str, rev: int = 1) -> str:
    """Constructs the official SAM.gov EDMS wage determination download URL."""
    return f"{SAM_GOV_DOWNLOAD_URL}?wageDeterminations={wd_id}&rev={rev}"


def fetch_sam_gov_wd(wd_id: str, rev: int = 1, timeout: int = 15) -> bytes:
    """Fetches a DOL Wage Determination from SAM.gov."""
    url = build_sam_gov_url(wd_id, rev)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/pdf,text/plain,application/json,*/*",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to fetch SAM.gov WD from {url}: {e}")
        raise RuntimeError(f"Unable to fetch SAM.gov WD {wd_id} rev {rev} from {url}: {e}")


def extract_text_from_pdf(pdf_bytes_or_path: Union[bytes, str, Path]) -> str:
    """Extract text from a PDF wage determination using pypdf."""
    try:
        from pypdf import PdfReader
        import io
        if isinstance(pdf_bytes_or_path, (str, Path)):
            reader = PdfReader(str(pdf_bytes_or_path))
        else:
            reader = PdfReader(io.BytesIO(pdf_bytes_or_path))
        text_pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_pages.append(t)
        return "\n".join(text_pages)
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise RuntimeError(f"Failed to extract text from PDF wage determination: {e}")


def parse_wd_text(text: str, default_wd_id: str = "WD-UNKNOWN") -> WageDetermination:
    """Parses Davis-Bacon Wage Determination text into a WageDetermination object."""
    # 1. Extract metadata
    wd_id_match = re.search(r"General Decision Number:\s*([A-Z0-9]+)", text, re.IGNORECASE)
    wd_id = wd_id_match.group(1).strip() if wd_id_match else default_wd_id

    rev_match = re.search(r"Modification Number:\s*(\d+)", text, re.IGNORECASE)
    rev = int(rev_match.group(1)) if rev_match else 1

    state_match = re.search(r"State:\s*([A-Za-z\s]+)", text)
    state = state_match.group(1).strip()[:2].upper() if state_match else "US"

    county_match = re.search(r"County\s*(?:or Description)?:\s*([A-Za-z\s]+?)(?:County|\n|$)", text, re.IGNORECASE)
    county = county_match.group(1).strip() if county_match else "General"

    construction_match = re.search(r"Construction Types?:\s*([A-Za-z\s,/]+)", text, re.IGNORECASE)
    construction_type = construction_match.group(1).strip() if construction_match else "Heavy / Solar"

    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    pub_date = date_match.group(1) if date_match else None

    wd = WageDetermination(
        wd_id=wd_id,
        revision=rev,
        state=state,
        county=county,
        construction_type=construction_type,
        published_date=pub_date,
    )

    # 2. Parse rate table entries
    lines = text.splitlines()

    # Pattern A: Tabular / pipe format: Trade | Basic | Fringe
    # Example: Electrician | 54.00 | 40.50
    pipe_pattern = re.compile(r"^\s*([A-Za-z0-9\s\-_/]+)\s*\|\s*\$?([0-9]+\.[0-9]{2})\s*\|\s*\$?([0-9]+\.[0-9]{2})")

    # Pattern B: Traditional Davis-Bacon dot-leader format:
    # Example: ELECTRICIAN.......................$ 54.00           40.50
    # or: Inside Wireman.................$ 54.00           40.50
    dot_pattern = re.compile(
        r"^\s*([A-Za-z0-9\s\-_/]+?)\.{3,}\s*\$?\s*([0-9]+\.[0-9]{2})\s+\$?\s*([0-9]+\.[0-9]{2})"
    )

    # Pattern C: Standard line format with rates column:
    # Example: Electrician       54.00     40.50
    col_pattern = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9\s\-_/]{3,35})\s{2,}\$?([0-9]{2,3}\.[0-9]{2})\s{2,}\$?([0-9]{1,3}\.[0-9]{2})"
    )

    current_trade_group = ""

    for line in lines:
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("==") or cleaned.startswith("--"):
            continue

        # Check pipe pattern
        pm = pipe_pattern.match(line)
        if pm:
            trade = pm.group(1).strip().upper()
            basic = float(pm.group(2))
            fringe = float(pm.group(3))
            wd.add_classification(WageClassification(trade=trade, basic_rate=basic, fringe_rate=fringe))
            continue

        # Check dot-leader pattern
        dm = dot_pattern.match(line)
        if dm:
            subtrade = dm.group(1).strip()
            trade_name = f"{current_trade_group} - {subtrade}" if current_trade_group and current_trade_group not in subtrade.upper() else subtrade
            basic = float(dm.group(2))
            fringe = float(dm.group(3))
            wd.add_classification(WageClassification(trade=trade_name.strip().upper(), basic_rate=basic, fringe_rate=fringe))
            continue

        # Check column pattern
        cm = col_pattern.match(line)
        if cm:
            name = cm.group(1).strip().upper()
            # Ignore headers
            if "RATES" in name or "CLASSIFICATION" in name:
                continue
            basic = float(cm.group(2))
            fringe = float(cm.group(3))
            wd.add_classification(WageClassification(trade=name, basic_rate=basic, fringe_rate=fringe))
            continue

        # Check trade group header like "ELEC0134-001 06/05/2023" or "ELECTRICIAN"
        if re.match(r"^[A-Z]{3,5}\d{3,5}-\d{3}", cleaned):
            continue
        if len(cleaned) < 40 and cleaned.isupper() and not any(ch.isdigit() for ch in cleaned):
            if "COUNTY" not in cleaned and "STATE" not in cleaned and "PAGE" not in cleaned:
                current_trade_group = cleaned

    return wd


def parse_wd_json(data: Union[str, Dict[str, Any]]) -> WageDetermination:
    """Parses JSON-structured wage determination."""
    if isinstance(data, str):
        obj = json.loads(data)
    else:
        obj = data

    classifications = {}
    for item in obj.get("classifications", []):
        trade = item.get("trade", "").strip().upper()
        basic = float(item.get("basic_rate", 0.0))
        fringe = float(item.get("fringe_rate", 0.0))
        total = float(item.get("total_rate", basic + fringe))
        wc = WageClassification(
            trade=trade,
            basic_rate=basic,
            fringe_rate=fringe,
            total_rate=total,
            notes=item.get("notes"),
        )
        classifications[trade] = wc

    return WageDetermination(
        wd_id=obj.get("wd_id", "WD-JSON"),
        revision=int(obj.get("revision", 1)),
        state=obj.get("state", "US"),
        county=obj.get("county", "General"),
        construction_type=obj.get("construction_type", "Heavy / Solar"),
        published_date=obj.get("published_date"),
        classifications=classifications,
    )


def load_wage_determination(source: Union[str, Path, bytes], wd_id: Optional[str] = None, rev: int = 1) -> WageDetermination:
    """Unified entrypoint to load a Wage Determination from a file path, raw bytes, or SAM.gov URL."""
    if isinstance(source, (str, Path)):
        src_str = str(source)
        # Check if URL
        if src_str.startswith("http://") or src_str.startswith("https://"):
            content = fetch_sam_gov_wd(wd_id or "WD-NET", rev=rev)
            return parse_wd_text(content.decode("utf-8", errors="ignore"), default_wd_id=wd_id or "WD-NET")

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Wage determination file not found at: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                return parse_wd_json(f.read())
        elif suffix == ".pdf":
            text = extract_text_from_pdf(path)
            return parse_wd_text(text, default_wd_id=wd_id or path.stem)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return parse_wd_text(f.read(), default_wd_id=wd_id or path.stem)
    elif isinstance(source, bytes):
        # Determine if PDF by magic bytes %PDF
        if source.startswith(b"%PDF"):
            text = extract_text_from_pdf(source)
            return parse_wd_text(text, default_wd_id=wd_id or "WD-PDF")
        else:
            try:
                # Try JSON
                data = json.loads(source.decode("utf-8"))
                return parse_wd_json(data)
            except Exception:
                return parse_wd_text(source.decode("utf-8", errors="ignore"), default_wd_id=wd_id or "WD-BYTES")
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")
