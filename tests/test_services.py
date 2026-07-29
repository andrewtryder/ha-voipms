"""Test the VoIP.MS integration services."""

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN


async def test_send_sms_service_success(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test the voipms.send_sms service successfully sends an SMS."""
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

    mock_voipms_client.send_sms.return_value = {"status": "success"}

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

    mock_voipms_client.send_sms.return_value = {"status": "success"}

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


async def test_send_sms_service_api_rejection(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that a non-success status raises a HomeAssistantError."""
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

    mock_voipms_client.send_sms.return_value = {"status": "invalid_credentials"}

    with pytest.raises(
        HomeAssistantError, match="VoIP.MS API rejected SMS send: invalid_credentials"
    ):
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {
                "to": "5559876543",
                "message": "Hello",
            },
            blocking=True,
        )


async def test_send_sms_service_network_error(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that a network error raises a HomeAssistantError."""
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

    mock_voipms_client.send_sms.side_effect = VoipMsApiError("Connection timed out")

    with pytest.raises(
        HomeAssistantError, match="Network error sending SMS: Connection timed out"
    ):
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {
                "to": "5559876543",
                "message": "Hello",
            },
            blocking=True,
        )


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
