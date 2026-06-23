"""Constants for the VoIP.ms Custom integration."""
import logging
from datetime import timedelta

DOMAIN = "voipms_custom"

LOGGER = logging.getLogger(__package__)

CONF_DEFAULT_DID = "default_did"

UPDATE_INTERVAL = timedelta(minutes=5)

# Events
EVENT_INBOUND_SMS = "voipms_inbound_sms"
