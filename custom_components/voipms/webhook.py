"""Webhook handling for VoIP.ms integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web
from aiohttp.hdrs import METH_GET, METH_POST
from homeassistant.components.webhook import async_unregister
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from .__init__ import VoipmsConfigEntry
from .api import VoipMsApiError, VoipMsRestClient
from .const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    WebhookRegistrationStatus,
    build_webhook_callback_url,
)
from .models import InboundSms, InboundSmsValidationError
from .processor import process_inbound_sms

_LOGGER = logging.getLogger(__name__)
MAX_PROCESSED_IDS = 1000


def _set_webhook_status(
    entry: VoipmsConfigEntry,
    status: WebhookRegistrationStatus,
    *,
    failure_category: str | None = None,
) -> None:
    """Update sanitized webhook registration status on runtime data."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is None:
        return
    runtime_data.webhook_registration_status = status
    runtime_data.webhook_failure_category = failure_category


async def async_register_inbound_sms_webhook(
    hass: HomeAssistant, entry: VoipmsConfigEntry
) -> None:
    """Register the inbound SMS webhook with VoIP.ms."""
    webhook_id = f"voipms_{entry.entry_id}"

    processed_cache = entry.runtime_data.processed_sms_ids

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
                    "Inbound SMS validated: message_id=%s",
                    sms.message_id,
                )
            except InboundSmsValidationError as e:
                _LOGGER.warning(
                    "Inbound SMS validation failed: %s, payload_keys=%s",
                    e,
                    list(payload.keys()),
                )
                # Acknowledge with 200 OK to prevent VoIP.ms retries
                return web.Response(text="ok", status=200)

            # Deduplicate by message ID
            if sms.message_id in processed_cache:
                _LOGGER.info("Duplicate SMS message_id=%s, skipping", sms.message_id)
                return web.Response(text="ok", status=200)

            # Validate recipient DID
            configured_did = entry.data.get(CONF_DEFAULT_DID)
            if configured_did and sms.recipient != configured_did:
                _LOGGER.warning(
                    "SMS recipient does not match configured DID",
                )
                return web.Response(text="ok", status=200)

            # Process the validated SMS
            await process_inbound_sms(hass, entry, sms)

            processed_cache[sms.message_id] = None
            if len(processed_cache) > MAX_PROCESSED_IDS:
                processed_cache.popitem(last=False)

            return web.Response(text="ok", status=200)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error handling VoIP.ms webhook: %s", err)
            return web.Response(status=500)

    from custom_components import voipms

    voipms.async_register(
        hass,
        DOMAIN,
        "VoIP.ms SMS",
        webhook_id,
        webhook_handler,
        allowed_methods=(METH_GET, METH_POST),
    )

    # Register callback with VoIP.ms API
    if not entry.options.get("manage_webhook", True):
        _set_webhook_status(entry, WebhookRegistrationStatus.DISABLED)
        return

    _set_webhook_status(entry, WebhookRegistrationStatus.NOT_ATTEMPTED)

    try:
        external_url = voipms.get_url(hass, prefer_external=True, allow_cloud=True)
        webhook_url = build_webhook_callback_url(external_url, webhook_id)
        did = entry.data.get(CONF_DEFAULT_DID)
        if not did:
            _set_webhook_status(
                entry,
                WebhookRegistrationStatus.FAILED,
                failure_category="missing_did",
            )
            return

        def register_webhook() -> dict[str, Any]:
            client = VoipMsRestClient(
                entry.data[CONF_USERNAME],
                entry.data[CONF_PASSWORD],
            )
            return client.set_sms(did=did, enable=1, url_callback=webhook_url)

        result = await hass.async_add_executor_job(register_webhook)

        if result.get("status") != "success":
            from homeassistant.helpers import issue_registry as ir

            provider_status = result.get("status", "unknown")
            if not isinstance(provider_status, str) or not provider_status:
                provider_status = "unknown"

            ir.async_create_issue(
                hass,
                DOMAIN,
                "webhook_registration_failed",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="webhook_registration_failed",
                translation_placeholders={"status": provider_status},
            )
            _set_webhook_status(
                entry,
                WebhookRegistrationStatus.FAILED,
                failure_category=provider_status,
            )
            _LOGGER.warning(
                "VoIP.ms webhook registration failed: status=%s", provider_status
            )
        else:
            _set_webhook_status(entry, WebhookRegistrationStatus.REGISTERED)
            _LOGGER.info("Registered VoIP.ms webhook successfully")
    except VoipMsApiError:
        _set_webhook_status(
            entry,
            WebhookRegistrationStatus.FAILED,
            failure_category="network_error",
        )
        _LOGGER.warning(
            "Failed to register webhook with VoIP.ms due to a network or API error. "
            "You may need to configure it manually."
        )
    except Exception:  # noqa: BLE001
        _set_webhook_status(
            entry,
            WebhookRegistrationStatus.FAILED,
            failure_category="unexpected_error",
        )
        _LOGGER.warning(
            "Failed to register webhook with VoIP.ms. You may need to configure it manually.",
        )


async def async_unregister_inbound_sms_webhook(
    hass: HomeAssistant, entry: VoipmsConfigEntry
) -> None:
    """Unregister the inbound SMS webhook."""
    webhook_id = f"voipms_{entry.entry_id}"
    async_unregister(hass, webhook_id)
