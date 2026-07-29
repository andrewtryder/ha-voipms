"""Test VoIP.ms data update coordinator."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_LOGBOOK_ENTRY
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN


async def test_coordinator_fails_when_balance_fetch_fails(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator raises UpdateFailed when core network fetch fails."""
    mock_voipms_client.get_balance.side_effect = VoipMsApiError(
        "VoIP.ms REST API request failed: The read operation timed out"
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

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # If get_balance fails, coordinator raises UpdateFailed which triggers a retry
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_coordinator_auth_failure(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on invalid credentials."""
    mock_voipms_client.get_balance.return_value = {"status": "invalid_credentials"}

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

    # Auth failure should put the entry into SETUP_ERROR
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_coordinator_subsystem_degradation(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator retains previous values on subsystem failure."""
    # First successful poll
    mock_voipms_client.get_balance.return_value = {
        "status": "success",
        "balance": 10.50,
    }
    mock_voipms_client.get_voicemails.return_value = {
        "status": "success",
        "voicemails": [{"mailbox": "100"}],
    }
    mock_voipms_client.get_voicemail_messages.return_value = {
        "status": "success",
        "messages": [{"id": "1"}, {"id": "2"}],
    }
    mock_voipms_client.get_cdr.return_value = {"status": "no_cdr"}
    mock_voipms_client.get_sub_accounts.return_value = {"status": "no_subaccounts"}

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

    coordinator = entry.runtime_data.coordinator
    assert coordinator.data["balance"] == 10.50
    assert coordinator.data["voicemail_count"] == 2

    # Second poll: balance succeeds, voicemails throw exception
    mock_voipms_client.get_balance.return_value = {"status": "success", "balance": 9.50}
    mock_voipms_client.get_voicemails.side_effect = VoipMsApiError("API timeout")

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # The balance updated, but the voicemail count should be retained
    assert coordinator.data["balance"] == 9.50
    assert coordinator.data["voicemail_count"] == 2


async def test_coordinator_processes_new_calls_on_subsequent_refresh(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test coordinator logs only newly seen calls after the initial seed poll."""
    now = dt_util.utcnow()
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

    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert len(logbook_events) == 1
    assert "Outbound call from 5551234567 to 5559876543" in logbook_events[0]["message"]
    assert logbook_events[0]["entity_id"] == "sensor.voip_ms_outbound_calls_24h"
