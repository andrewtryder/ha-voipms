"""Test VoIP.ms REST API client."""

from __future__ import annotations

import json
import logging
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from custom_components.voipms.api import (
    MAX_RESPONSE_BYTES,
    VoipMsApiError,
    VoipMsRestClient,
)


def _response(
    body: bytes,
    *,
    content_length: str | None = "auto",
) -> MagicMock:
    """Build a synthetic HTTP response object."""
    response = MagicMock()
    headers = Message()
    if content_length == "auto":
        headers["Content-Length"] = str(len(body))
    elif content_length is not None:
        headers["Content-Length"] = content_length
    response.headers = headers
    response.read = MagicMock(return_value=body)
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


def _patch_urlopen(response: MagicMock):
    """Patch urlopen to return a context-managed response."""
    return patch(
        "custom_components.voipms.api.urlopen",
        return_value=response,
    )


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


def test_get_sub_accounts() -> None:
    """Test getSubAccounts calls the correct API method."""
    client = VoipMsRestClient("user", "pass")
    client.call = MagicMock(return_value={"status": "success", "subaccounts": []})

    client.get_sub_accounts()

    client.call.assert_called_once_with("getSubAccounts")


def test_get_registration_status() -> None:
    """Test getRegistrationStatus calls the correct API method with account."""
    client = VoipMsRestClient("user", "pass")
    client.call = MagicMock(return_value={"status": "success", "registered": "yes"})

    client.get_registration_status(account="100001_ata")

    client.call.assert_called_once_with("getRegistrationStatus", account="100001_ata")


@pytest.mark.parametrize(
    "exception",
    [
        URLError("Network error"),
        TimeoutError("Timeout"),
        OSError("OS error"),
        HTTPError(
            "https://voip.ms/api/v1/rest.php?api_username=secret_user&api_password=secret_pass",
            500,
            "Internal Server Error",
            {},
            None,
        ),
    ],
)
def test_api_client_handles_http_errors(exception: Exception) -> None:
    """Test API client wraps expected network exceptions in VoipMsApiError."""
    client = VoipMsRestClient("secret_user", "secret_pass")

    with patch("custom_components.voipms.api.urlopen", side_effect=exception):
        with pytest.raises(VoipMsApiError) as exc_info:
            client.call("some_method")

        message = str(exc_info.value)
        assert "secret_user" not in message
        assert "secret_pass" not in message
        assert "api_username" not in message
        assert "api_password" not in message
        assert "https://voip.ms/api/v1/rest.php?" not in message


def test_http_error_includes_status_code_only() -> None:
    """Test HTTP error messages include status code without the request URL."""
    client = VoipMsRestClient("secret_user", "secret_pass")
    error = HTTPError(
        "https://voip.ms/api/v1/rest.php?api_username=secret_user&api_password=secret_pass",
        500,
        "Internal Server Error",
        {},
        None,
    )

    with patch("custom_components.voipms.api.urlopen", side_effect=error):
        with pytest.raises(VoipMsApiError) as exc_info:
            client.call("getBalance")

    message = str(exc_info.value)
    assert "500" in message
    assert "secret_user" not in message
    assert "secret_pass" not in message
    assert "?api_username=" not in message


def test_response_under_byte_limit() -> None:
    """Test response smaller than the byte limit succeeds."""
    body = json.dumps({"status": "success", "balance": "1.00"}).encode()
    response = _response(body)
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getBalance")

    assert result["status"] == "success"
    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_response_exactly_byte_limit() -> None:
    """Test response exactly equal to the byte limit succeeds."""
    prefix = b'{"status":"success","balance":"1.00","pad":"'
    suffix = b'"}'
    pad_len = MAX_RESPONSE_BYTES - len(prefix) - len(suffix)
    body = prefix + (b"x" * pad_len) + suffix
    assert len(body) == MAX_RESPONSE_BYTES

    response = _response(body)
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getBalance")

    assert result["status"] == "success"
    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_response_one_byte_over_limit() -> None:
    """Test response one byte over the limit is rejected."""
    body = b"x" * (MAX_RESPONSE_BYTES + 1)
    response = _response(body, content_length=None)
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="maximum allowed size"):
            client.call("getBalance")

    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_content_length_over_limit() -> None:
    """Test Content-Length over the limit rejects before reading the body."""
    response = _response(b"", content_length=str(MAX_RESPONSE_BYTES + 1))
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="maximum allowed size"):
            client.call("getBalance")

    response.read.assert_not_called()


def test_missing_content_length_uses_bounded_read() -> None:
    """Test missing Content-Length still uses a bounded read."""
    body = json.dumps({"status": "success", "balance": "1.00"}).encode()
    response = _response(body, content_length=None)
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getBalance")

    assert result["balance"] == "1.00"
    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_malformed_content_length_uses_bounded_read() -> None:
    """Test malformed Content-Length still uses a bounded read."""
    body = json.dumps({"status": "success", "balance": "1.00"}).encode()
    response = _response(body, content_length="not-a-number")
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getBalance")

    assert result["status"] == "success"
    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_invalid_utf8() -> None:
    """Test invalid UTF-8 responses raise a sanitized error."""
    response = _response(b"\xff\xfe")
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="not valid UTF-8"):
            client.call("getBalance")


def test_invalid_json_does_not_log_raw_body(caplog: pytest.LogCaptureFixture) -> None:
    """Test invalid JSON handling does not log the raw body."""
    raw = b"not-json-at-all"
    response = _response(raw)
    client = VoipMsRestClient("user", "pass")

    with (
        _patch_urlopen(response),
        caplog.at_level(logging.DEBUG, logger="custom_components.voipms.api"),
    ):
        with pytest.raises(VoipMsApiError, match="invalid JSON"):
            client.call("getBalance")

    assert b"not-json-at-all".decode() not in caplog.text
    assert "not-json-at-all" not in caplog.text


def test_json_list_rejected() -> None:
    """Test JSON list responses are rejected."""
    response = _response(json.dumps([{"status": "success"}]).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getBalance")


def test_missing_status() -> None:
    """Test responses without a status key are rejected."""
    response = _response(json.dumps({"balance": "1.00"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="valid status"):
            client.call("getBalance")


def test_empty_status() -> None:
    """Test empty status values are rejected."""
    response = _response(json.dumps({"status": "", "balance": "1.00"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="valid status"):
            client.call("getBalance")


def test_non_string_status() -> None:
    """Test non-string status values are rejected."""
    response = _response(json.dumps({"status": 1, "balance": "1.00"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="valid status"):
            client.call("getBalance")


def test_get_balance_success_without_balance() -> None:
    """Test getBalance success without balance field is rejected."""
    response = _response(json.dumps({"status": "success"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getBalance")


def test_get_cdr_invalid_payload() -> None:
    """Test getCDR success with invalid cdr type is rejected."""
    response = _response(json.dumps({"status": "success", "cdr": "oops"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getCDR")


def test_get_voicemails_invalid_payload() -> None:
    """Test getVoicemails success with invalid payload is rejected."""
    response = _response(json.dumps({"status": "success", "voicemails": 1}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getVoicemails")


def test_get_voicemail_messages_invalid_payload() -> None:
    """Test getVoicemailMessages success with invalid payload is rejected."""
    response = _response(json.dumps({"status": "success", "messages": 1}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getVoicemailMessages")


def test_get_sub_accounts_invalid_payload() -> None:
    """Test getSubAccounts success with invalid payload is rejected."""
    response = _response(json.dumps({"status": "success", "subaccounts": 1}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getSubAccounts")


def test_get_registration_status_unexpected_registered() -> None:
    """Test getRegistrationStatus rejects unexpected registered values."""
    response = _response(
        json.dumps({"status": "success", "registered": "maybe"}).encode()
    )
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getRegistrationStatus")


def test_get_sms() -> None:
    """Test get_sms calls getSMS with sms parameter."""
    client = VoipMsRestClient("user", "pass")
    client.call = MagicMock(return_value={"status": "success", "sms": []})

    client.get_sms(sms="12345")

    client.call.assert_called_once_with("getSMS", sms="12345")


def test_set_sms_includes_retry() -> None:
    """Test set_sms passes url_callback_retry=1."""
    client = VoipMsRestClient("user", "pass")
    client.call = MagicMock(return_value={"status": "success"})

    client.set_sms(did="5551234567", enable=1, url_callback="http://example.com")

    client.call.assert_called_once_with(
        "setSMS",
        did="5551234567",
        enable=1,
        url_callback_enable=1,
        url_callback="http://example.com",
        url_callback_retry=1,
    )


def test_get_sms_valid_payload_list() -> None:
    """Test getSMS with list payload is accepted."""
    response = _response(
        json.dumps(
            {"status": "success", "sms": [{"id": "123", "message": "hi"}]}
        ).encode()
    )
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getSMS", sms="123")

    assert result["status"] == "success"
    assert len(result["sms"]) == 1


def test_get_sms_valid_payload_dict() -> None:
    """Test getSMS with dict payload is accepted."""
    response = _response(
        json.dumps(
            {"status": "success", "sms": {"0": {"id": "123", "message": "hi"}}}
        ).encode()
    )
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call("getSMS", sms="123")

    assert result["status"] == "success"


def test_get_sms_invalid_payload() -> None:
    """Test getSMS with invalid payload is rejected."""
    response = _response(json.dumps({"status": "success", "sms": "invalid"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        with pytest.raises(VoipMsApiError, match="unexpected response shape"):
            client.call("getSMS", sms="123")


@pytest.mark.parametrize(
    ("method", "payload"),
    [
        ("getCDR", {"status": "no_cdr"}),
        ("getVoicemails", {"status": "no_voicemails"}),
        ("getSubAccounts", {"status": "no_subaccounts"}),
        ("getSMS", {"status": "no_sms"}),
    ],
)
def test_valid_no_data_responses(method: str, payload: dict) -> None:
    """Test known no-data statuses are accepted without success fields."""
    response = _response(json.dumps(payload).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call(method)

    assert result["status"] == payload["status"]


@pytest.mark.parametrize("method", ["sendSMS", "setSMS"])
def test_valid_mutation_responses(method: str) -> None:
    """Test sendSMS and setSMS success responses need only a status."""
    response = _response(json.dumps({"status": "success"}).encode())
    client = VoipMsRestClient("user", "pass")

    with _patch_urlopen(response):
        result = client.call(method)

    assert result["status"] == "success"


def test_empty_method_name_rejected() -> None:
    """Test empty method names are rejected before making a request."""
    client = VoipMsRestClient("user", "pass")
    with patch("custom_components.voipms.api.urlopen") as mock_urlopen:
        with pytest.raises(VoipMsApiError, match="method name"):
            client.call("")
        mock_urlopen.assert_not_called()


def test_network_error_message_omits_full_url() -> None:
    """Test network error messages do not contain the full request URL."""
    client = VoipMsRestClient("secret_user", "secret_pass")
    with patch(
        "custom_components.voipms.api.urlopen",
        side_effect=URLError(
            "https://voip.ms/api/v1/rest.php?api_username=secret_user&api_password=secret_pass"
        ),
    ):
        with pytest.raises(VoipMsApiError) as exc_info:
            client.call("getBalance")

    message = str(exc_info.value)
    assert "secret_user" not in message
    assert "secret_pass" not in message
    assert "https://voip.ms/api/v1/rest.php?" not in message
