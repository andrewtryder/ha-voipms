"""Test VoIP.ms setup and unload."""

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.components.persistent_notification import (
    _async_get_or_create_notifications,
)
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

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    mock_voipms_client.set_sms.assert_called_once()
    call_kwargs = mock_voipms_client.set_sms.call_args.kwargs
    expected_url = build_webhook_callback_url(
        "http://example.com", f"voipms_{entry.entry_id}"
    )
    assert call_kwargs["url_callback"] == expected_url

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data[DOMAIN]


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
    assert "voipms_sms_42" in notifications
    assert notifications["voipms_sms_42"]["message"] == "hello"
    assert notifications["voipms_sms_42"]["title"] == "SMS from 5559876543"
