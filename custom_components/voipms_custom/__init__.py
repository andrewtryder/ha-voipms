"""The VoIP.ms Custom integration."""
from __future__ import annotations

import logging
import os

import zeep
from aiohttp import web

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.helpers.network import get_url

from .const import DOMAIN, EVENT_INBOUND_SMS
from .coordinator import VoipmsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VoIP.ms Custom from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = VoipmsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup webhook
    webhook_id = f"voipms_{entry.entry_id}"

    async def handle_webhook(hass: HomeAssistant, webhook_id: str, request: web.Request):
        """Handle incoming webhook from VoIP.ms."""
        try:
            data = await request.post() # or request.query if it's a GET, VoIP.ms can send GET or POST.
            if not data:
                data = await request.query

            # Fire an event
            hass.bus.async_fire(EVENT_INBOUND_SMS, dict(data))

            return web.Response(text="OK")
        except Exception as err:
            _LOGGER.error("Error handling VoIP.ms webhook: %s", err)
            return web.Response(status=500)

    async_register(
        hass,
        DOMAIN,
        "VoIP.ms SMS",
        webhook_id,
        handle_webhook,
    )

    # Try to register webhook with VoIP.ms
    try:
        external_url = get_url(hass, prefer_external=True, allow_cloud=True)
        webhook_url = f"{external_url}/api/webhook/{webhook_id}"

        # Determine DID to set SMS callback
        from .const import CONF_DEFAULT_DID
        did = entry.data.get(CONF_DEFAULT_DID)

        if did:
            def register_webhook():
                wsdl_path = os.path.join(os.path.dirname(__file__), "server.wsdl")
                client = zeep.Client(wsdl=wsdl_path)
                result = client.service.setSMS(
                    api_username=entry.data[CONF_USERNAME],
                    api_password=entry.data[CONF_PASSWORD],
                    did=did,
                    enable=1,
                    url_callback=webhook_url
                )
                return result

            result = await hass.async_add_executor_job(register_webhook)
            _LOGGER.info("Registered VoIP.ms webhook %s: %s", webhook_url, result)
    except Exception as ex:
        _LOGGER.warning("Failed to register webhook with VoIP.ms. You may need to configure it manually. Error: %s", ex)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Unregister webhook
    webhook_id = f"voipms_{entry.entry_id}"
    async_unregister(hass, webhook_id)

    return unload_ok
