"""Data models for VoIP.ms integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from .const import DIRECTION_INBOUND, DIRECTION_OUTBOUND


class InboundSmsValidationError(ValueError):
    """Raised when inbound SMS payload validation fails."""

    pass


@dataclass(frozen=True)
class InboundSms:
    """Represents an inbound SMS message from VoIP.ms."""

    sender: str  # VoIP.ms "from" field
    recipient: str  # VoIP.ms "to" field
    message: str
    message_id: str  # VoIP.ms "id" field
    timestamp: str  # VoIP.ms "date" field

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


@dataclass(frozen=True)
class CallRecord:
    """Represents a call detail record from VoIP.ms."""

    unique_id: str
    caller_id: str
    destination: str
    description: str
    timestamp: str
    duration: str
    disposition: str
    direction: str

    FIELD_UNIQUE_ID: ClassVar[str] = "uniqueid"
    FIELD_CALLER_ID: ClassVar[str] = "callerid"
    FIELD_DESTINATION: ClassVar[str] = "destination"
    FIELD_DESCRIPTION: ClassVar[str] = "description"
    FIELD_DATE: ClassVar[str] = "date"
    FIELD_DURATION: ClassVar[str] = "duration"
    FIELD_DISPOSITION: ClassVar[str] = "disposition"

    @staticmethod
    def _direction_from_description(description: str) -> str:
        """Classify call direction from the CDR description."""
        normalized = description.lower()
        if (
            "incoming" in normalized
            or "inbound" in normalized
            or "voicemail" in normalized
        ):
            return DIRECTION_INBOUND
        return DIRECTION_OUTBOUND

    @staticmethod
    def _is_voicemail_description(description: str) -> bool:
        """Return whether a CDR description indicates voicemail routing."""
        return "voicemail" in description.lower()

    @staticmethod
    def parse_cdr_record(record: Mapping[str, Any]) -> CallRecord | None:
        """Parse a VoIP.ms CDR record into a CallRecord."""
        timestamp = record.get(CallRecord.FIELD_DATE)
        if not isinstance(timestamp, str) or not timestamp.strip():
            return None

        description = str(record.get(CallRecord.FIELD_DESCRIPTION, ""))
        caller_id = str(record.get(CallRecord.FIELD_CALLER_ID, ""))
        destination = str(record.get(CallRecord.FIELD_DESTINATION, ""))
        duration = str(record.get(CallRecord.FIELD_DURATION, ""))
        disposition = str(record.get(CallRecord.FIELD_DISPOSITION, ""))
        unique_id = record.get(CallRecord.FIELD_UNIQUE_ID)
        if not isinstance(unique_id, str) or not unique_id.strip():
            unique_id = f"{timestamp}|{caller_id}|{destination}|{description}"

        return CallRecord(
            unique_id=unique_id,
            caller_id=caller_id,
            destination=destination,
            description=description,
            timestamp=timestamp,
            duration=duration,
            disposition=disposition,
            direction=CallRecord._direction_from_description(description),
        )

    def is_voicemail(self) -> bool:
        """Return whether this call was routed to voicemail."""
        return self._is_voicemail_description(self.description)

    def to_event_data(self) -> dict[str, str]:
        """Convert to dictionary for event bus delivery."""
        return {
            self.FIELD_UNIQUE_ID: self.unique_id,
            self.FIELD_CALLER_ID: self.caller_id,
            self.FIELD_DESTINATION: self.destination,
            self.FIELD_DESCRIPTION: self.description,
            self.FIELD_DATE: self.timestamp,
            self.FIELD_DURATION: self.duration,
            self.FIELD_DISPOSITION: self.disposition,
            "direction": self.direction,
            "is_voicemail": str(self.is_voicemail()).lower(),
        }
