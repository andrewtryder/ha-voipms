"""The VoIP.ms Custom integration."""

from __future__ import annotations

import logging

from aiohttp import web
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.webhook import async_register, async_unregister
from homeassistant.helpers.network import get_url

from .api import VoipMsRestClient
from .const import DOMAIN, EVENT_INBOUND_SMS, build_webhook_callback_url
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

    webhook_id = f"voipms_{entry.entry_id}"

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ):
        """Handle incoming webhook from VoIP.ms."""
        try:
            if request.method == "POST":
                data = await request.post()
            else:
                data = request.query
            if not data:
                data = {}

            payload = dict(data)
            hass.bus.async_fire(EVENT_INBOUND_SMS, payload)
            _LOGGER.info(
                "Received VoIP.ms SMS from %s to %s (id=%s)",
                payload.get("from"),
                payload.get("to"),
                payload.get("id"),
            )

            return web.Response(text="ok")
        except Exception as err:
            _LOGGER.error("Error handling VoIP.ms webhook: %s", err)
            return web.Response(status=500)

    async_register(
        hass,
        DOMAIN,
        "VoIP.ms SMS",
        webhook_id,
        handle_webhook,
        allowed_methods=(METH_GET, METH_POST, METH_PUT),
    )

    try:
        external_url = get_url(hass, prefer_external=True, allow_cloud=True)
        webhook_url = build_webhook_callback_url(external_url, webhook_id)

        from .const import CONF_DEFAULT_DID

        did = entry.data.get(CONF_DEFAULT_DID)

        if did:

            def register_webhook():
                client = VoipMsRestClient(
                    entry.data[CONF_USERNAME],
                    entry.data[CONF_PASSWORD],
                )
                return client.set_sms(did=did, enable=1, url_callback=webhook_url)

            result = await hass.async_add_executor_job(register_webhook)
            _LOGGER.info("Registered VoIP.ms webhook %s: %s", webhook_url, result)
    except Exception as ex:
        _LOGGER.warning(
            "Failed to register webhook with VoIP.ms. You may need to configure it manually. Error: %s",
            ex,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    webhook_id = f"voipms_{entry.entry_id}"
    async_unregister(hass, webhook_id)

    return unload_ok
