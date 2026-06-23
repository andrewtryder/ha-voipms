"""Config flow for VoIP.ms Custom integration."""
from __future__ import annotations

import logging
from typing import Any
import os

import voluptuous as vol
import zeep
from zeep.exceptions import Fault
from requests.exceptions import RequestException

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_DEFAULT_DID

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEFAULT_DID): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    def test_connection():
        # Load WSDL from local file
        wsdl_path = os.path.join(os.path.dirname(__file__), "server.wsdl")
        client = zeep.Client(wsdl=wsdl_path)

        # Call getBalance to verify credentials
        result = client.service.getBalance(
            api_username=data[CONF_USERNAME],
            api_password=data[CONF_PASSWORD],
        )
        return result

    try:
        result = await hass.async_add_executor_job(test_connection)
    except (Fault, RequestException, ValueError) as ex:
        _LOGGER.error("Connection error: %s", ex)
        raise CannotConnect from ex

    # Check for failure in the result (e.g. status != 'success')
    # VoIP.ms often returns a string 'success' or an array with a status
    # However, getBalance might just return the balance directly or an array with status.
    # We will assume if result contains 'status' and it's not 'success', it failed.
    # Note: Depending on WSDL, it returns different shapes.

    # We do a basic check here. If zeep didn't throw and we got a response,
    # we inspect it. If it's a dict and status is present.
    if isinstance(result, dict) and result.get("status") and result["status"] != "success":
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_USERNAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for VoIP.ms Custom."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
