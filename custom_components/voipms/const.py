"""Constants for the VoIP.ms integration."""

import logging
from datetime import timedelta
from enum import StrEnum

DOMAIN = "voipms"

LOGGER = logging.getLogger(__package__)

CONF_DEFAULT_DID = "default_did"

UPDATE_INTERVAL = timedelta(minutes=5)

MIN_SMS_MESSAGE_LENGTH = 1
MAX_SMS_MESSAGE_LENGTH = 160


class WebhookRegistrationStatus(StrEnum):
    """Sanitized webhook registration status for system health."""

    NOT_ATTEMPTED = "not_attempted"
    DISABLED = "disabled"
    REGISTERED = "registered"
    FAILED = "failed"


# Events
EVENT_INBOUND_SMS = "voipms_inbound_sms"
EVENT_INBOUND_CALL = "voipms_inbound_call"
EVENT_OUTBOUND_CALL = "voipms_outbound_call"

DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"
DIRECTION_UNKNOWN = "unknown"

WEBHOOK_CALLBACK_QUERY = (
    "to={TO}&from={FROM}&message={MESSAGE}&id={ID}&date={TIMESTAMP}"
)


def build_webhook_callback_url(base_url: str, webhook_id: str) -> str:
    """Build the VoIP.ms SMS URL callback with query-parameter templates."""
    return f"{base_url}/api/webhook/{webhook_id}?{WEBHOOK_CALLBACK_QUERY}"
