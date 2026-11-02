"""Unit tests for PDF extraction and SAM.gov network fetching."""

import io
import pytest
from unittest.mock import patch, MagicMock
from pwacheck.wd import (
    extract_text_from_pdf,
    fetch_sam_gov_wd,
    load_wage_determination,
)


def test_pdf_extraction_fallback_or_mock():
    # Test extract_text_from_pdf with mock reader
    with patch("pypdf.PdfReader") as mock_reader_cls:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "General Decision Number: IL20240008\n"
            "State: Illinois\n"
            "County: Cook\n"
            "ELECTRICIAN.......................$ 54.00           40.50\n"
            "LABORER...........................$ 47.40           32.18\n"
        )
        mock_instance = MagicMock()
        mock_instance.pages = [mock_page]
        mock_reader_cls.return_value = mock_instance

        fake_pdf = b"%PDF-1.4 dummy pdf bytes"
        text = extract_text_from_pdf(fake_pdf)
        assert "General Decision Number: IL20240008" in text
        assert "ELECTRICIAN" in text

        wd = load_wage_determination(fake_pdf)
        assert wd.wd_id == "IL20240008"
        assert wd.get_classification("Electrician") is not None


def test_fetch_sam_gov_wd_mock():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = (
            b"General Decision Number: OH20240001\n"
            b"State: Ohio\n"
            b"County: Franklin\n"
            b"ELECTRICIAN.......................$ 52.00           38.00\n"
        )
        mock_get.return_value = mock_resp

        content = fetch_sam_gov_wd("OH20240001", rev=1)
        assert b"OH20240001" in content
        assert mock_get.called
        assert "wageDeterminations=OH20240001" in mock_get.call_args[0][0]
