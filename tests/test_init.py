"""Test VoIP.ms setup and unload."""

from homeassistant.components.persistent_notification import (
    _async_get_or_create_notifications,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    build_webhook_callback_url,
)
from custom_components.voipms.models import InboundSms
from custom_components.voipms.processor import process_inbound_sms


async def test_setup_unload_entry(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test setup and unload of the integration."""
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

    assert hasattr(entry, "runtime_data")
    assert entry.runtime_data is not None

    mock_voipms_client.set_sms.assert_called_once()
    call_kwargs = mock_voipms_client.set_sms.call_args.kwargs
    expected_url = build_webhook_callback_url(
        "http://example.com", f"voipms_{entry.unique_id}"
    )
    assert call_kwargs["url_callback"] == expected_url

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert getattr(entry, "runtime_data", None) is None


async def test_inbound_sms_event_creates_persistent_notification(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test inbound SMS events create persistent notifications."""
    assert await async_setup_component(hass, "persistent_notification", {})

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

    sms = InboundSms(
        sender="5559876543",
        recipient="5551234567",
        message="hello",
        message_id="42",
        timestamp="2024-01-01",
    )
    await process_inbound_sms(hass, entry, sms)
    await hass.async_block_till_done()

    notifications = _async_get_or_create_notifications(hass)
    expected_id = f"voipms_{entry.unique_id}_sms_42"
    assert expected_id in notifications
    assert notifications[expected_id]["message"] == "hello"
    assert notifications[expected_id]["title"] == "SMS from ******6543"


async def test_setup_entry_not_ready(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test ConfigEntryNotReady when API validation fails during setup."""
    from custom_components.voipms.api import VoipMsApiError

    mock_voipms_client.get_balance.side_effect = VoipMsApiError("Network timeout")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    assert not result


async def test_multi_entry_setup_and_unload(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test multiple entries can be set up and unloaded cleanly."""
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry1",
        data={
            CONF_USERNAME: "user1",
            CONF_PASSWORD: "password",
            CONF_DEFAULT_DID: "5551111111",
        },
        unique_id="user1",
    )
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry2",
        data={
            CONF_USERNAME: "user2",
            CONF_PASSWORD: "password",
            CONF_DEFAULT_DID: "5552222222",
        },
        unique_id="user2",
    )
    entry1.add_to_hass(hass)
    entry2.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # In HA, setting up the first entry for a component may trigger the setup of all added entries for that domain.
    # If entry2 wasn't automatically set up, set it up.
    from homeassistant.config_entries import ConfigEntryState

    if entry2.state != ConfigEntryState.LOADED:
        assert await hass.config_entries.async_setup(entry2.entry_id)
        await hass.async_block_till_done()

    # Both entries should have runtime_data
    assert hasattr(entry1, "runtime_data") and entry1.runtime_data is not None
    assert hasattr(entry2, "runtime_data") and entry2.runtime_data is not None

    # Unload entry1
    assert await hass.config_entries.async_unload(entry1.entry_id)
    await hass.async_block_till_done()
    assert getattr(entry1, "runtime_data", None) is None
    # Entry2 should still be loaded
    assert hasattr(entry2, "runtime_data") and entry2.runtime_data is not None

    # Unload entry2
    assert await hass.config_entries.async_unload(entry2.entry_id)
    await hass.async_block_till_done()
    assert getattr(entry2, "runtime_data", None) is None
