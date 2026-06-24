"""Global fixtures for VoIP.ms Custom integration tests."""

from unittest.mock import patch
import pytest


pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing."""
    yield


@pytest.fixture
def mock_voipms_client():
    """Mock the VoIP.ms REST client to prevent real API calls."""
    with (
        patch(
            "custom_components.voipms_custom.config_flow.VoipMsRestClient"
        ) as mock_client_flow,
        patch(
            "custom_components.voipms_custom.coordinator.VoipMsRestClient"
        ) as mock_client_coord,
        patch(
            "custom_components.voipms_custom.notify.VoipMsRestClient"
        ) as mock_client_notify,
        patch(
            "custom_components.voipms_custom.__init__.VoipMsRestClient"
        ) as mock_client_init,
    ):
        mock_instance = mock_client_flow.return_value
        mock_client_coord.return_value = mock_instance
        mock_client_notify.return_value = mock_instance
        mock_client_init.return_value = mock_instance

        mock_instance.get_balance.return_value = {
            "status": "success",
            "balance": 15.50,
        }
        mock_instance.get_cdr.return_value = {
            "status": "success",
            "cdr": [
                {"date": "2024-01-01 12:00:00", "description": "Incoming call"},
                {"date": "2024-01-01 13:00:00", "description": "Outbound call"},
            ],
        }
        mock_instance.set_sms.return_value = {"status": "success"}
        mock_instance.send_sms.return_value = {"status": "success"}

        yield mock_instance
