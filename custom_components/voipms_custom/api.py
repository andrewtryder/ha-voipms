"""REST API client for VoIP.ms."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_LOGGER = logging.getLogger(__name__)

VOIPMS_REST_API_URL = "https://voip.ms/api/v1/rest.php"
DEFAULT_TIMEOUT = 30


class VoipMsApiError(Exception):
    """Error raised when the VoIP.ms REST API cannot be reached or parsed."""


class VoipMsRestClient:
    """Minimal blocking REST client for the VoIP.ms API."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        api_url: str = VOIPMS_REST_API_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the REST client."""
        self.username = username
        self.password = password
        self.api_url = api_url
        self.timeout = timeout

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        """Call a VoIP.ms REST API method and return the decoded JSON response."""
        query_params = {
            "api_username": self.username,
            "api_password": self.password,
            "method": method,
            "format": "json",
            **params,
        }
        encoded_params = urlencode(query_params)
        request = Request(
            f"{self.api_url}?{encoded_params}",
            headers={"User-Agent": "ha-voipms/1.0"},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                raw_response = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as ex:
            raise VoipMsApiError(f"VoIP.ms REST API request failed: {ex}") from ex

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as ex:
            _LOGGER.debug("Invalid VoIP.ms REST response: %s", raw_response)
            raise VoipMsApiError("VoIP.ms REST API returned invalid JSON") from ex

        if not isinstance(result, dict):
            raise VoipMsApiError("VoIP.ms REST API returned an unexpected response shape")

        return result

    def get_balance(self) -> dict[str, Any]:
        """Fetch the account balance."""
        return self.call("getBalance")

    def get_cdr(self, *, date_from: str, date_to: str) -> dict[str, Any]:
        """Fetch call detail records."""
        return self.call("getCDR", date_from=date_from, date_to=date_to)

    def send_sms(self, *, did: str, dst: str, message: str) -> dict[str, Any]:
        """Send an SMS message."""
        return self.call("sendSMS", did=did, dst=dst, message=message)

    def set_sms(self, *, did: str, enable: int, url_callback: str) -> dict[str, Any]:
        """Set SMS callback delivery for a DID."""
        return self.call("setSMS", did=did, enable=enable, url_callback=url_callback)
