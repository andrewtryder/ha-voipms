"""The VoIP.ms integration."""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.webhook import (  # noqa: F401 — used by test mocks
    async_register,
    async_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryError,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv

from .api import VoipMsApiError, VoipMsRestClient  # noqa: F401 — used by test mocks
from .const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    MAX_SMS_MESSAGE_LENGTH,
    WebhookRegistrationStatus,
)
from .coordinator import VoipmsDataUpdateCoordinator
from .validation import validate_phone_number, validate_sms_message
from .webhook import (
    async_register_inbound_sms_webhook,
    async_unregister_inbound_sms_webhook,
)


@dataclass
class VoipmsData:
    """Runtime data for the VoIP.ms integration."""

    coordinator: VoipmsDataUpdateCoordinator
    processed_sms_ids: OrderedDict[str, None]
    last_sms_entity: Any = None
    last_call_entity: Any = None
    webhook_registration_status: WebhookRegistrationStatus = (
        WebhookRegistrationStatus.NOT_ATTEMPTED
    )
    webhook_failure_category: str | None = None


type VoipmsConfigEntry = ConfigEntry[VoipmsData]

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_SMS = "send_sms"
ATTR_TO = "to"
ATTR_DID = "did"
ATTR_MESSAGE = "message"

SEND_SMS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TO): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_DID): cv.string,
    }
)


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


def _service_validation_error(
    translation_key: str,
    *,
    placeholders: dict[str, str] | None = None,
) -> ServiceValidationError:
    """Build a translated service validation error without leaking inputs."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=translation_key,
        translation_placeholders=placeholders,
    )


async def async_setup_entry(hass: HomeAssistant, entry: VoipmsConfigEntry) -> bool:
    """Set up VoIP.ms from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    stored_did = entry.data.get(CONF_DEFAULT_DID)
    if stored_did is not None:
        try:
            validate_phone_number(stored_did)
        except ValueError as err:
            raise ConfigEntryError(
                translation_domain=DOMAIN,
                translation_key="invalid_did",
            ) from err

    coordinator = VoipmsDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    manage_webhook = entry.options.get("manage_webhook", True)
    entry.runtime_data = VoipmsData(
        coordinator=coordinator,
        processed_sms_ids=OrderedDict(),
        webhook_registration_status=(
            WebhookRegistrationStatus.DISABLED
            if not manage_webhook
            else WebhookRegistrationStatus.NOT_ATTEMPTED
        ),
    )

    async def async_send_sms_service(call: ServiceCall) -> None:
        """Handle the voipms.send_sms service call."""
        try:
            to = validate_phone_number(call.data[ATTR_TO])
        except ValueError as err:
            raise _service_validation_error("invalid_recipient") from err

        try:
            message = validate_sms_message(call.data[ATTR_MESSAGE])
        except ValueError as err:
            raw_message = call.data[ATTR_MESSAGE]
            if not isinstance(raw_message, str) or not raw_message.strip():
                raise _service_validation_error("empty_message") from err
            raise _service_validation_error(
                "message_too_long",
                placeholders={"max_length": str(MAX_SMS_MESSAGE_LENGTH)},
            ) from err

        explicit_did = call.data.get(ATTR_DID)
        if explicit_did is not None:
            try:
                did = validate_phone_number(explicit_did)
            except ValueError as err:
                raise _service_validation_error("invalid_did") from err
        else:
            configured_did = entry.data.get(CONF_DEFAULT_DID)
            if configured_did is None or (
                isinstance(configured_did, str) and not configured_did.strip()
            ):
                raise _service_validation_error("missing_did")
            try:
                did = validate_phone_number(configured_did)
            except ValueError as err:
                raise _service_validation_error("invalid_did") from err

        try:
            result = await hass.async_add_executor_job(
                partial(coordinator.client.send_sms, did=did, dst=to, message=message)
            )
        except VoipMsApiError as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="sms_network_error",
            ) from ex

        if result.get("status") != "success":
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="sms_provider_rejected",
                translation_placeholders={
                    "status": str(result.get("status", "unknown")),
                },
            )

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_SMS, async_send_sms_service, schema=SEND_SMS_SCHEMA
    )

    if hass.http is not None:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/voipms-frontend",
                    str(Path(__file__).parent / "frontend"),
                    cache_headers=False,
                )
            ]
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_inbound_sms_webhook(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: VoipmsConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await async_unregister_inbound_sms_webhook(hass, entry)
        if (
            hass.services.has_service(DOMAIN, "send_sms")
            and len(hass.config_entries.async_loaded_entries(DOMAIN)) <= 1
        ):
            hass.services.async_remove(DOMAIN, "send_sms")
        entry.runtime_data = None

    return unload_ok
