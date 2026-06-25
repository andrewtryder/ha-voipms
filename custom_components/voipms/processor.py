"""Inbound SMS processing for VoIP.ms integration."""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_LOGBOOK_ENTRY
from homeassistant.helpers import entity_registry as er

from .models import InboundSms

_LOGGER = logging.getLogger(__name__)

LOGBOOK_NAME = "VoIP.MS"
MAX_SMS_LOGBOOK_MESSAGE_LEN = 120


def _log_inbound_sms_to_logbook(
    hass: HomeAssistant, entry: ConfigEntry, sms: InboundSms
) -> None:
    """Write an inbound SMS entry to the Home Assistant logbook."""
    message_text = sms.message
    if len(message_text) > MAX_SMS_LOGBOOK_MESSAGE_LEN:
        message_text = f"{message_text[: MAX_SMS_LOGBOOK_MESSAGE_LEN - 3]}..."

    entity_id = None
    entity_registry = er.async_get(hass)
    balance_unique_id = f"{entry.entry_id}_balance"
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id == balance_unique_id:
            entity_id = registry_entry.entity_id
            break

    logbook_data = {
        "name": LOGBOOK_NAME,
        "message": (f"SMS from {sms.sender} to {sms.recipient}: {message_text}"),
        "domain": "voipms",
    }
    if entity_id is not None:
        logbook_data["entity_id"] = entity_id

    hass.bus.async_fire(EVENT_LOGBOOK_ENTRY, logbook_data)


def _create_inbound_sms_notification(hass: HomeAssistant, sms: InboundSms) -> None:
    """Create a persistent notification for an inbound SMS."""
    notification_id = f"voipms_sms_{sms.message_id}" if sms.message_id else None

    persistent_notification.async_create(
        hass,
        sms.message,
        title=f"SMS from {sms.sender}",
        notification_id=notification_id,
    )


def _notify_last_sms_sensor(
    hass: HomeAssistant, entry: ConfigEntry, sms: InboundSms
) -> None:
    """Update the last SMS sensor with the most recent message."""
    # Look up the last SMS sensor by its unique ID
    entity_registry = er.async_get(hass)
    sensor_unique_id = f"{entry.entry_id}_last_sms"
    sensor_entity_id = None

    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id == sensor_unique_id:
            sensor_entity_id = registry_entry.entity_id
            break

    if sensor_entity_id is None:
        # Sensor not yet created; skip for now
        _LOGGER.debug("Last SMS sensor not yet created for entry %s", entry.entry_id)
        return

    # Create sensor state and attributes
    state = sms.sender
    attributes = {
        "message": sms.message,
        "recipient": sms.recipient,
        "timestamp": sms.timestamp,
        "message_id": sms.message_id,
    }

    hass.states.async_set(sensor_entity_id, state, attributes)


async def process_inbound_sms(
    hass: HomeAssistant, entry: ConfigEntry, sms: InboundSms
) -> None:
    """Process an inbound SMS message from VoIP.ms.

    Args:
        hass: Home Assistant instance
        entry: Configuration entry for this integration
        sms: Validated InboundSms model instance
    """
    _LOGGER.info(
        "Processing inbound SMS: sender=%s, recipient=%s, message_id=%s",
        sms.sender,
        sms.recipient,
        sms.message_id,
    )

    # Fire event for automations
    from homeassistant.const import EVENT_INBOUND_SMS

    hass.bus.async_fire(EVENT_INBOUND_SMS, sms.to_event_data())

    # Write to logbook
    _log_inbound_sms_to_logbook(hass, entry, sms)

    # Create notification
    _create_inbound_sms_notification(hass, sms)

    # Update last SMS sensor
    _notify_last_sms_sensor(hass, entry, sms)

    _LOGGER.info("Inbound SMS processed: message_id=%s", sms.message_id)
