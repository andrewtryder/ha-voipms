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


def mask_phone_number(phone_number: str | None) -> str:
    """Mask a phone number, keeping only the last 4 digits visible.

    Examples:
        +1234567890 -> +1******7890
        1234567890 -> ******7890
        123 -> ***
        None -> ""
    """
    if not phone_number:
        return ""

    phone_str = str(phone_number)

    # If the string is too short, just return asterisks
    if len(phone_str) <= 4:
        return "*" * len(phone_str)

    has_plus = phone_str.startswith("+")

    # Keep the plus if it exists, and the last 4 digits
    if has_plus:
        last_four = phone_str[-4:]
        prefix = phone_str[:2]  # e.g. +1
        # The number of asterisks should be the length of the string minus the prefix and last four
        asterisks = "*" * (len(phone_str) - len(prefix) - 4)
        return f"{prefix}{asterisks}{last_four}"
    else:
        last_four = phone_str[-4:]
        asterisks = "*" * (len(phone_str) - 4)
        return f"{asterisks}{last_four}"
