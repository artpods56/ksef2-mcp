from importlib.metadata import version

import pytest
from ksef2 import Environment

from ksef2_mcp.server import (
    available_client_features,
    environment_summary_payload,
    parse_environment,
    sdk_overview_payload,
)


def test_parse_environment_accepts_case_insensitive_names() -> None:
    assert parse_environment("test") is Environment.TEST
    assert parse_environment("Production") is Environment.PRODUCTION


def test_parse_environment_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Unsupported environment"):
        parse_environment("sandbox")


def test_sdk_overview_reports_installed_versions() -> None:
    payload = sdk_overview_payload()

    assert payload["ksef2_version"] == version("ksef2")
    assert payload["mcp_version"] == version("mcp")
    assert any(item["name"] == "TEST" for item in payload["environments"])
    assert "FA3" in payload["form_schemas"]


def test_available_client_features_include_testdata_only_in_test() -> None:
    assert "testdata" in available_client_features(Environment.TEST)
    assert "testdata" not in available_client_features(Environment.PRODUCTION)


def test_environment_summary_matches_environment() -> None:
    payload = environment_summary_payload("DEMO")

    assert payload["environment"] == "DEMO"
    assert payload["supports_testdata"] is False
    assert "authentication" in payload["client_features"]
