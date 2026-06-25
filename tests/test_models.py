"""Test VoIP.ms model validation."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import DOMAIN, CONF_DEFAULT_DID
from custom_components.voipms.models import (
    InboundSms,
    InboundSmsValidationError,
)


async def test_inbound_sms_valid_payload(
    hass: HomeAssistant, mock_voipms_client
) -> None:
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


async def test_inbound_sms_missing_from(
    hass: HomeAssistant, mock_voipms_client
) -> None:
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


async def test_inbound_sms_missing_message(
    hass: HomeAssistant, mock_voipms_client
) -> None:
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


async def test_inbound_sms_missing_date(
    hass: HomeAssistant, mock_voipms_client
) -> None:
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


async def test_inbound_sms_empty_message(
    hass: HomeAssistant, mock_voipms_client
) -> None:
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


def test_call_record_parses_inbound_cdr() -> None:
    """Test inbound CDR record parsing."""
    from custom_components.voipms.const import DIRECTION_INBOUND
    from custom_components.voipms.models import CallRecord

    record = {
        "uniqueid": "call-123",
        "callerid": "5559876543",
        "destination": "5551234567",
        "description": "Incoming call",
        "date": "2024-01-01 12:00:00",
        "duration": "45",
        "disposition": "ANSWERED",
    }

    call = CallRecord.parse_cdr_record(record)
    assert call is not None
    assert call.unique_id == "call-123"
    assert call.caller_id == "5559876543"
    assert call.destination == "5551234567"
    assert call.direction == DIRECTION_INBOUND
    assert call.to_event_data()["direction"] == DIRECTION_INBOUND


def test_call_record_parses_outbound_cdr_without_uniqueid() -> None:
    """Test outbound CDR record parsing falls back to composite unique ID."""
    from custom_components.voipms.const import DIRECTION_OUTBOUND
    from custom_components.voipms.models import CallRecord

    record = {
        "callerid": "5551234567",
        "destination": "5559876543",
        "description": "Outbound call",
        "date": "2024-01-01 13:00:00",
        "duration": "30",
        "disposition": "ANSWERED",
    }

    call = CallRecord.parse_cdr_record(record)
    assert call is not None
    assert call.direction == DIRECTION_OUTBOUND
    assert call.unique_id == ("2024-01-01 13:00:00|5551234567|5559876543|Outbound call")


def test_call_record_returns_none_without_date() -> None:
    """Test invalid CDR records are ignored."""
    from custom_components.voipms.models import CallRecord

    assert CallRecord.parse_cdr_record({"description": "Incoming call"}) is None


def test_call_record_detects_voicemail_from_description() -> None:
    """Test voicemail calls are detected from CDR description."""
    from custom_components.voipms.const import DIRECTION_INBOUND
    from custom_components.voipms.models import CallRecord

    record = {
        "uniqueid": "vm-1",
        "callerid": "5559876543",
        "destination": "5551234567",
        "description": "Failover to Voicemail {Voicemail}",
        "date": "2024-01-01 12:00:00",
        "duration": "12",
        "disposition": "ANSWERED",
    }

    call = CallRecord.parse_cdr_record(record)
    assert call is not None
    assert call.is_voicemail() is True
    assert call.direction == DIRECTION_INBOUND
    assert call.to_event_data()["is_voicemail"] == "true"
