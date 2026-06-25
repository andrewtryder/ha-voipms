"""Webhook handling for VoIP.ms integration."""

from __future__ import annotations

import logging

from aiohttp import web
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT
from homeassistant.components.webhook import async_register, async_unregister

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url

from .api import VoipMsRestClient
from .const import DOMAIN, build_webhook_callback_url, CONF_DEFAULT_DID
from .models import InboundSms, InboundSmsValidationError
from .processor import process_inbound_sms

_LOGGER = logging.getLogger(__name__)


async def async_register_inbound_sms_webhook(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register the inbound SMS webhook with VoIP.ms."""
    webhook_id = f"voipms_{entry.entry_id}"

    async def webhook_handler(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle inbound webhook from VoIP.ms."""
        try:
            # Parse payload from GET or POST
            if request.method == "POST":
                data = await request.post()
            else:
                data = request.query
            if not data:
                data = {}

            payload = dict(data)
            _LOGGER.info(
                "Inbound SMS webhook received: method=%s, payload_keys=%s",
                request.method,
                list(payload.keys()),
            )

            # Validate and parse payload
            try:
                sms = InboundSms.parse_inbound_sms(payload)
                _LOGGER.info(
                    "Inbound SMS validated: message_id=%s, sender=%s, recipient=%s",
                    sms.message_id,
                    sms.sender,
                    sms.recipient,
                )
            except InboundSmsValidationError as e:
                _LOGGER.warning(
                    "Inbound SMS validation failed: %s, payload_keys=%s",
                    e,
                    list(payload.keys()),
                )
                # Acknowledge with 200 OK to prevent VoIP.ms retries
                return web.Response(text="ok", status=200)

            # Process the validated SMS
            await process_inbound_sms(hass, entry, sms)

            return web.Response(text="ok", status=200)
        except Exception as err:
            _LOGGER.error("Error handling VoIP.ms webhook: %s", err)
            return web.Response(status=500)

    async_register(
        hass,
        DOMAIN,
        "VoIP.ms SMS",
        webhook_id,
        webhook_handler,
        allowed_methods=(METH_GET, METH_POST, METH_PUT),
    )

    # Register callback with VoIP.ms API
    try:
        external_url = get_url(hass, prefer_external=True, allow_cloud=True)
        webhook_url = build_webhook_callback_url(external_url, webhook_id)
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


async def async_unregister_inbound_sms_webhook(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Unregister the inbound SMS webhook."""
    webhook_id = f"voipms_{entry.entry_id}"
    async_unregister(hass, webhook_id)