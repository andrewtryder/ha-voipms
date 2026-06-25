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

    sensors = [
        VoipmsBalanceSensor(coordinator, entry),
        VoipmsInboundCallsSensor(coordinator, entry),
        VoipmsOutboundCallsSensor(coordinator, entry),
        VoipmsLastSmsSensor(entry),
    ]

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


class VoipmsLastSmsSensor(VoipmsBaseSensor):
    """Representation of the last received SMS for VoIP.ms."""

    _attr_has_entity_name = True
    _attr_name = "Last SMS"
    _attr_unique_id = None

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the last SMS sensor."""
        super().__init__(None, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_sms"
        self._state = None
        self._attributes = {}

    def set_state_from_sms(self, sms: Any) -> None:
        """Set sensor state and attributes from an InboundSms model."""
        self._state = sms.sender
        self._attributes = {
            "message": sms.message,
            "recipient": sms.recipient,
            "timestamp": sms.timestamp,
            "message_id": sms.message_id,
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes
