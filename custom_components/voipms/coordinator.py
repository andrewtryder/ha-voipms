"""Data update coordinator for VoIP.ms integration."""

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.util import dt as dt_util

from .api import VoipMsApiError, VoipMsRestClient
from .const import DIRECTION_INBOUND, DOMAIN, UPDATE_INTERVAL
from .models import CallRecord

_LOGGER = logging.getLogger(__name__)


class VoipmsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching VoIP.ms data."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the data update coordinator."""
        self.config_entry = config_entry
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.client = VoipMsRestClient(self.username, self.password)
        self._seen_call_ids: set[str] = set()
        self._calls_initialized = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from VoIP.ms."""
        data = await self.hass.async_add_executor_job(self._fetch_data)
        new_calls = data.pop("new_calls", [])
        if new_calls:
            from .processor import process_call

            for call in new_calls:
                await process_call(self.hass, self.config_entry, call)
        return data

    def _fetch_data(self) -> dict:
        """Fetch data from VoIP.ms REST API (blocking call)."""
        data: dict[str, Any] = {
            "balance": None,
            "inbound_calls_24h": 0,
            "outbound_calls_24h": 0,
            "voicemail_count": 0,
            "new_calls": [],
            "registrations": {},
        }

        try:
            balance_result = self.client.get_balance()

            if balance_result.get("status") == "success":
                data["balance"] = self._extract_balance(balance_result.get("balance"))
            else:
                _LOGGER.warning("Failed to fetch balance: %s", balance_result)

        except (VoipMsApiError, ValueError) as ex:
            _LOGGER.warning("Error fetching balance: %s", ex)

        try:
            registrations: dict[str, dict[str, Any]] = {}
            subs_result = self.client.get_sub_accounts()
            if subs_result.get("status") == "success":
                subaccounts = subs_result.get("subaccounts", [])
                if isinstance(subaccounts, dict):
                    subaccounts = [subaccounts]
                if isinstance(subaccounts, list):
                    for sub in subaccounts:
                        account_name = sub.get("account")
                        if not account_name:
                            continue
                        try:
                            reg_result = self.client.get_registration_status(
                                account=account_name
                            )
                            registrations[account_name] = {
                                "registered": (reg_result.get("registered") == "yes"),
                                "description": sub.get("description", ""),
                                "device_type": sub.get("device_type", ""),
                                "callerid_number": sub.get("callerid_number", ""),
                                "protocol": sub.get("protocol", ""),
                            }
                        except (VoipMsApiError, ValueError) as ex:
                            _LOGGER.warning(
                                "Error fetching registration status for %s: %s",
                                account_name,
                                ex,
                            )
            data["registrations"] = registrations
        except (VoipMsApiError, ValueError) as ex:
            _LOGGER.warning("Error fetching subaccounts: %s", ex)

        try:
            vm_result = self.client.get_voicemails()
            if vm_result.get("status") == "success":
                mailboxes = vm_result.get("voicemails", [])
                if isinstance(mailboxes, dict):
                    mailboxes = [mailboxes]
                if isinstance(mailboxes, list):
                    total_messages = 0
                    for mailbox in mailboxes:
                        if not isinstance(mailbox, dict):
                            continue
                        mailbox_id = mailbox.get("mailbox")
                        if not mailbox_id:
                            continue
                        try:
                            msg_result = self.client.get_voicemail_messages(
                                mailbox=mailbox_id
                            )
                            if msg_result.get("status") == "success":
                                messages = msg_result.get("messages", [])
                                if isinstance(messages, dict):
                                    messages = [messages]
                                if isinstance(messages, list):
                                    total_messages += len(messages)
                        except (VoipMsApiError, ValueError) as ex:
                            _LOGGER.warning(
                                "Error fetching messages for mailbox %s: %s",
                                mailbox_id,
                                ex,
                            )
                    data["voicemail_count"] = total_messages
            else:
                _LOGGER.debug("Failed to fetch voicemails: %s", vm_result)
        except (VoipMsApiError, ValueError) as ex:
            _LOGGER.warning("Error fetching voicemails: %s", ex)

        try:
            now = dt_util.now()
            yesterday = now - timedelta(days=1)

            date_from = yesterday.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")
            timezone = self._timezone_offset_hours(now)

            cdr_result = self.client.get_cdr(
                date_from=date_from,
                date_to=date_to,
                timezone=timezone,
            )

            if cdr_result.get("status") == "success":
                cdrs = cdr_result.get("cdr", [])
                if isinstance(cdrs, dict):
                    cdrs = [cdrs]

                inbound_count = 0
                outbound_count = 0
                new_calls: list[CallRecord] = []
                threshold_time = now.replace(tzinfo=None) - timedelta(hours=24)

                for call in cdrs:
                    try:
                        call_record = CallRecord.parse_cdr_record(call)
                        if call_record is None:
                            continue

                        call_date = datetime.strptime(
                            call_record.timestamp, "%Y-%m-%d %H:%M:%S"
                        )
                        if call_date < threshold_time:
                            continue

                        if call_record.direction == DIRECTION_INBOUND:
                            inbound_count += 1
                        else:
                            outbound_count += 1

                        if call_record.unique_id in self._seen_call_ids:
                            continue
                        self._seen_call_ids.add(call_record.unique_id)
                        if self._calls_initialized:
                            new_calls.append(call_record)
                    except ValueError:
                        pass

                if not self._calls_initialized:
                    self._calls_initialized = True

                data["inbound_calls_24h"] = inbound_count
                data["outbound_calls_24h"] = outbound_count
                data["new_calls"] = new_calls

            else:
                _LOGGER.debug("No CDRs found or failed: %s", cdr_result)

        except (VoipMsApiError, ValueError) as ex:
            _LOGGER.error("Error fetching CDR: %s", ex)

        return data

    @staticmethod
    def _extract_balance(balance: Any) -> Any:
        """Extract the current balance from simple or advanced balance responses."""
        if isinstance(balance, dict):
            return balance.get("current_balance")
        return balance

    @staticmethod
    def _timezone_offset_hours(now: datetime) -> int:
        """Return a VoIP.ms-compatible whole-hour UTC offset."""
        offset = now.utcoffset()
        if offset is None:
            return 0
        return int(offset.total_seconds() // 3600)
