"""Test VoIP.ms inbound SMS processor."""

from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, EVENT_LOGBOOK_ENTRY
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    EVENT_INBOUND_CALL,
    EVENT_INBOUND_SMS,
    EVENT_OUTBOUND_CALL,
)
from custom_components.voipms.models import CallRecord, InboundSms
from custom_components.voipms.processor import process_call, process_inbound_sms


def _get_last_call_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the entity ID for the last call sensor."""
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id == f"{entry.entry_id}_last_call":
            return registry_entry.entity_id
    raise AssertionError("Last call sensor entity not found")


def _sample_call(**overrides) -> CallRecord:
    """Return a sample inbound call record."""
    values = {
        "unique_id": "call-abc123",
        "caller_id": "5559876543",
        "destination": "5551234567",
        "description": "Incoming call",
        "timestamp": "2024-01-01 12:00:00",
        "duration": "45",
        "disposition": "ANSWERED",
        "direction": "inbound",
    }
    values.update(overrides)
    return CallRecord(**values)


async def test_process_call_creates_event_logbook_and_notification(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that processing a call creates event, logbook, and notification."""
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

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    call = _sample_call()
    captured_events: list = []
    captured_logbook: list = []

    hass.bus.async_listen(
        EVENT_INBOUND_CALL, lambda event: captured_events.append(event.data)
    )
    hass.bus.async_listen(
        EVENT_LOGBOOK_ENTRY, lambda event: captured_logbook.append(event.data)
    )

    with patch(
        "custom_components.voipms.processor.persistent_notification.async_create"
    ) as mock_create:
        await process_call(hass, entry, call)
        await hass.async_block_till_done()

        assert len(captured_events) == 1
        assert captured_events[0]["callerid"] == "5559876543"
        assert captured_events[0]["destination"] == "5551234567"
        assert captured_events[0]["direction"] == "inbound"

        assert len(captured_logbook) == 1
        assert (
            "Inbound call from 5559876543 to 5551234567"
            in captured_logbook[0]["message"]
        )
        assert captured_logbook[0]["entity_id"] == "sensor.voip_ms_inbound_calls_24h"

        mock_create.assert_called_once()
        assert (
            mock_create.call_args.kwargs["notification_id"] == "voipms_call_call-abc123"
        )


async def test_process_outbound_call_fires_outbound_event(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test outbound calls fire the outbound call event."""
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

    call = _sample_call(
        unique_id="call-out-1",
        description="Outbound call",
        direction="outbound",
        timestamp="2024-01-01 13:00:00",
    )
    captured_events: list = []
    hass.bus.async_listen(
        EVENT_OUTBOUND_CALL, lambda event: captured_events.append(event.data)
    )

    await process_call(hass, entry, call)
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    assert captured_events[0]["direction"] == "outbound"


async def test_process_call_updates_last_call_sensor(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that processing a call updates the last call sensor."""
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

    sensor_entity_id = _get_last_call_entity_id(hass, entry)
    assert hass.states.get(sensor_entity_id).state == "unknown"

    call = _sample_call()
    await process_call(hass, entry, call)
    await hass.async_block_till_done()

    sensor_state = hass.states.get(sensor_entity_id)
    assert sensor_state is not None
    assert sensor_state.state == "2024-01-01 12:00:00"
    assert sensor_state.attributes["caller_id"] == "5559876543"
    assert sensor_state.attributes["destination"] == "5551234567"
    assert sensor_state.attributes["direction"] == "inbound"
    assert sensor_state.attributes["duration"] == "45"
    assert sensor_state.attributes["disposition"] == "ANSWERED"
    assert sensor_state.attributes["is_voicemail"] is False


def _get_last_sms_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the entity ID for the last SMS sensor."""
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id == f"{entry.entry_id}_last_sms":
            return registry_entry.entity_id
    raise AssertionError("Last SMS sensor entity not found")


async def test_process_inbound_sms_creates_event_logbook_and_notification(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that processing an inbound SMS creates event, logbook, and notification."""
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

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Create a valid InboundSms instance
    sms = InboundSms(
        sender="5559876543",
        recipient="5551234567",
        message="Hello, world!",
        message_id="abc123",
        timestamp="2024-01-01",
    )

    # Capture event, logbook, and notification
    captured_events: list = []
    captured_logbook: list = []

    def capture_event(event):
        captured_events.append(event.data)

    def capture_logbook(event):
        captured_logbook.append(event.data)

    hass.bus.async_listen(EVENT_INBOUND_SMS, capture_event)
    hass.bus.async_listen(EVENT_LOGBOOK_ENTRY, capture_logbook)

    # Get notifications storage
    from homeassistant.components.persistent_notification import (
        _async_get_or_create_notifications,
    )

    _async_get_or_create_notifications(hass)

    # Mock the notification component to capture async_create calls
    with patch(
        "custom_components.voipms.processor.persistent_notification.async_create"
    ) as mock_create:
        mock_create.return_value = None

        # Process the SMS
        await process_inbound_sms(hass, entry, sms)
        await hass.async_block_till_done()

        # Verify event was fired
        assert len(captured_events) == 1
        assert captured_events[0]["from"] == "5559876543"
        assert captured_events[0]["to"] == "5551234567"
        assert captured_events[0]["message"] == "Hello, world!"
        assert captured_events[0]["id"] == "abc123"

        # Verify logbook entry was created (with balance sensor entity)
        assert len(captured_logbook) == 1
        assert captured_logbook[0]["name"] == "VoIP.MS"
        assert captured_logbook[0]["domain"] == DOMAIN

        # Verify notification was created
        mock_create.assert_called_once_with(
            hass,
            "Hello, world!",
            title="SMS from 5559876543",
            notification_id="voipms_sms_abc123",
        )


async def test_process_inbound_sms_updates_last_sms_sensor(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that processing an inbound SMS updates the last SMS sensor."""
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

    # Verify sensor exists but has no SMS data before processing
    sensor_entity_id = _get_last_sms_entity_id(hass, entry)
    assert hass.states.get(sensor_entity_id).state == "unknown"

    # Create a valid InboundSms instance
    sms = InboundSms(
        sender="5559876543",
        recipient="5551234567",
        message="Hello, world!",
        message_id="def456",
        timestamp="2024-01-01",
    )

    # Process the SMS
    await process_inbound_sms(hass, entry, sms)
    await hass.async_block_till_done()

    # Verify sensor state was set
    sensor_state = hass.states.get(sensor_entity_id)
    assert sensor_state is not None
    assert sensor_state.state == "2024-01-01"
    assert sensor_state.attributes["sender"] == "5559876543"
    assert sensor_state.attributes["message"] == "Hello, world!"
    assert sensor_state.attributes["recipient"] == "5551234567"
    assert sensor_state.attributes["timestamp"] == "2024-01-01"
    assert sensor_state.attributes["message_id"] == "def456"


async def test_process_inbound_sms_long_message_truncation(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that long messages are truncated in logbook but not notification."""
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

    # Capture logbook events
    captured_logbook: list = []

    def capture_logbook(event):
        captured_logbook.append(event.data)

    hass.bus.async_listen(EVENT_LOGBOOK_ENTRY, capture_logbook)

    # Create a long message (longer than 120 chars)
    long_message = "A" * 150
    sms = InboundSms(
        sender="5559876543",
        recipient="5551234567",
        message=long_message,
        message_id="ghi789",
        timestamp="2024-01-01",
    )

    # Process the SMS
    await process_inbound_sms(hass, entry, sms)
    await hass.async_block_till_done()

    # Verify logbook contains truncated message
    assert len(captured_logbook) == 1
    assert "SMS from 5559876543 to 5551234567" in captured_logbook[0]["message"]
    assert "AAAA" in captured_logbook[0]["message"]
    assert "..." in captured_logbook[0]["message"]

    # Verify the sensor state was set with full message
    sensor_state = hass.states.get(_get_last_sms_entity_id(hass, entry))
    assert sensor_state is not None
    assert sensor_state.attributes["message"] == long_message
