"""Data models for VoIP.ms integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from homeassistant.const import CONF_MESSAGE, CONF_SENDER, CONF_RECIPIENT, CONF_ID, CONF_TIMESTAMP


class InboundSmsValidationError(ValueError):
    """Raised when inbound SMS payload validation fails."""
    pass


@dataclass(frozen=True)
class InboundSms:
    """Represents an inbound SMS message from VoIP.ms."""

    sender: str          # VoIP.ms "from" field
    recipient: str       # VoIP.ms "to" field
    message: str
    message_id: str      # VoIP.ms "id" field
    timestamp: str        # VoIP.ms "date" field

    # Constants for field names used in webhook payloads
    FIELD_FROM = "from"
    FIELD_TO = "to"
    FIELD_MESSAGE = "message"
    FIELD_ID = "id"
    FIELD_DATE = "date"

    @staticmethod
    def parse_inbound_sms(payload: Mapping[str, Any]) -> InboundSms:
        """Parse and validate an inbound SMS payload from a webhook.

        Args:
            payload: Webhook data (GET query or POST body)

        Returns:
            InboundSms: Validated model instance

        Raises:
            InboundSmsValidationError: If any required field is missing or empty
        """
        # Required field names in VoIP.ms webhook payload
        required_fields = [
            InboundSms.FIELD_FROM,
            InboundSms.FIELD_TO,
            InboundSms.FIELD_MESSAGE,
            InboundSms.FIELD_ID,
            InboundSms.FIELD_DATE,
        ]

        # Identify missing or empty fields
        missing_or_empty = []
        invalid_types = []

        for field_name in required_fields:
            value = payload.get(field_name)
            if value is None:
                missing_or_empty.append(field_name)
            elif not isinstance(value, str) or not value.strip():
                invalid_types.append(field_name)

        if missing_or_empty:
            raise InboundSmsValidationError(
                f"Missing or empty fields in inbound SMS payload: {', '.join(missing_or_empty)}"
            )
        if invalid_types:
            raise InboundSmsValidationError(
                f"Invalid field types/values in inbound SMS payload: {', '.join(invalid_types)}"
            )

        # Map VoIP.ms field names to model fields
        return InboundSms(
            sender=payload[InboundSms.FIELD_FROM],
            recipient=payload[InboundSms.FIELD_TO],
            message=payload[InboundSms.FIELD_MESSAGE].strip(),
            message_id=payload[InboundSms.FIELD_ID],
            timestamp=payload[InboundSms.FIELD_DATE],
        )

    def to_event_data(self) -> dict[str, str]:
        """Convert to dictionary for event bus delivery.

        Returns:
            dict with field names matching the original VoIP.ms webhook payload.
        """
        return {
            self.FIELD_FROM: self.sender,
            self.FIELD_TO: self.recipient,
            self.FIELD_MESSAGE: self.message,
            self.FIELD_ID: self.message_id,
            self.FIELD_DATE: self.timestamp,
        }