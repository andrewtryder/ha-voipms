"""Config flow for VoIP.ms integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import VoipMsApiError, VoipMsRestClient
from .const import CONF_DEFAULT_DID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Map VoIP.ms API status values to config-flow translation keys.
API_STATUS_ERRORS: dict[str, str] = {
    "invalid_credentials": "invalid_credentials",
    "ip_not_enabled": "ip_not_enabled",
    "api_not_enabled": "api_not_enabled",
    "missing_credentials": "missing_credentials",
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEFAULT_DID): str,
        vol.Optional("manage_webhook", default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    def test_connection() -> dict[str, Any]:
        client = VoipMsRestClient(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        return client.get_balance()

    try:
        result = await hass.async_add_executor_job(test_connection)
    except (VoipMsApiError, ValueError) as ex:
        _LOGGER.error("Connection error: %s", ex)
        raise CannotConnect from ex

    if result.get("status") != "success":
        _LOGGER.warning("VoIP.ms auth failed: %s", result)
        status = result.get("status")
        error_key = API_STATUS_ERRORS.get(status, "invalid_auth")
        raise InvalidAuth(error_key)

    return {"title": data[CONF_USERNAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for VoIP.ms."""

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
            except InvalidAuth as err:
                errors["base"] = err.translation_key
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                manage_webhook = user_input.pop("manage_webhook", True)
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                    options={"manage_webhook": manage_webhook},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle initiation of re-authentication with VoIP.ms."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, **user_input}
            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth as err:
                errors["base"] = err.translation_key
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self._get_reconfigure_entry()

        errors = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth as err:
                errors["base"] = err.translation_key
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                manage_webhook = user_input.pop(
                    "manage_webhook", entry.options.get("manage_webhook", True)
                )
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    options={"manage_webhook": manage_webhook},
                    reason="reconfigure_successful",
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PASSWORD, default=entry.data.get(CONF_PASSWORD, "")
                ): str,
                vol.Required(
                    CONF_DEFAULT_DID,
                    default=entry.data.get(CONF_DEFAULT_DID, ""),
                ): str,
                vol.Optional(
                    "manage_webhook",
                    default=entry.options.get("manage_webhook", True),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for VoIP.ms."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        try:
            self.config_entry = config_entry
        except AttributeError:
            pass  # Provided by base class in HA 2024.12+

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "manage_webhook",
                        default=self.config_entry.options.get("manage_webhook", True),
                    ): bool,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

    def __init__(self, translation_key: str = "invalid_auth") -> None:
        """Initialize with a config-flow error translation key."""
        super().__init__(translation_key=translation_key)
