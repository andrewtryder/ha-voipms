"""Test VoIP.ms data update coordinator."""

from datetime import datetime

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms_custom.api import VoipMsApiError
from custom_components.voipms_custom.const import CONF_DEFAULT_DID, DOMAIN


async def test_coordinator_continues_when_balance_fetch_fails(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator returns CDR data when balance fetch fails."""
    now = datetime.now()
    valid_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    mock_voipms_client.get_balance.side_effect = VoipMsApiError(
        "VoIP.ms REST API request failed: The read operation timed out"
    )
    mock_voipms_client.get_cdr.return_value = {
        "status": "success",
        "cdr": [
            {"date": valid_time_str, "description": "Incoming call"},
            {"date": valid_time_str, "description": "Outbound call"},
        ],
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.data is not None
    assert coordinator.data["balance"] is None
    assert coordinator.data["inbound_calls_24h"] == 1
    assert coordinator.data["outbound_calls_24h"] == 1

    balance_state = hass.states.get("sensor.voip_ms_account_balance")
    assert balance_state is not None
    assert balance_state.state == "unknown"
