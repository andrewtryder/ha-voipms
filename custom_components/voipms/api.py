"""REST API client for VoIP.ms."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_LOGGER = logging.getLogger(__name__)

VOIPMS_REST_API_URL = "https://voip.ms/api/v1/rest.php"
DEFAULT_TIMEOUT = 30
API_USERNAME_PARAM = "api_username"
API_PASSWORD_PARAM = "api_password"
MAX_RESPONSE_BYTES = 1_048_576

_NO_DATA_STATUSES = frozenset(
    {
        "no_cdr",
        "no_voicemails",
        "no_subaccounts",
        "no_sms",
    }
)

_MUTATION_METHODS = frozenset({"sendSMS", "setSMS"})


class VoipMsApiError(Exception):
    """Error raised when the VoIP.ms REST API cannot be reached or parsed."""


def _is_list_or_dict(value: Any) -> bool:
    """Return True if value is a list or dictionary."""
    return isinstance(value, (list, dict))


def _validate_get_balance(result: dict[str, Any]) -> bool:
    """Validate getBalance success payload."""
    return "balance" in result


def _validate_get_cdr(result: dict[str, Any]) -> bool:
    """Validate getCDR success payload."""
    return _is_list_or_dict(result.get("cdr"))


def _validate_get_voicemails(result: dict[str, Any]) -> bool:
    """Validate getVoicemails success payload."""
    return _is_list_or_dict(result.get("voicemails"))


def _validate_get_voicemail_messages(result: dict[str, Any]) -> bool:
    """Validate getVoicemailMessages success payload."""
    return _is_list_or_dict(result.get("messages"))


def _validate_get_sub_accounts(result: dict[str, Any]) -> bool:
    """Validate getSubAccounts success payload."""
    return _is_list_or_dict(result.get("subaccounts"))


def _validate_get_registration_status(result: dict[str, Any]) -> bool:
    """Validate getRegistrationStatus success payload."""
    return result.get("registered") in {"yes", "no"}


def _validate_get_sms(result: dict[str, Any]) -> bool:
    """Validate getSMS success payload."""
    return _is_list_or_dict(result.get("sms"))


_SUCCESS_VALIDATORS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "getBalance": _validate_get_balance,
    "getCDR": _validate_get_cdr,
    "getVoicemails": _validate_get_voicemails,
    "getVoicemailMessages": _validate_get_voicemail_messages,
    "getSubAccounts": _validate_get_sub_accounts,
    "getRegistrationStatus": _validate_get_registration_status,
    "getSMS": _validate_get_sms,
}


def _sanitize_network_error(exc: BaseException) -> str:
    """Build a sanitized network error message that cannot leak credentials."""
    if isinstance(exc, HTTPError):
        code = getattr(exc, "code", None)
        reason = getattr(exc, "reason", None)
        if isinstance(reason, bytes):
            reason = reason.decode("ascii", errors="replace")
        if code is not None:
            if reason:
                return (
                    f"VoIP.ms REST API request failed with HTTP status {code}: {reason}"
                )
            return f"VoIP.ms REST API request failed with HTTP status {code}"
        return "VoIP.ms REST API request failed with an HTTP error"

    if isinstance(exc, TimeoutError):
        return "VoIP.ms REST API request timed out"

    if isinstance(exc, URLError):
        return "VoIP.ms REST API request failed due to a network error"

    if isinstance(exc, OSError):
        return "VoIP.ms REST API request failed due to a connection error"

    return "VoIP.ms REST API request failed"


def _read_bounded_body(response: Any) -> bytes:
    """Read at most MAX_RESPONSE_BYTES from an HTTP response body."""
    content_length = None
    headers = getattr(response, "headers", None)
    if headers is not None:
        raw_length = headers.get("Content-Length")
        if raw_length is not None:
            try:
                parsed = int(raw_length)
            except TypeError, ValueError:
                parsed = None
            else:
                if parsed >= 0:
                    content_length = parsed

    if content_length is not None and content_length > MAX_RESPONSE_BYTES:
        raise VoipMsApiError(
            "VoIP.ms REST API response exceeded the maximum allowed size"
        )

    raw_response = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw_response) > MAX_RESPONSE_BYTES:
        raise VoipMsApiError(
            "VoIP.ms REST API response exceeded the maximum allowed size"
        )
    return raw_response


def _validate_response_shape(method: str, result: dict[str, Any]) -> None:
    """Validate generic and method-specific VoIP.ms response shapes."""
    status = result.get("status")
    if not isinstance(status, str) or not status:
        raise VoipMsApiError("VoIP.ms REST API response did not include a valid status")

    if status in _NO_DATA_STATUSES:
        return

    if status != "success":
        return

    if method in _MUTATION_METHODS:
        return

    validator = _SUCCESS_VALIDATORS.get(method)
    if validator is not None and not validator(result):
        raise VoipMsApiError("VoIP.ms REST API returned an unexpected response shape")


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
        if not isinstance(method, str) or not method:
            raise VoipMsApiError(
                "VoIP.ms REST API method name must be a non-empty string"
            )

        query_params = {
            API_USERNAME_PARAM: self.username,
            API_PASSWORD_PARAM: self.password,
            "method": method,
            "content_type": "json",
            **params,
        }
        encoded_params = urlencode(query_params)
        request = Request(
            f"{self.api_url}?{encoded_params}",
            headers={"User-Agent": "ha-voipms/1.0"},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_response = _read_bounded_body(response)
        except (HTTPError, URLError, TimeoutError, OSError) as ex:
            raise VoipMsApiError(_sanitize_network_error(ex)) from ex

        try:
            text = raw_response.decode("utf-8")
        except UnicodeDecodeError as ex:
            _LOGGER.debug(
                "VoIP.ms REST API returned non-UTF-8 response for method=%s length=%s",
                method,
                len(raw_response),
            )
            raise VoipMsApiError(
                "VoIP.ms REST API returned a response that was not valid UTF-8"
            ) from ex

        try:
            result = json.loads(text)
        except json.JSONDecodeError as ex:
            _LOGGER.debug(
                "VoIP.ms REST API returned invalid JSON for method=%s length=%s",
                method,
                len(raw_response),
            )
            raise VoipMsApiError("VoIP.ms REST API returned invalid JSON") from ex

        if not isinstance(result, dict):
            raise VoipMsApiError(
                "VoIP.ms REST API returned an unexpected response shape"
            )

        _validate_response_shape(method, result)
        return result

    def get_balance(self) -> dict[str, Any]:
        """Fetch the account balance."""
        return self.call("getBalance")

    def get_cdr(self, *, date_from: str, date_to: str, timezone: int) -> dict[str, Any]:
        """Fetch call detail records."""
        return self.call(
            "getCDR",
            date_from=date_from,
            date_to=date_to,
            timezone=timezone,
            answered=1,
            noanswer=1,
            busy=1,
            failed=1,
        )

    def get_sms(self, *, sms: str | int) -> dict[str, Any]:
        """Fetch SMS details by message ID."""
        return self.call("getSMS", sms=str(sms))

    def send_sms(self, *, did: str, dst: str, message: str) -> dict[str, Any]:
        """Send a text message."""
        return self.call("sendSMS", did=did, dst=dst, message=message)

    def set_sms(self, *, did: str, enable: int, url_callback: str) -> dict[str, Any]:
        """Configure text message callback delivery for a DID."""
        return self.call(
            "setSMS",
            did=did,
            enable=enable,
            url_callback_enable=1,
            url_callback=url_callback,
            url_callback_retry=1,
        )

    def get_voicemails(self) -> dict[str, Any]:
        """Fetch voicemail mailbox configurations."""
        return self.call("getVoicemails")

    def get_voicemail_messages(self, *, mailbox: str) -> dict[str, Any]:
        """Fetch voicemail messages for a specific mailbox."""
        return self.call("getVoicemailMessages", mailbox=mailbox)

    def get_sub_accounts(self) -> dict[str, Any]:
        """Fetch all subaccounts."""
        return self.call("getSubAccounts")

    def get_registration_status(self, *, account: str) -> dict[str, Any]:
        """Fetch SIP registration status for a subaccount."""
        return self.call("getRegistrationStatus", account=account)
