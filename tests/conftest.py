from pathlib import Path

import pytest


@pytest.fixture
def valid_fa3_invoice_xml() -> str:
    return (Path(__file__).parent / "fixtures" / "valid_fa3_invoice.xml").read_text(
        encoding="utf-8"
    )
