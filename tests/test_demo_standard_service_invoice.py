from ksef2_mcp.demo.standard_service_invoice import build_standard_service_invoice_xml


def test_demo_standard_service_invoice_xml_contains_realistic_mvp_fields() -> None:
    xml = build_standard_service_invoice_xml()

    assert "FV/03/2026/BA/001" in xml
    assert "BrightAnalytics Sp. z o.o." in xml
    assert "Northwind Studio Sp. z o.o." in xml
    assert "Monthly analytics and reporting subscription" in xml
    assert "Dashboard customization workshop" in xml
    assert "2026-03-27" in xml
    assert "2026-03-01" in xml
    assert "2026-03-31" in xml
    assert "1800.00" in xml
    assert "800.00" in xml
