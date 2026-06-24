"""Test VoIP.ms inbound SMS webhook handling."""

from unittest.mock import patch

from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT
from homeassistant.components.webhook import async_handle_webhook
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_LOGBOOK_ENTRY
from homeassistant.core import HomeAssistant
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms_custom.const import (
    CONF_DEFAULT_DID,
    DOMAIN,
    EVENT_INBOUND_SMS,
    build_webhook_callback_url,
)


async def test_webhook_registers_with_get_method(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test webhook registration allows GET for VoIP.ms SMS delivery."""
    captured: dict = {}

    def capture_register(hass, domain, name, webhook_id, handler, **kwargs):
        captured["allowed_methods"] = kwargs.get("allowed_methods")
        from homeassistant.components.webhook import async_register as real_register

        real_register(hass, domain, name, webhook_id, handler, **kwargs)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.voipms_custom.async_register",
        side_effect=capture_register,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert captured["allowed_methods"] == (METH_GET, METH_POST, METH_PUT)


async def test_set_sms_receives_callback_url_template(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test VoIP.ms setSMS receives URL with query-parameter templates."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_voipms_client.set_sms.assert_called_once()
    call_kwargs = mock_voipms_client.set_sms.call_args.kwargs
    expected_url = build_webhook_callback_url(
        "http://example.com", f"voipms_{entry.entry_id}"
    )
    assert call_kwargs["url_callback"] == expected_url
    assert "to={TO}" in call_kwargs["url_callback"]
    assert "from={FROM}" in call_kwargs["url_callback"]
    assert "message={MESSAGE}" in call_kwargs["url_callback"]


async def test_inbound_sms_webhook_fires_event_on_get(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test GET webhook request fires voipms_inbound_sms with query data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    events: list = []

    def capture_event(event):
        events.append(event.data)

    hass.bus.async_listen(EVENT_INBOUND_SMS, capture_event)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&message=hello&id=42&date=2024-01-01",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert response.text == "ok"
    assert len(events) == 1
    assert events[0]["to"] == "5551234567"
    assert events[0]["from"] == "5559876543"
    assert events[0]["message"] == "hello"
    assert events[0]["id"] == "42"
    assert events[0]["date"] == "2024-01-01"


async def test_inbound_sms_webhook_writes_logbook_entry(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test GET webhook request writes an Activity/logbook entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    logbook_events: list = []

    def capture_logbook(event):
        logbook_events.append(event.data)

    hass.bus.async_listen(EVENT_LOGBOOK_ENTRY, capture_logbook)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&message=hello&id=42&date=2024-01-01",
    )
    await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert len(logbook_events) == 1
    assert logbook_events[0]["name"] == "VoIP.MS"
    assert logbook_events[0]["domain"] == DOMAIN
    assert "SMS from 5559876543 to 5551234567: hello" in logbook_events[0]["message"]
    assert logbook_events[0]["entity_id"] == "sensor.voip_ms_account_balance"
