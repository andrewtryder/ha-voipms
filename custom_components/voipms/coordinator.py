"""Data update coordinator for VoIP.ms integration."""

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.util import dt as dt_util

from .api import VoipMsApiError, VoipMsRestClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VoipmsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching VoIP.ms data."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the data update coordinator."""
        self.config_entry = config_entry
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.client = VoipMsRestClient(self.username, self.password)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from VoIP.ms."""
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self) -> dict:
        """Fetch data from VoIP.ms REST API (blocking call)."""
        data = {
            "balance": None,
            "inbound_calls_24h": 0,
            "outbound_calls_24h": 0,
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
                threshold_time = now.replace(tzinfo=None) - timedelta(hours=24)

                for call in cdrs:
                    try:
                        call_date_str = call.get("date", "")
                        call_date = datetime.strptime(
                            call_date_str, "%Y-%m-%d %H:%M:%S"
                        )

                        if call_date >= threshold_time:
                            description = str(call.get("description", "")).lower()
                            if "incoming" in description or "inbound" in description:
                                inbound_count += 1
                            else:
                                outbound_count += 1
                    except (AttributeError, ValueError):
                        pass

                data["inbound_calls_24h"] = inbound_count
                data["outbound_calls_24h"] = outbound_count

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
