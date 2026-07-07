"""Tests for the VoIP.ms helpers."""

from custom_components.voipms.helpers import mask_phone_number


def test_mask_phone_number() -> None:
    """Test phone number masking."""
    assert mask_phone_number("+1234567890") == "+1*****7890"
    assert mask_phone_number("1234567890") == "******7890"
    assert mask_phone_number("+12") == "***"
    assert mask_phone_number("1234") == "****"
    assert mask_phone_number("123") == "***"
    assert mask_phone_number("") == ""
    assert mask_phone_number(None) == ""
