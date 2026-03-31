from pathlib import Path

from ksef2 import Environment

from ksef2_mcp.config import AppSettings, Capability, KsefAuthMode


def test_settings_parse_comma_separated_env_lists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KSEF_MCP_ENVIRONMENT", "TEST")
    monkeypatch.setenv("KSEF_MCP_NIP", "5261040828")
    monkeypatch.setenv("KSEF_MCP_AUTH_MODE", KsefAuthMode.TEST_CERTIFICATE.value)
    monkeypatch.setenv(
        "KSEF_MCP_CAPABILITIES",
        "upload_invoice_xml,send_invoice,get_submission_status",
    )
    monkeypatch.setenv("KSEF_MCP_REQUIRED_SCOPES", "ksef:mcp,offline_access")

    settings = AppSettings()

    assert settings.environment is Environment.TEST
    assert settings.capabilities == [
        Capability.UPLOAD_INVOICE_XML,
        Capability.SEND_INVOICE,
        Capability.GET_SUBMISSION_STATUS,
    ]
    assert settings.required_scopes == ["ksef:mcp", "offline_access"]
