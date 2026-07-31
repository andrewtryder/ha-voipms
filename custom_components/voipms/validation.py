"""Input validation helpers for the VoIP.ms integration."""

from __future__ import annotations

import re

from .const import MAX_SMS_MESSAGE_LENGTH, MIN_SMS_MESSAGE_LENGTH

# Exactly 10 ASCII digits (NANPA).
_NANPA_PATTERN = re.compile(r"^[0-9]{10}$")

# E.164: leading +, 8–15 digits total after +, first digit 1–9.
_E164_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")


def validate_phone_number(value: str) -> str:
    """Return the trimmed canonical number or raise ValueError.

    Accepted forms:
    * NANPA: exactly 10 ASCII digits (e.g. ``5551234567``)
    * E.164: ``+`` followed by 8–15 ASCII digits, first digit 1–9
    """
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string")

    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Phone number cannot be empty")

    if _NANPA_PATTERN.fullmatch(trimmed) or _E164_PATTERN.fullmatch(trimmed):
        return trimmed

    raise ValueError("Phone number is not a valid NANPA or E.164 number")


def validate_sms_message(value: str) -> str:
    """Return the original message or raise ValueError.

    Rejects empty and whitespace-only strings and messages longer than
    ``MAX_SMS_MESSAGE_LENGTH`` Unicode code points. Leading/trailing
    whitespace is preserved when the message is otherwise valid.
    """
    if not isinstance(value, str):
        raise ValueError("SMS message must be a string")

    if not value or not value.strip():
        raise ValueError("SMS message cannot be empty")

    if len(value) < MIN_SMS_MESSAGE_LENGTH:
        raise ValueError("SMS message cannot be empty")

    if len(value) > MAX_SMS_MESSAGE_LENGTH:
        raise ValueError("SMS message exceeds maximum length")

    return value
