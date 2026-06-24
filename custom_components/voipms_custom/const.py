"""Constants for the VoIP.ms Custom integration."""

import logging
from datetime import timedelta

DOMAIN = "voipms_custom"

LOGGER = logging.getLogger(__package__)

CONF_DEFAULT_DID = "default_did"

UPDATE_INTERVAL = timedelta(minutes=5)

# Events
EVENT_INBOUND_SMS = "voipms_inbound_sms"

WEBHOOK_CALLBACK_QUERY = (
    "to={TO}&from={FROM}&message={MESSAGE}&id={ID}&date={TIMESTAMP}"
)


def build_webhook_callback_url(base_url: str, webhook_id: str) -> str:
    """Build the VoIP.ms SMS URL callback with query-parameter templates."""
    return f"{base_url}/api/webhook/{webhook_id}?{WEBHOOK_CALLBACK_QUERY}"
