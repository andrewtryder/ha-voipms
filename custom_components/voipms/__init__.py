"""The VoIP.ms integration."""

from __future__ import annotations

import logging

from homeassistant.components.webhook import (  # noqa: F401 — used by test mocks
    async_register,
    async_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import VoipMsRestClient  # noqa: F401 — used by test mocks
from .const import DOMAIN
from .coordinator import VoipmsDataUpdateCoordinator
from .webhook import (
    async_register_inbound_sms_webhook,
    async_unregister_inbound_sms_webhook,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)


def get_url(
    hass: HomeAssistant,
    *,
    prefer_external: bool = False,
    allow_cloud: bool = False,
) -> str:
    """Return the URL of the Home Assistant instance.

    Exposed at module level so tests can patch ``custom_components.voipms.get_url``.
    """
    from homeassistant.helpers import network

    return network.get_url(
        hass, prefer_external=prefer_external, allow_cloud=allow_cloud
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VoIP.ms from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = VoipmsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_inbound_sms_webhook(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    await async_unregister_inbound_sms_webhook(hass, entry)

    if hass.services.has_service(DOMAIN, "send_sms"):
        hass.services.async_remove(DOMAIN, "send_sms")

    return unload_ok
