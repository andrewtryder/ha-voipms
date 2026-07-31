"""Tests for phone number and SMS message validation helpers."""

import pytest

from custom_components.voipms.const import MAX_SMS_MESSAGE_LENGTH
from custom_components.voipms.validation import (
    validate_phone_number,
    validate_sms_message,
)


@pytest.mark.parametrize(
    "value",
    [
        "5551234567",
        "+15551234567",
        "+442071838750",
    ],
)
def test_validate_phone_number_accepts(value: str) -> None:
    """Test accepted NANPA and E.164 phone numbers."""
    assert validate_phone_number(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "555-123-4567",
        "(555) 123-4567",
        "1 555 123 4567",
        "15551234567",
        "+0123456789",
        "123",
        "+123",
        "abcdefghij",
        "１２３４５６７８９０",
        "++15551234567",
        "sip:5551234567@example.com",
    ],
)
def test_validate_phone_number_rejects(value: str) -> None:
    """Test rejected phone number forms."""
    with pytest.raises(ValueError):
        validate_phone_number(value)


def test_validate_phone_number_trims_whitespace() -> None:
    """Test leading and trailing whitespace is trimmed before validation."""
    assert validate_phone_number("  5551234567  ") == "5551234567"


def test_validate_sms_message_accepts_exact_max() -> None:
    """Test a message of exactly MAX_SMS_MESSAGE_LENGTH is accepted."""
    message = "a" * MAX_SMS_MESSAGE_LENGTH
    assert validate_sms_message(message) == message


def test_validate_sms_message_rejects_too_long() -> None:
    """Test a message longer than MAX_SMS_MESSAGE_LENGTH is rejected."""
    with pytest.raises(ValueError):
        validate_sms_message("a" * (MAX_SMS_MESSAGE_LENGTH + 1))


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_validate_sms_message_rejects_empty(value: str) -> None:
    """Test empty and whitespace-only messages are rejected."""
    with pytest.raises(ValueError):
        validate_sms_message(value)


def test_validate_sms_message_preserves_intentional_whitespace() -> None:
    """Test leading/trailing whitespace is preserved when content exists."""
    message = "  hello  "
    assert validate_sms_message(message) == message
