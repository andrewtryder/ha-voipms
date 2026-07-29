"""Data update coordinator for VoIP.ms integration."""

import logging

from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import VoipMsApiError, VoipMsRestClient
from .const import DIRECTION_INBOUND, DIRECTION_OUTBOUND, DOMAIN, UPDATE_INTERVAL
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
        self._seen_call_ids: dict[str, datetime] = {}
        self._calls_initialized = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from VoIP.ms."""
        data = await self.hass.async_add_executor_job(self._fetch_data, self.data)
        new_calls = data.pop("new_calls", [])
        if new_calls:
            from .processor import process_call

            for call in new_calls:
                await process_call(self.hass, self.config_entry, call)
        return data

    def _fetch_data(self, previous_data: dict | None = None) -> dict:
        """Fetch data from VoIP.ms REST API (blocking call)."""
        data: dict[str, Any] = {
            "balance": None,
            "inbound_calls_24h": 0,
            "outbound_calls_24h": 0,
            "voicemail_count": 0,
            "new_calls": [],
            "registrations": {},
        }
        if previous_data:
            data.update(previous_data)
            data["new_calls"] = []

        try:
            balance_result = self.client.get_balance()

            status = balance_result.get("status")
            if status in [
                "invalid_credentials",
                "ip_not_enabled",
                "api_not_enabled",
                "missing_credentials",
            ]:
                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
            elif status == "success":
                data["balance"] = self._extract_balance(balance_result.get("balance"))
            else:
                raise UpdateFailed(f"Failed to fetch balance: {balance_result}")

        except (VoipMsApiError, ValueError) as ex:
            raise UpdateFailed(f"Failed to connect to VoIP.ms: {ex}") from ex

        try:
            registrations: dict[str, dict[str, Any]] = {}
            subs_result = self.client.get_sub_accounts()
            status = subs_result.get("status")
            if status in [
                "invalid_credentials",
                "ip_not_enabled",
                "api_not_enabled",
                "missing_credentials",
            ]:
                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
            elif status == "success":
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
                            status = reg_result.get("status")
                            if status in [
                                "invalid_credentials",
                                "ip_not_enabled",
                                "api_not_enabled",
                                "missing_credentials",
                            ]:
                                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
                            if status != "success":
                                raise UpdateFailed(
                                    f"Failed to fetch registration for {account_name}"
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
                            # Retain cached registration for this account on failure
                            old_regs = data.get("registrations", {})
                            if account_name in old_regs:
                                registrations[account_name] = old_regs[account_name]
                    data["registrations"] = registrations
            elif status == "no_subaccounts":
                pass
            else:
                raise UpdateFailed(f"Failed to fetch subaccounts: {subs_result}")
        except (VoipMsApiError, ValueError) as ex:
            _LOGGER.warning("Error fetching subaccounts: %s", ex)

        try:
            vm_result = self.client.get_voicemails()
            status = vm_result.get("status")
            if status in [
                "invalid_credentials",
                "ip_not_enabled",
                "api_not_enabled",
                "missing_credentials",
            ]:
                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
            elif status == "success":
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
                            status = msg_result.get("status")
                            if status in [
                                "invalid_credentials",
                                "ip_not_enabled",
                                "api_not_enabled",
                                "missing_credentials",
                            ]:
                                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
                            if status == "success":
                                messages = msg_result.get("messages", [])
                                if isinstance(messages, dict):
                                    messages = [messages]
                                if isinstance(messages, list):
                                    total_messages += len(messages)
                            else:
                                raise UpdateFailed(
                                    f"Failed to fetch messages for {mailbox_id}"
                                )
                        except (VoipMsApiError, ValueError) as ex:
                            raise UpdateFailed(
                                f"Error fetching messages for mailbox {mailbox_id}: {ex}"
                            ) from ex
                    data["voicemail_count"] = total_messages
            elif vm_result.get("status") == "no_voicemails":
                data["voicemail_count"] = 0
            else:
                raise UpdateFailed(f"Failed to fetch voicemails: {vm_result}")
        except (VoipMsApiError, ValueError) as ex:
            raise UpdateFailed(f"Error fetching voicemails: {ex}") from ex

        try:
            now_utc = dt_util.utcnow()
            date_from_dt = now_utc - timedelta(days=2)
            date_to_dt = now_utc + timedelta(days=1)

            date_from = date_from_dt.strftime("%Y-%m-%d")
            date_to = date_to_dt.strftime("%Y-%m-%d")

            cdr_result = self.client.get_cdr(
                date_from=date_from,
                date_to=date_to,
                timezone=0,
            )

            status = cdr_result.get("status")
            if status in [
                "invalid_credentials",
                "ip_not_enabled",
                "api_not_enabled",
                "missing_credentials",
            ]:
                raise ConfigEntryAuthFailed(f"Auth failed: {status}")
            elif status == "success":
                cdrs = cdr_result.get("cdr", [])
                if isinstance(cdrs, dict):
                    cdrs = [cdrs]

                inbound_count = 0
                outbound_count = 0
                new_calls: list[CallRecord] = []
                threshold_time = now_utc - timedelta(hours=24)

                seen_payload_signatures: dict[str, int] = {}

                for call in cdrs:
                    try:
                        raw_unique = str(call.get(CallRecord.FIELD_UNIQUE_ID, ""))
                        occurrence = 0
                        if not raw_unique.strip():
                            signature = f"{call.get(CallRecord.FIELD_DATE)}|{call.get(CallRecord.FIELD_CALLER_ID)}|{call.get(CallRecord.FIELD_DESTINATION)}|{call.get(CallRecord.FIELD_DESCRIPTION)}"
                            occurrence = seen_payload_signatures.get(signature, 0)
                            seen_payload_signatures[signature] = occurrence + 1

                        call_record = CallRecord.parse_cdr_record(
                            call, occurrence=occurrence
                        )
                        if call_record is None:
                            continue

                        call_date = datetime.strptime(
                            call_record.timestamp, "%Y-%m-%d %H:%M:%S"
                        ).replace(tzinfo=dt_util.UTC)
                        if call_date < threshold_time or call_date > now_utc:
                            continue

                        if call_record.direction == DIRECTION_INBOUND:
                            inbound_count += 1
                        elif call_record.direction == DIRECTION_OUTBOUND:
                            outbound_count += 1
                        else:
                            # Ignore unknown call directions for counts
                            pass

                        if call_record.unique_id in self._seen_call_ids:
                            continue
                        self._seen_call_ids[call_record.unique_id] = call_date

                        # Prune seen calls older than 72 hours
                        prune_threshold = now_utc - timedelta(hours=72)
                        stale_keys = [
                            k
                            for k, v in self._seen_call_ids.items()
                            if v < prune_threshold
                        ]
                        for k in stale_keys:
                            self._seen_call_ids.pop(k, None)

                        if self._calls_initialized and call_record.direction in (
                            DIRECTION_INBOUND,
                            DIRECTION_OUTBOUND,
                        ):
                            new_calls.append(call_record)
                    except ValueError as ex:
                        _LOGGER.warning("Failed to parse call record: %s", ex)

                if not self._calls_initialized:
                    self._calls_initialized = True

                data["inbound_calls_24h"] = inbound_count
                data["outbound_calls_24h"] = outbound_count
                data["new_calls"] = new_calls

            elif cdr_result.get("status") == "no_cdr":
                data["inbound_calls_24h"] = 0
                data["outbound_calls_24h"] = 0
            else:
                raise UpdateFailed(f"Failed to fetch CDRs: {cdr_result}")
        except (VoipMsApiError, ValueError) as ex:
            raise UpdateFailed(f"Error fetching CDR: {ex}") from ex

        return data

    @staticmethod
    def _extract_balance(balance: Any) -> Any:
        """Extract the current balance from simple or advanced balance responses."""
        if isinstance(balance, dict):
            return balance.get("current_balance")
        return balance
