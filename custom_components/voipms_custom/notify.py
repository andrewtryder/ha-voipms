"""VoIP.ms Custom Notify Service."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry

from .api import VoipMsRestClient
from .const import CONF_DEFAULT_DID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up notify platform."""
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

    def __init__(
        self, hass: HomeAssistant, username: str, password: str, default_did: str
    ) -> None:
        """Initialize the service."""
        self.hass = hass
        self.username = username
        self.password = password
        self.default_did = default_did
        self.client = VoipMsRestClient(username, password)

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Handle a Home Assistant notify call."""
        targets = kwargs.get("target")
        if not targets:
            _LOGGER.error("No target provided for VoIP.ms SMS")
            return

        data = kwargs.get("data") or {}
        did = data.get("did", self.default_did)

        def call_send_sms(target: str):
            return self.client.send_sms(did=did, dst=target, message=message)

        for target in targets:
            try:
                result = await self.hass.async_add_executor_job(call_send_sms, target)

                if result.get("status") != "success":
                    _LOGGER.error("VoIP.ms sendSMS failed: %s", result.get("status"))
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Failed to send VoIP.ms SMS to %s: %s", target, ex)
