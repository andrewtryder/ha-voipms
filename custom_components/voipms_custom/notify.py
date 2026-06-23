"""VoIP.ms Custom Notify Service."""
from __future__ import annotations

import logging
import os
from typing import Any

import zeep
from zeep.exceptions import Fault

from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_DEFAULT_DID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up notify platform (not needed for legacy notify, but required by HA entity component flow if treating as entity)."""
    # Notify currently has both legacy async_get_service and entity-based async_setup_entry depending on how it's used.
    # We will just pass since we registered it as a platform but using legacy get_service.
    pass

async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: dict[str, Any] | None = None,
) -> "VoipmsNotificationService" | None:
    """Get the VoIP.ms notification service."""
    if discovery_info is None:
        return None

    return VoipmsNotificationService(
        hass,
        discovery_info[CONF_USERNAME],
        discovery_info[CONF_PASSWORD],
        discovery_info[CONF_DEFAULT_DID],
    )


class VoipmsNotificationService(BaseNotificationService):
    """Implement the notification service for VoIP.ms."""

    def __init__(self, hass: HomeAssistant, username: str, password: str, default_did: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.username = username
        self.password = password
        self.default_did = default_did

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to a user."""
        targets = kwargs.get("target")
        if not targets:
            _LOGGER.error("No target provided for VoIP.ms SMS")
            return

        # Allows overriding DID per message
        data = kwargs.get("data") or {}
        did = data.get("did", self.default_did)

        def send_sms(target: str):
            wsdl_path = os.path.join(os.path.dirname(__file__), "server.wsdl")
            client = zeep.Client(wsdl=wsdl_path)

            return client.service.sendSMS(
                api_username=self.username,
                api_password=self.password,
                did=did,
                dst=target,
                message=message,
            )

        for target in targets:
            try:
                result = await self.hass.async_add_executor_job(send_sms, target)

                # Check status
                if isinstance(result, dict) and result.get("status") != "success":
                     _LOGGER.error("VoIP.ms sendSMS failed: %s", result.get("status"))
            except Exception as ex:
                _LOGGER.error("Failed to send VoIP.ms SMS to %s: %s", target, ex)
