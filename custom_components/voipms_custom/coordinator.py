"""Data update coordinator for VoIP.ms Custom integration."""

import logging
import os
from datetime import datetime, timedelta

import zeep
from zeep.exceptions import Fault
from requests.exceptions import RequestException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VoipmsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching VoIP.ms data."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the data update coordinator."""
        self.config_entry = config_entry
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]

        # Load WSDL
        wsdl_path = os.path.join(os.path.dirname(__file__), "server.wsdl")
        self.client = zeep.Client(wsdl=wsdl_path)

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
        """Fetch data from VoIP.ms API (blocking call)."""
        data = {
            "balance": None,
            "inbound_calls_24h": 0,
            "outbound_calls_24h": 0,
        }

        try:
            # Fetch balance
            balance_result = self.client.service.getBalance(
                api_username=self.username,
                api_password=self.password,
            )

            # The balance result structure can vary. Check if it's a dict and extract balance
            if isinstance(balance_result, dict):
                if balance_result.get("status") == "success":
                    data["balance"] = balance_result.get("balance")
                else:
                    _LOGGER.warning("Failed to fetch balance: %s", balance_result)
            else:
                # Some WSDLs return the decimal directly
                data["balance"] = float(balance_result)

        except (Fault, RequestException, ValueError) as ex:
            _LOGGER.error("Error fetching balance: %s", ex)
            raise UpdateFailed(f"Error fetching balance: {ex}") from ex

        try:
            # Fetch CDR for the last 24 hours
            # According to VoIP.ms API, getCDR takes date_from and date_to (YYYY-MM-DD)
            # and optionally time_from and time_to (HH:MM:SS) if supported by WSDL,
            # but date_from/date_to are standard.
            # We'll use the last 2 days of dates to ensure we cover the 24 hour period
            now = datetime.now()
            yesterday = now - timedelta(days=1)

            date_from = yesterday.strftime("%Y-%m-%d")
            date_to = now.strftime("%Y-%m-%d")

            cdr_result = self.client.service.getCDR(
                api_username=self.username,
                api_password=self.password,
                date_from=date_from,
                date_to=date_to,
            )

            # Process CDR array to count inbound and outbound
            if isinstance(cdr_result, dict) and cdr_result.get("status") == "success":
                # Assuming 'cdr' element contains the list of calls
                cdrs = cdr_result.get("cdr", [])
                # Handle single object vs list in zeep return
                if isinstance(cdrs, dict):
                    cdrs = [cdrs]

                inbound_count = 0
                outbound_count = 0

                # We need to filter based on actual 24h threshold
                threshold_time = now - timedelta(hours=24)

                for call in cdrs:
                    # Parse date: typically 'YYYY-MM-DD HH:MM:SS'
                    try:
                        call_date_str = call.get("date", "")
                        call_date = datetime.strptime(
                            call_date_str, "%Y-%m-%d %H:%M:%S"
                        )

                        if call_date >= threshold_time:
                            # Depending on VoIP.ms, 'account' or 'destination' might indicate direction.
                            # Usually, 'type' or 'description' or missing DID indicates direction, or comparing 'account' to DIDs.
                            # For standard getCDR, if 'destination' is one of our DIDs, it's inbound.
                            # If 'account' is our subaccount and destination is external, it's outbound.
                            # However, 'type' might exist. Let's look for 'description' containing 'Incoming' or 'destination' matching DID.
                            # Without full API knowledge, we'll try to infer.

                            # A common way in VoIP.ms CDR is checking 'description' for "Incoming" vs "Outbound"
                            # Or checking if callerid length is 10/11 vs destination length.
                            description = str(call.get("description", "")).lower()
                            if "incoming" in description or "inbound" in description:
                                inbound_count += 1
                            else:
                                # Default to outbound if not explicitly incoming
                                outbound_count += 1
                    except ValueError:
                        pass  # Skip invalid dates

                data["inbound_calls_24h"] = inbound_count
                data["outbound_calls_24h"] = outbound_count

            else:
                # It might return "no_cdr" or similar
                _LOGGER.debug("No CDRs found or failed: %s", cdr_result)

        except (Fault, RequestException, ValueError) as ex:
            # We might not want to fail the whole update if CDR fails
            _LOGGER.error("Error fetching CDR: %s", ex)

        return data
