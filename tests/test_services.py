"""Test the VoIP.MS integration services."""

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    MAX_SMS_MESSAGE_LENGTH,
)


def _entry(
    *,
    did: str | None = "5551234567",
    username: str = "test_user",
    password: str = "test_password",
) -> MockConfigEntry:
    data = {
        CONF_USERNAME: username,
        CONF_PASSWORD: password,
    }
    if did is not None:
        data[CONF_DEFAULT_DID] = did
    return MockConfigEntry(domain=DOMAIN, data=data)


async def test_send_sms_service_success(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test the voipms.send_sms service successfully sends an SMS."""
    entry = _entry()
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


async def test_send_sms_service_e164_recipient(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test valid E.164 recipient succeeds."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "send_sms",
        {"to": "+15559876543", "message": "Hello"},
        blocking=True,
    )

    assert mock_voipms_client.send_sms.call_args.kwargs["dst"] == "+15559876543"


async def test_send_sms_service_with_explicit_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test the 'did' field overrides the default DID."""
    entry = _entry()
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


async def test_send_sms_invalid_recipient(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test invalid recipient raises ServiceValidationError without calling API."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    bad_to = "555-987-6543"
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": bad_to, "message": "Hello"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_recipient"
    assert bad_to not in str(exc_info.value)
    mock_voipms_client.send_sms.assert_not_called()


async def test_send_sms_invalid_explicit_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test invalid explicit DID raises ServiceValidationError."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    bad_did = "(555) 000-0000"
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": "5559876543", "message": "Hello", "did": bad_did},
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_did"
    assert bad_did not in str(exc_info.value)
    mock_voipms_client.send_sms.assert_not_called()


async def test_send_sms_invalid_configured_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test invalid configured DID raises ServiceValidationError at send time."""
    entry = _entry(did="5551234567")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Simulate legacy/corrupt stored DID without reloading the entry.
    object.__setattr__(
        entry,
        "data",
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "bad-did",
        },
    )

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": "5559876543", "message": "Hello"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "invalid_did"
    assert "bad-did" not in str(exc_info.value)
    mock_voipms_client.send_sms.assert_not_called()


async def test_send_sms_missing_did(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing configured DID raises ServiceValidationError."""
    entry = _entry(did="5551234567")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    object.__setattr__(
        entry,
        "data",
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        },
    )

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": "5559876543", "message": "Hello"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "missing_did"
    mock_voipms_client.send_sms.assert_not_called()


@pytest.mark.parametrize("message", ["", "   "])
async def test_send_sms_empty_message(
    hass: HomeAssistant, mock_voipms_client, message: str
) -> None:
    """Test empty and whitespace-only messages are rejected."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": "5559876543", "message": message},
            blocking=True,
        )

    assert exc_info.value.translation_key == "empty_message"
    mock_voipms_client.send_sms.assert_not_called()


async def test_send_sms_message_exact_max(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test a 160-character message succeeds."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    message = "a" * MAX_SMS_MESSAGE_LENGTH
    await hass.services.async_call(
        DOMAIN,
        "send_sms",
        {"to": "5559876543", "message": message},
        blocking=True,
    )

    assert mock_voipms_client.send_sms.call_args.kwargs["message"] == message


async def test_send_sms_message_too_long(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test a 161-character message is rejected."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    message = "a" * (MAX_SMS_MESSAGE_LENGTH + 1)
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"to": "5559876543", "message": message},
            blocking=True,
        )

    assert exc_info.value.translation_key == "message_too_long"
    assert message not in str(exc_info.value)
    mock_voipms_client.send_sms.assert_not_called()


async def test_send_sms_service_api_rejection(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that a non-success status raises a HomeAssistantError."""
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_voipms_client.send_sms.return_value = {"status": "invalid_credentials"}

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {
                "to": "5559876543",
                "message": "Hello",
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "sms_provider_rejected"
    assert "5559876543" not in str(exc_info.value)
    assert "Hello" not in str(exc_info.value)


async def test_send_sms_service_network_error(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that a network error raises a HomeAssistantError."""
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_voipms_client.send_sms.side_effect = VoipMsApiError("Connection timed out")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {
                "to": "5559876543",
                "message": "Hello",
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "sms_network_error"
    assert "5559876543" not in str(exc_info.value)


async def test_unload_removes_service(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test the send_sms service is removed on unload."""
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "send_sms")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "send_sms")
