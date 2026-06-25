"""Sensor platform for VoIP.ms integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Any

from .const import DOMAIN
from .coordinator import VoipmsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VoIP.ms sensor platform."""
    coordinator = hass.data["voipms"][entry.entry_id]
    last_sms_sensor = VoipmsLastSmsSensor(entry)
    last_call_sensor = VoipmsLastCallSensor(entry)

    sensors = [
        VoipmsBalanceSensor(coordinator, entry),
        VoipmsInboundCallsSensor(coordinator, entry),
        VoipmsOutboundCallsSensor(coordinator, entry),
        VoipmsVoicemailCallsSensor(coordinator, entry),
        last_sms_sensor,
        last_call_sensor,
    ]

    hass.data[DOMAIN][f"{entry.entry_id}_last_sms_entity"] = last_sms_sensor
    hass.data[DOMAIN][f"{entry.entry_id}_last_call_entity"] = last_call_sensor
    async_add_entities(sensors, True)


class VoipmsBaseSensor(CoordinatorEntity[VoipmsDataUpdateCoordinator], SensorEntity):
    """Base class for VoIP.ms sensors."""

    def __init__(
        self, coordinator: VoipmsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }


class VoipmsBalanceSensor(VoipmsBaseSensor):
    """Representation of a VoIP.ms Account Balance sensor."""

    _attr_has_entity_name = True
    _attr_name = "Account Balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"  # Assuming USD, adjust if needed

    def __init__(
        self, coordinator: VoipmsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_balance"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("balance")
        return None


class VoipmsInboundCallsSensor(VoipmsBaseSensor):
    """Representation of a VoIP.ms Inbound Calls (24h) sensor."""

    _attr_has_entity_name = True
    _attr_name = "Inbound Calls (24h)"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "calls"

    def __init__(
        self, coordinator: VoipmsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the inbound calls sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_inbound_calls_24h"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("inbound_calls_24h")
        return None


class VoipmsOutboundCallsSensor(VoipmsBaseSensor):
    """Representation of a VoIP.ms Outbound Calls (24h) sensor."""

    _attr_has_entity_name = True
    _attr_name = "Outbound Calls (24h)"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "calls"

    def __init__(
        self, coordinator: VoipmsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the outbound calls sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_outbound_calls_24h"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("outbound_calls_24h")
        return None


class VoipmsVoicemailCallsSensor(VoipmsBaseSensor):
    """Representation of a VoIP.ms Voicemails sensor."""

    _attr_has_entity_name = True
    _attr_name = "Voicemails"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "messages"

    def __init__(
        self, coordinator: VoipmsDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the voicemails sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_voicemail_calls_24h"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("voicemail_count")
        return None


class VoipmsLastSmsSensor(SensorEntity):
    """Representation of the last received SMS for VoIP.ms."""

    _attr_has_entity_name = True
    _attr_name = "Last SMS"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the last SMS sensor."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_sms"
        self._state = None
        self._attributes: dict[str, Any] = {}

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }

    def set_state_from_sms(self, sms: Any) -> None:
        """Set sensor state and attributes from an InboundSms model."""
        self._state = sms.timestamp
        self._attributes = {
            "sender": sms.sender,
            "message": sms.message,
            "recipient": sms.recipient,
            "timestamp": sms.timestamp,
            "message_id": sms.message_id,
        }
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes


class VoipmsLastCallSensor(SensorEntity):
    """Representation of the last tracked call for VoIP.ms."""

    _attr_has_entity_name = True
    _attr_name = "Last Call"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the last call sensor."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_call"
        self._state = None
        self._attributes: dict[str, Any] = {}

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }

    def set_state_from_call(self, call: Any) -> None:
        """Set sensor state and attributes from a CallRecord model."""
        self._state = call.timestamp
        self._attributes = {
            "caller_id": call.caller_id,
            "destination": call.destination,
            "description": call.description,
            "duration": call.duration,
            "disposition": call.disposition,
            "direction": call.direction,
            "is_voicemail": call.is_voicemail(),
            "unique_id": call.unique_id,
            "timestamp": call.timestamp,
        }
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes
