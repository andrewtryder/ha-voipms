"""Helper functions for the VoIP.ms integration."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def voipms_device_info(entry_id: str) -> DeviceInfo:
    """Return common device information for VoIP.ms entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="VoIP.MS",
        manufacturer="VoIP.MS",
    )
