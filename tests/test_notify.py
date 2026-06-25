"""Test the VoIP.MS notify platform."""

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN


async def test_notify_entity_created(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test the notify entity is created from the config entry."""
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

    state = hass.states.get("notify.voip_ms_sms")
    assert state is not None


async def test_send_sms_service_calls_send_sms(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test the voipms.send_sms service invokes sendSMS on the client."""
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

    await hass.services.async_call(
        DOMAIN,
        "send_sms",
        {
            "to": "5559876543",
            "message": "Hello from HA",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_voipms_client.send_sms.assert_called_once()
    call_kwargs = mock_voipms_client.send_sms.call_args.kwargs
    assert call_kwargs["did"] == "5551234567"
    assert call_kwargs["dst"] == "5559876543"
    assert call_kwargs["message"] == "Hello from HA"


async def test_send_sms_service_with_explicit_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test the 'did' field overrides the default DID."""
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

    await hass.services.async_call(
        DOMAIN,
        "send_sms",
        {
            "to": "5559876543",
            "message": "Hello",
            "did": "5550000000",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_voipms_client.send_sms.assert_called_once()
    assert mock_voipms_client.send_sms.call_args.kwargs["did"] == "5550000000"


async def test_unload_removes_service(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test the send_sms service is removed on unload."""
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
    assert hass.services.has_service(DOMAIN, "send_sms")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "send_sms")
