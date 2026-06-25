"""The VoIP.ms integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import VoipMsRestClient
from .coordinator import VoipmsDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)
