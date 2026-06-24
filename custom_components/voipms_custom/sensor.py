"""Sensor platform for VoIP.ms Custom integration."""

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

from .const import DOMAIN
from .coordinator import VoipmsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VoIP.ms sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        VoipmsBalanceSensor(coordinator, entry),
        VoipmsInboundCallsSensor(coordinator, entry),
        VoipmsOutboundCallsSensor(coordinator, entry),
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
