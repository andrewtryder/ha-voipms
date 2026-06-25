"""The VoIP.ms integration."""

from __future__ import annotations

import logging
from homeassistant.const import Platform

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)