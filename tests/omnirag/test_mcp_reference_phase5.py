import pytest

from extensions.omnirag.mcp.reference_server import calculate_availability, lookup_device, search_runbook


def test_reference_mcp_device_lookup_is_deterministic_and_read_only_data():
    out = lookup_device("gw-01")
    assert out["found"] is True
    assert out["record"]["role"] == "edge-gateway"


def test_reference_mcp_runbook_search():
    out = search_runbook("gateway reporting issue")
    assert out and out[0]["name"] == "gateway"


def test_reference_mcp_availability_validation():
    out = calculate_availability(1000, 10)
    assert out["availability_percent"] == 99.0
    with pytest.raises(ValueError):
        calculate_availability(0, 0)
