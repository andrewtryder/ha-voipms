"""Test VoIP.ms model validation."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import DOMAIN, CONF_DEFAULT_DID
from custom_components.voipms.models import (
    InboundSms,
    InboundSmsValidationError,
)


async def test_inbound_sms_valid_payload(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test valid inbound SMS payload parses correctly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Test full valid payload
    payload = {
        "from": "5559876543",
        "to": "5551234567",
        "message": "Hello, world!",
        "id": "abc123",
        "date": "2024-01-01",
    }

    sms = InboundSms.parse_inbound_sms(payload)
    assert sms.sender == "5559876543"
    assert sms.recipient == "5551234567"
    assert sms.message == "Hello, world!"
    assert sms.message_id == "abc123"
    assert sms.timestamp == "2024-01-01"

    # Verify event data matches legacy keys
    event_data = sms.to_event_data()
    assert event_data["from"] == "5559876543"
    assert event_data["to"] == "5551234567"
    assert event_data["message"] == "Hello, world!"
    assert event_data["id"] == "abc123"
    assert event_data["date"] == "2024-01-01"


async def test_inbound_sms_missing_from(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing 'from' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "to": "5551234567",
        "message": "Hello",
        "id": "123",
        "date": "2024-01-01",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "from" in str(e)


async def test_inbound_sms_missing_to(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing 'to' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "from": "5559876543",
        "message": "Hello",
        "id": "123",
        "date": "2024-01-01",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "to" in str(e)


async def test_inbound_sms_missing_message(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing 'message' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "from": "5559876543",
        "to": "5551234567",
        "id": "123",
        "date": "2024-01-01",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "message" in str(e)


async def test_inbound_sms_missing_id(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing 'id' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "from": "5559876543",
        "to": "5551234567",
        "message": "Hello",
        "date": "2024-01-01",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "id" in str(e)


async def test_inbound_sms_missing_date(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test missing 'date' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "from": "5559876543",
        "to": "5551234567",
        "message": "Hello",
        "id": "123",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "date" in str(e)


async def test_inbound_sms_empty_message(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test empty 'message' field raises validation error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    payload = {
        "from": "5559876543",
        "to": "5551234567",
        "message": "",
        "id": "123",
        "date": "2024-01-01",
    }

    try:
        InboundSms.parse_inbound_sms(payload)
        assert False, "Expected InboundSmsValidationError"
    except InboundSmsValidationError as e:
        assert "message" in str(e)