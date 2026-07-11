"""Base entity for VoIP.ms integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class VoipmsEntity(Entity):
    """Base entity for VoIP.ms."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the base entity."""
        self._entry = entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information linking this entity to the integration."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }
