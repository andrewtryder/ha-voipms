"""Provide info to system health."""

from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .api import VOIPMS_REST_API_URL
from .const import DOMAIN

_ENTRY_STATE_MAP: dict[ConfigEntryState, str] = {
    ConfigEntryState.LOADED: "loaded",
    ConfigEntryState.SETUP_RETRY: "setup_retry",
    ConfigEntryState.SETUP_ERROR: "setup_error",
    ConfigEntryState.NOT_LOADED: "not_loaded",
}


@callback
def async_register(
    hass: HomeAssistant,
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register system health callbacks."""
    register.async_register_info(async_get_system_health_info)


async def async_get_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the system health page."""
    info: dict[str, Any] = {
        "api_endpoint_reachable": system_health.async_check_can_reach_url(
            hass, VOIPMS_REST_API_URL
        ),
        "last_update_success": None,
        "config_entry_state": "missing",
        "webhook_management_enabled": False,
        "webhook_registration_status": "not_attempted",
    }

    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return info

    entry = entries[0]
    info["config_entry_state"] = _ENTRY_STATE_MAP.get(entry.state, "not_loaded")
    info["webhook_management_enabled"] = bool(entry.options.get("manage_webhook", True))

    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is None:
        return info

    coordinator = getattr(runtime_data, "coordinator", None)
    if coordinator is not None:
        info["last_update_success"] = bool(
            getattr(coordinator, "last_update_success", False)
        )

    status = getattr(runtime_data, "webhook_registration_status", None)
    if status is not None:
        info["webhook_registration_status"] = (
            status.value if hasattr(status, "value") else str(status)
        )

    return info
