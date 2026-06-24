"""Test VoIP.ms Custom setup and unload."""

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms_custom.const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    build_webhook_callback_url,
)


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
