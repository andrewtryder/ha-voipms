"""Binary sensor platform for VoIP.ms SIP registration status."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up VoIP.ms binary sensors for SIP registration status."""
    coordinator: VoipmsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    registrations: dict[str, dict[str, Any]] = (
        coordinator.data.get("registrations", {}) if coordinator.data else {}
    )

    entities = [
        VoipmsRegistrationBinarySensor(coordinator, entry, account_name, reg_data)
        for account_name, reg_data in registrations.items()
    ]
    async_add_entities(entities)


class VoipmsRegistrationBinarySensor(
    CoordinatorEntity[VoipmsDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor that shows whether a SIP subaccount is registered."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VoipmsDataUpdateCoordinator,
        entry: ConfigEntry,
        account_name: str,
        reg_data: dict[str, Any],
    ) -> None:
        """Initialize the registration binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._account_name = account_name
        self._attr_unique_id = f"{entry.entry_id}_registration_{account_name}"
        self._attr_name = f"SIP {account_name}"
        self._attr_is_on = reg_data.get("registered", False)
        self._attr_extra_state_attributes = {
            "description": reg_data.get("description", ""),
            "device_type": reg_data.get("device_type", ""),
            "callerid_number": reg_data.get("callerid_number", ""),
            "protocol": reg_data.get("protocol", ""),
        }

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }

    @property
    def is_on(self) -> bool:
        """Return True if the subaccount is currently registered."""
        if self.coordinator.data is None:
            return False
        reg_data = self.coordinator.data.get("registrations", {}).get(
            self._account_name
        )
        if reg_data is None:
            return False
        return bool(reg_data.get("registered", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}
        reg_data = self.coordinator.data.get("registrations", {}).get(
            self._account_name
        )
        if reg_data is None:
            return {}
        return {
            "description": reg_data.get("description", ""),
            "device_type": reg_data.get("device_type", ""),
            "callerid_number": reg_data.get("callerid_number", ""),
            "protocol": reg_data.get("protocol", ""),
        }
