"""Test VoIP.ms sensors."""

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import DOMAIN, CONF_DEFAULT_DID


async def test_sensors(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test sensors are created and updated correctly."""

    now = datetime.now()
    valid_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    mock_voipms_client.get_balance.return_value = {
        "status": "success",
        "balance": 42.50,
    }
    mock_voipms_client.get_cdr.return_value = {
        "status": "success",
        "cdr": [
            {"date": valid_time_str, "description": "Incoming call"},
            {"date": valid_time_str, "description": "Outbound call"},
            {"date": valid_time_str, "description": "Inbound call"},
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

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    balance_state = hass.states.get("sensor.voip_ms_account_balance")
    assert balance_state is not None
    assert balance_state.state == "42.5"

    inbound_state = hass.states.get("sensor.voip_ms_inbound_calls_24h")
    assert inbound_state is not None
    assert inbound_state.state == "2"

    outbound_state = hass.states.get("sensor.voip_ms_outbound_calls_24h")
    assert outbound_state is not None
    assert outbound_state.state == "1"
