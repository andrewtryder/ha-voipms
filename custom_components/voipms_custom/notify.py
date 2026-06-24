"""VoIP.MS Notify platform."""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.service import async_set_service_schema

from .api import VoipMsRestClient
from .const import CONF_DEFAULT_DID, DOMAIN

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VoIP.MS notify platform from a config entry."""
    entity = VoipmsNotifyEntity(entry)
    async_add_entities([entity])

    @callback
    def async_send_sms_service(call: ServiceCall) -> None:
        """Handle the voipms_custom.send_sms service call."""
        to = call.data[ATTR_TO]
        message = call.data[ATTR_MESSAGE]
        did = call.data.get(ATTR_DID, entity.default_did)
        hass.async_create_task(entity.async_send_sms(did, to, message))

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_SMS, async_send_sms_service, schema=SEND_SMS_SCHEMA
    )

    service_desc = {
        "name": "Send an SMS",
        "description": "Send an SMS message through VoIP.MS.",
        "fields": {
            ATTR_TO: {
                "name": "To",
                "description": "Destination phone number.",
                "required": True,
            },
            ATTR_MESSAGE: {
                "name": "Message",
                "description": "Text message to send.",
                "required": True,
            },
            ATTR_DID: {
                "name": "From DID",
                "description": "Sender DID. Defaults to the config entry DID.",
                "required": False,
            },
        },
    }
    async_set_service_schema(hass, DOMAIN, SERVICE_SEND_SMS, service_desc)


class VoipmsNotifyEntity(NotifyEntity):
    """Representation of a VoIP.MS SMS notify entity."""

    _attr_has_entity_name = True
    _attr_name = "SMS"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the notify entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sms"
        self._client = VoipMsRestClient(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
        self._default_did = entry.data[CONF_DEFAULT_DID]

    @property
    def default_did(self) -> str:
        """Return the default DID."""
        return self._default_did

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information linking this entity to the integration."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "VoIP.MS",
            "manufacturer": "VoIP.MS",
        }

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message via VoIP.MS SMS.

        The standard notify.send_message service has no target field, so this
        is a convenience for automations that already know the recipient. Use
        the voipms_custom.send_sms service to specify a recipient.
        """
        _LOGGER.warning(
            "notify.send_message has no recipient; call the %s.%s service with"
            " a 'to' field instead",
            DOMAIN,
            SERVICE_SEND_SMS,
        )

    async def async_send_sms(self, did: str, to: str, message: str) -> None:
        """Send an SMS via VoIP.MS."""
        try:
            result = await self.hass.async_add_executor_job(
                partial(self._client.send_sms, did=did, dst=to, message=message)
            )
            if result.get("status") != "success":
                _LOGGER.error("VoIP.MS sendSMS failed: %s", result.get("status"))
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error("Failed to send VoIP.MS SMS to %s: %s", to, ex)
