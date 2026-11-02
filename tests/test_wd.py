"""Unit tests for Wage Determination ingestion and parsing."""

import pytest
from pathlib import Path

from pwacheck.wd import (
    parse_wd_text,
    parse_wd_json,
    load_wage_determination,
    build_sam_gov_url,
)
from pwacheck.models import WageClassification, WageDetermination

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_build_sam_gov_url():
    url = build_sam_gov_url("IL20240008", rev=3)
    assert "https://sam.gov/api/prod/edms/v2/wage-determination-download" in url
    assert "wageDeterminations=IL20240008" in url
    assert "rev=3" in url


def test_parse_wd_text_fixture():
    txt_path = FIXTURES_DIR / "sample_wd_IL20240008.txt"
    assert txt_path.exists()

    wd = load_wage_determination(txt_path)
    assert wd.wd_id == "IL20240008"
    assert wd.state == "IL"
    assert wd.county == "Cook"
    assert len(wd.classifications) >= 4

    elec = wd.get_classification("ELECTRICIAN")
    assert elec is not None
    assert elec.basic_rate == 54.00
    assert elec.fringe_rate == 40.50
    assert elec.total_rate == 94.50

    lab = wd.get_classification("LABORER")
    assert lab is not None
    assert lab.basic_rate == 47.40
    assert lab.fringe_rate == 32.18
    assert lab.total_rate == 79.58


def test_parse_wd_json_fixture():
    json_path = FIXTURES_DIR / "sample_wd_IL20240008.json"
    assert json_path.exists()

    wd = load_wage_determination(json_path)
    assert wd.wd_id == "IL20240008"
    assert wd.revision == 3
    assert len(wd.classifications) == 5

    iron = wd.get_classification("IRONWORKER")
    assert iron is not None
    assert iron.basic_rate == 55.51
    assert iron.fringe_rate == 42.47
    assert iron.total_rate == 97.98


def test_classification_alias_lookup():
    wd = WageDetermination(
        wd_id="TEST001",
        state="IL",
        county="Cook",
    )
    wd.add_classification(WageClassification(trade="ELECTRICIAN", basic_rate=50.0, fringe_rate=30.0))
    wd.add_classification(WageClassification(trade="LABORER", basic_rate=40.0, fringe_rate=20.0))

    # Aliases
    assert wd.get_classification("Inside Wireman") is not None
    assert wd.get_classification("Journeyman Electrician") is not None
    assert wd.get_classification("General Laborer") is not None
    assert wd.get_classification("Construction Laborer") is not None
    assert wd.get_classification("NonExistentTrade") is None
