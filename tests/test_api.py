"""Test VoIP.ms REST API client."""

from unittest.mock import MagicMock

from custom_components.voipms_custom.api import VoipMsRestClient


def test_get_cdr_passes_call_status_filters() -> None:
    """Test getCDR includes required VoIP.ms call status parameters."""
    client = VoipMsRestClient("user", "pass")
    client.call = MagicMock(return_value={"status": "success", "cdr": []})

    client.get_cdr(date_from="2026-06-23", date_to="2026-06-24", timezone=-4)

    client.call.assert_called_once_with(
        "getCDR",
        date_from="2026-06-23",
        date_to="2026-06-24",
        timezone=-4,
        answered=1,
        noanswer=1,
        busy=1,
        failed=1,
    )
