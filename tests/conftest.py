"""Global fixtures for VoIP.ms Custom integration tests."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest


pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing."""
    yield


@pytest.fixture(autouse=True)
def mock_voipms_client():
    """Mock the VoIP.ms REST client to prevent real API calls."""
    mock_instance = MagicMock()
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

    patch_targets = (
        "custom_components.voipms_custom.VoipMsRestClient",
        "custom_components.voipms_custom.config_flow.VoipMsRestClient",
        "custom_components.voipms_custom.coordinator.VoipMsRestClient",
        "custom_components.voipms_custom.notify.VoipMsRestClient",
        "custom_components.voipms_custom.api.VoipMsRestClient",
    )
    mock_class = MagicMock(return_value=mock_instance)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "custom_components.voipms_custom.get_url",
                return_value="http://example.com",
            )
        )
        for target in patch_targets:
            stack.enter_context(patch(target, mock_class))
        yield mock_instance
