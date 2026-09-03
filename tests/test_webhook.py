"""Test VoIP.ms inbound SMS webhook handling."""

from unittest.mock import patch

import pytest
from aiohttp.hdrs import METH_GET, METH_POST
from homeassistant.components.persistent_notification import (
    _async_get_or_create_notifications,
)
from homeassistant.components.webhook import async_handle_webhook
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_LOGBOOK_ENTRY
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.aiohttp import MockRequest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import (
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
        "custom_components.voipms.async_register",
        side_effect=capture_register,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert captured["allowed_methods"] == (METH_GET, METH_POST)


async def test_set_sms_receives_callback_url_template(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test VoIP.ms setSMS receives URL with metadata query parameters only."""
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
    assert "id={ID}" in call_kwargs["url_callback"]
    assert "date={TIMESTAMP}" in call_kwargs["url_callback"]
    assert "{MESSAGE}" not in call_kwargs["url_callback"]
    assert "message=" not in call_kwargs["url_callback"]


async def test_inbound_sms_webhook_fires_event_on_get(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test GET webhook request without message calls getSMS and fires voipms_inbound_sms."""
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
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert response.text == "ok"
    mock_voipms_client.get_sms.assert_called_once_with(sms="42")
    assert len(events) == 1
    assert events[0]["to"] == "5551234567"
    assert events[0]["from"] == "5559876543"
    assert events[0]["message"] == "hello"
    assert events[0]["date"] == "2024-01-01 12:00:00"
    assert events[0]["account"] == "test_user"
    assert events[0]["config_entry_id"] == entry.entry_id


async def test_inbound_sms_webhook_authoritative_provider_metadata(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test authenticated getSMS metadata overrides forged callback query parameters."""
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": [
            {
                "id": "42",
                "did": "5551234567",
                "contact": "5559876543",
                "date": "2026-09-03 14:57:28",
                "message": "hello",
                "type": "1",
            }
        ],
    }

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    # Callback claims forged from, to, and date
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=2222222222&from=1111111111&id=42&date=1999-01-01%2000:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    mock_voipms_client.get_sms.assert_called_once_with(sms="42")
    assert len(events) == 1
    # Event uses provider data, not callback data
    assert events[0]["to"] == "5551234567"
    assert events[0]["from"] == "5559876543"
    assert events[0]["date"] == "2026-09-03 14:57:28"
    assert events[0]["message"] == "hello"


async def test_inbound_sms_webhook_multiline_and_unicode_message(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test inbound SMS with multiline CR/LF and Unicode content is preserved."""
    multiline_text = "first line\r\n\r\nsecond line \U0001f600"
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": [
            {
                "id": "100",
                "date": "2024-01-01 12:00:00",
                "type": "1",
                "did": "5551234567",
                "contact": "5559876543",
                "message": multiline_text,
            }
        ],
    }

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=100&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    mock_voipms_client.get_sms.assert_called_once_with(sms="100")
    assert len(events) == 1
    assert events[0]["message"] == multiline_text


async def test_legacy_inbound_sms_webhook_with_message_skips_get_sms(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test legacy webhook containing valid message is processed without calling getSMS."""
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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&message=legacy_hello&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    mock_voipms_client.get_sms.assert_not_called()
    assert len(events) == 1
    assert events[0]["message"] == "legacy_hello"


async def test_legacy_inbound_sms_webhook_validation_failure_returns_200(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test legacy webhook with invalid payload returns 200 OK without calling getSMS."""
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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    # Invalid date format in legacy callback
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&message=legacy_hello&id=42&date=invalid-date",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    mock_voipms_client.get_sms.assert_not_called()
    assert len(events) == 0


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
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert len(logbook_events) == 1
    assert logbook_events[0]["name"] == "VoIP.MS"
    assert logbook_events[0]["domain"] == DOMAIN
    assert "SMS from ******6543 to ******4567: hello" in logbook_events[0]["message"]
    assert logbook_events[0]["entity_id"] == "sensor.voip_ms_account_balance"


async def test_inbound_sms_webhook_creates_persistent_notification(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test GET webhook request creates a persistent notification."""
    assert await async_setup_component(hass, "persistent_notification", {})

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

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    notifications = _async_get_or_create_notifications(hass)
    expected_id = f"voipms_{entry.entry_id}_sms_42"
    assert expected_id in notifications
    assert notifications[expected_id]["message"] == "hello"
    assert notifications[expected_id]["title"] == "SMS from ******6543"


async def test_inbound_sms_webhook_deduplication(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test GET webhook request ignores duplicate messages without repeat API calls."""
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
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert len(events) == 1
    assert mock_voipms_client.get_sms.call_count == 1

    # Second request with the same ID should be ignored (200 OK, no extra event, no extra API call)
    response2 = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response2.status == 200
    assert len(events) == 1
    assert mock_voipms_client.get_sms.call_count == 1


async def test_inbound_sms_webhook_api_failure_returns_503(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test transient API lookup failure returns 503 and allows subsequent retry."""
    mock_voipms_client.get_sms.side_effect = VoipMsApiError("Network timeout")

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 503
    assert len(events) == 0
    # Failed attempt must not be cached as processed
    assert "42" not in entry.runtime_data.processed_sms_ids

    # Simulate subsequent retry where API call succeeds
    mock_voipms_client.get_sms.side_effect = None
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": [
            {
                "id": "42",
                "date": "2024-01-01 12:00:00",
                "type": "1",
                "did": "5551234567",
                "contact": "5559876543",
                "message": "hello",
            }
        ],
    }

    retry_response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert retry_response.status == 200
    assert len(events) == 1
    assert "42" in entry.runtime_data.processed_sms_ids


@pytest.mark.parametrize(
    ("desc", "result_payload"),
    [
        ("api_limit_exceeded", {"status": "api_limit_exceeded"}),
        ("method_maintenance", {"status": "method_maintenance"}),
        ("no_sms", {"status": "no_sms"}),
        ("empty_sms_list", {"status": "success", "sms": []}),
        (
            "mismatched_id",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "999",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "missing_message",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "empty_message",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "whitespace_message",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "   \r\n  ",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "missing_did",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "empty_did",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "missing_contact",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "empty_contact",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "   ",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "missing_date",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "invalid_date_format",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "invalid-timestamp",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "invalid_did_type",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": 5551234567,
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": "hello",
                        "type": "1",
                    }
                ],
            },
        ),
        (
            "invalid_message_type",
            {
                "status": "success",
                "sms": [
                    {
                        "id": "42",
                        "did": "5551234567",
                        "contact": "5559876543",
                        "date": "2024-01-01 12:00:00",
                        "message": 12345,
                        "type": "1",
                    }
                ],
            },
        ),
    ],
)
async def test_inbound_sms_webhook_retryable_hydration_failures(
    hass: HomeAssistant, mock_voipms_client, desc: str, result_payload: dict
) -> None:
    """Test transient or unresolved hydration failures return 503 Service Unavailable."""
    mock_voipms_client.get_sms.return_value = result_payload

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 503, f"Failed for case: {desc}"
    assert len(events) == 0
    assert "42" not in entry.runtime_data.processed_sms_ids


async def test_inbound_sms_webhook_non_inbound_type_returns_200(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test matching record with non-inbound type is safely rejected with 200 OK."""
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": [
            {
                "id": "42",
                "did": "5551234567",
                "contact": "5559876543",
                "date": "2024-01-01 12:00:00",
                "message": "outbound sms",
                "type": "2",  # Outbound message
            }
        ],
    }

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert len(events) == 0


async def test_inbound_sms_webhook_configured_did_mismatch_returns_200(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test matching record with mismatched DID is rejected with 200 OK."""
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": [
            {
                "id": "42",
                "did": "5559999999",  # Different DID
                "contact": "5559876543",
                "date": "2024-01-01 12:00:00",
                "message": "hello",
                "type": "1",
            }
        ],
    }

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert len(events) == 0


@pytest.mark.parametrize(
    "query",
    [
        "from=5559876543&id=42&date=2024-01-01%2012:00:00",  # missing to
        "to=5551234567&id=42&date=2024-01-01%2012:00:00",  # missing from
        "to=5551234567&from=5559876543&date=2024-01-01%2012:00:00",  # missing id
        "to=5551234567&from=5559876543&id=42",  # missing date
        "to=&from=5559876543&id=42&date=2024-01-01%2012:00:00",  # empty to
    ],
)
async def test_inbound_sms_webhook_missing_required_metadata_returns_200(
    hass: HomeAssistant, mock_voipms_client, query: str
) -> None:
    """Test callback with missing or empty metadata fields returns 200 OK without calling getSMS."""
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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string=query,
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    mock_voipms_client.get_sms.assert_not_called()
    assert len(events) == 0


async def test_inbound_sms_webhook_dict_sms_collection_succeeds(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test getSMS response where sms is formatted as a dict of records."""
    mock_voipms_client.get_sms.return_value = {
        "status": "success",
        "sms": {
            "0": {
                "id": "42",
                "did": "5551234567",
                "contact": "5559876543",
                "date": "2024-01-01 12:00:00",
                "message": "dict message",
                "type": "1",
            }
        },
    }

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
    hass.bus.async_listen(EVENT_INBOUND_SMS, lambda e: events.append(e.data))

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    webhook_id = f"voipms_{entry.entry_id}"
    request = MockRequest(
        content=b"",
        mock_source="test",
        headers={},
        method="GET",
        query_string="to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00",
    )
    response = await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()

    assert response.status == 200
    assert len(events) == 1
    assert events[0]["message"] == "dict message"


async def test_security_filter_blocks_crlf_query_and_allows_metadata_callback(
    hass: HomeAssistant, hass_client_no_auth, mock_voipms_client
) -> None:
    """Regression test: security filter rejects query with CRLF but accepts metadata-only callback."""
    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "webhook", {})

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

    client = await hass_client_no_auth()
    webhook_id = f"voipms_{entry.entry_id}"

    # Query with %0D%0A (CR/LF in message) is rejected by security filter with 400 Bad Request
    crlf_url = f"/api/webhook/{webhook_id}?to=5551234567&from=5559876543&message=hello%0D%0Aworld&id=42&date=2024-01-01%2012:00:00"
    resp_bad = await client.get(crlf_url)
    assert resp_bad.status == 400

    # New metadata-only query succeeds with 200 OK
    clean_url = f"/api/webhook/{webhook_id}?to=5551234567&from=5559876543&id=42&date=2024-01-01%2012:00:00"
    resp_good = await client.get(clean_url)
    assert resp_good.status == 200
    assert await resp_good.text() == "ok"
