"""The VoIP.ms integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform

from .api import VoipMsRestClient as VoipMsRestClient
from .coordinator import VoipmsDataUpdateCoordinator as VoipmsDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)
