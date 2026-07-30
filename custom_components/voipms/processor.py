"""Inbound SMS and call processing for VoIP.ms integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components import persistent_notification
from homeassistant.const import CONF_USERNAME, EVENT_LOGBOOK_ENTRY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DIRECTION_INBOUND,
    DOMAIN,
    EVENT_INBOUND_CALL,
    EVENT_INBOUND_SMS,
    EVENT_OUTBOUND_CALL,
)

if TYPE_CHECKING:
    from .__init__ import VoipmsConfigEntry
from .helpers import mask_phone_number
from .models import CallRecord, InboundSms

_LOGGER = logging.getLogger(__name__)

LOGBOOK_NAME = "VoIP.MS"
MAX_SMS_LOGBOOK_MESSAGE_LEN = 120


def _get_logbook_entity_id(
    hass: HomeAssistant, entry: VoipmsConfigEntry, suffix: str
) -> str | None:
    """Return an entity ID for logbook linkage by unique ID suffix."""
    entity_registry = er.async_get(hass)
    unique_id = f"{entry.unique_id}_{suffix}"
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if registry_entry.unique_id == unique_id:
            return registry_entry.entity_id
    return None


def _log_inbound_sms_to_logbook(
    hass: HomeAssistant, entry: VoipmsConfigEntry, sms: InboundSms
) -> None:
    """Write an inbound SMS entry to the Home Assistant logbook."""
    message_text = sms.message
    if len(message_text) > MAX_SMS_LOGBOOK_MESSAGE_LEN:
        message_text = f"{message_text[: MAX_SMS_LOGBOOK_MESSAGE_LEN - 3]}..."

    logbook_data = {
        "name": LOGBOOK_NAME,
        "message": (
            f"SMS from {mask_phone_number(sms.sender)} to {mask_phone_number(sms.recipient)}: {message_text}"
        ),
        "domain": DOMAIN,
    }
    entity_id = _get_logbook_entity_id(hass, entry, "balance")
    if entity_id is not None:
        logbook_data["entity_id"] = entity_id

    hass.bus.async_fire(EVENT_LOGBOOK_ENTRY, logbook_data)


def _log_call_to_logbook(
    hass: HomeAssistant, entry: VoipmsConfigEntry, call: CallRecord
) -> None:
    """Write a call entry to the Home Assistant logbook."""
    direction_label = "Inbound" if call.direction == DIRECTION_INBOUND else "Outbound"
    duration_text = f"{call.duration}s" if call.duration else "unknown duration"
    disposition_text = call.disposition or "unknown disposition"
    logbook_data = {
        "name": LOGBOOK_NAME,
        "message": (
            f"{direction_label} call from {call.caller_id} to {call.destination} "
            f"({duration_text}, {disposition_text})"
        ),
        "domain": DOMAIN,
    }
    suffix = (
        "inbound_calls_24h"
        if call.direction == DIRECTION_INBOUND
        else "outbound_calls_24h"
    )
    entity_id = _get_logbook_entity_id(hass, entry, suffix)
    if entity_id is not None:
        logbook_data["entity_id"] = entity_id

    hass.bus.async_fire(EVENT_LOGBOOK_ENTRY, logbook_data)


def _create_inbound_sms_notification(
    hass: HomeAssistant, entry: VoipmsConfigEntry, sms: InboundSms
) -> None:
    """Create a persistent notification for an inbound SMS."""
    notification_id = (
        f"voipms_{entry.entry_id}_sms_{sms.message_id}" if sms.message_id else None
    )

    persistent_notification.async_create(
        hass,
        sms.message,
        title=f"SMS from {mask_phone_number(sms.sender)}",
        notification_id=notification_id,
    )


def _create_call_notification(
    hass: HomeAssistant, entry: VoipmsConfigEntry, call: CallRecord
) -> None:
    """Create a persistent notification for a call."""
    direction_label = "Inbound" if call.direction == DIRECTION_INBOUND else "Outbound"
    duration_text = f"{call.duration}s" if call.duration else "unknown duration"
    disposition_text = call.disposition or "unknown disposition"
    notification_id = f"voipms_{entry.entry_id}_call_{call.unique_id}"

    persistent_notification.async_create(
        hass,
        (
            f"From {call.caller_id} to {call.destination}\n"
            f"Duration: {duration_text}\n"
            f"Disposition: {disposition_text}"
        ),
        title=f"{direction_label} call",
        notification_id=notification_id,
    )


def _notify_last_sms_sensor(
    hass: HomeAssistant, entry: VoipmsConfigEntry, sms: InboundSms
) -> None:
    """Update the last SMS sensor with the most recent message."""
    entity = getattr(entry.runtime_data, "last_sms_entity", None)
    if entity is None or not hasattr(entity, "set_state_from_sms"):
        _LOGGER.debug("Last SMS sensor not yet created for entry %s", entry.entry_id)
        return

    entity.set_state_from_sms(sms)


def _notify_last_call_sensor(
    hass: HomeAssistant, entry: VoipmsConfigEntry, call: CallRecord
) -> None:
    """Update the last call sensor with the most recent call."""
    entity = getattr(entry.runtime_data, "last_call_entity", None)
    if entity is None or not hasattr(entity, "set_state_from_call"):
        _LOGGER.debug("Last call sensor not yet created for entry %s", entry.entry_id)
        return

    entity.set_state_from_call(call)


async def process_inbound_sms(
    hass: HomeAssistant, entry: VoipmsConfigEntry, sms: InboundSms
) -> None:
    """Process an inbound SMS message from VoIP.ms."""
    # Log masked numbers at INFO level to protect PII
    _LOGGER.info(
        "Processing inbound SMS: sender=%s, recipient=%s, message_id=%s",
        mask_phone_number(sms.sender),
        mask_phone_number(sms.recipient),
        sms.message_id,
    )

    event_data = {
        **sms.to_event_data(),
        "account": entry.data.get(CONF_USERNAME, ""),
        "config_entry_id": entry.entry_id,
    }
    hass.bus.async_fire(EVENT_INBOUND_SMS, event_data)
    _log_inbound_sms_to_logbook(hass, entry, sms)
    _create_inbound_sms_notification(hass, entry, sms)
    _notify_last_sms_sensor(hass, entry, sms)

    _LOGGER.info("Inbound SMS processed: message_id=%s", sms.message_id)


async def process_call(
    hass: HomeAssistant, entry: VoipmsConfigEntry, call: CallRecord
) -> None:
    """Process a call detail record from VoIP.ms."""
    event = (
        EVENT_INBOUND_CALL
        if call.direction == DIRECTION_INBOUND
        else EVENT_OUTBOUND_CALL
    )
    _LOGGER.info(
        "Processing %s call: caller=%s, destination=%s, unique_id=%s",
        call.direction,
        mask_phone_number(call.caller_id),
        mask_phone_number(call.destination),
        call.unique_id,
    )

    event_data = {
        **call.to_event_data(),
        "account": entry.data.get(CONF_USERNAME, ""),
        "config_entry_id": entry.entry_id,
    }
    hass.bus.async_fire(event, event_data)
    _log_call_to_logbook(hass, entry, call)
    _create_call_notification(hass, entry, call)
    _notify_last_call_sensor(hass, entry, call)

    _LOGGER.info("Call processed: unique_id=%s", call.unique_id)
