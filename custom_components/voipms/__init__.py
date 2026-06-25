"""The VoIP.ms integration."""

from __future__ import annotations

import logging
from homeassistant.const import Platform

from .api import VoipMsRestClient  # noqa: F401 — used by test mocks

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)


def get_url(hass, *, require_https: bool = True) -> str:
    """Return the URL of the Home Assistant instance.

    Exposed at module level so tests can patch ``custom_components.voipms.get_url``.
    """
    from homeassistant.components import http

    return http.get_url(hass, require_https=require_https)
