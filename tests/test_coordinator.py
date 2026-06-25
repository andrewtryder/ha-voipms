"""Test VoIP.ms data update coordinator."""

from datetime import datetime

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_LOGBOOK_ENTRY
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN


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


async def test_coordinator_processes_new_calls_on_subsequent_refresh(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator logs only newly seen calls after the initial seed poll."""
    now = datetime.now()
    valid_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    mock_voipms_client.get_cdr.return_value = {
        "status": "success",
        "cdr": [
            {
                "uniqueid": "call-1",
                "date": valid_time_str,
                "description": "Incoming call",
                "callerid": "5559876543",
                "destination": "5551234567",
                "duration": "45",
                "disposition": "ANSWERED",
            }
        ],
    }

    logbook_events: list = []
    hass.bus.async_listen(
        EVENT_LOGBOOK_ENTRY, lambda event: logbook_events.append(event.data)
    )

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
    assert len(logbook_events) == 0

    mock_voipms_client.get_cdr.return_value = {
        "status": "success",
        "cdr": [
            {
                "uniqueid": "call-1",
                "date": valid_time_str,
                "description": "Incoming call",
                "callerid": "5559876543",
                "destination": "5551234567",
                "duration": "45",
                "disposition": "ANSWERED",
            },
            {
                "uniqueid": "call-2",
                "date": valid_time_str,
                "description": "Outbound call",
                "callerid": "5551234567",
                "destination": "5559876543",
                "duration": "30",
                "disposition": "ANSWERED",
            },
        ],
    }

    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert len(logbook_events) == 1
    assert "Outbound call from 5551234567 to 5559876543" in logbook_events[0]["message"]
    assert logbook_events[0]["entity_id"] == "sensor.voip_ms_outbound_calls_24h"
