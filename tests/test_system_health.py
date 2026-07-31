"""Tests for VoIP.ms system health reporting."""

from unittest.mock import MagicMock, patch

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VOIPMS_REST_API_URL
from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN
from custom_components.voipms.system_health import (
    async_get_system_health_info,
    async_register,
)

_REACH_PATH = (
    "custom_components.voipms.system_health.system_health.async_check_can_reach_url"
)

SECRET_VALUES = (
    "test_user",
    "test_password",
    "5551234567",
    "http://example.com",
    "voipms_",
)


def _assert_no_secrets(info: dict) -> None:
    """Assert system health info does not leak secrets or webhook details."""
    serialized = str(info)
    for secret in SECRET_VALUES:
        assert secret not in serialized


def _patch_reach(return_value: bool = True):
    """Patch reachability helper with a sync MagicMock (no AsyncMock coroutine)."""
    return patch(_REACH_PATH, new=MagicMock(return_value=return_value))


async def test_async_register_registers_info_callback() -> None:
    """Test async_register wires the info callback."""
    register = MagicMock()
    async_register(MagicMock(), register)
    register.async_register_info.assert_called_once_with(async_get_system_health_info)


async def test_system_health_no_entries(hass: HomeAssistant) -> None:
    """Test system health with no config entries."""
    with _patch_reach(True) as mock_reach:
        info = await async_get_system_health_info(hass)

    mock_reach.assert_called_once_with(hass, VOIPMS_REST_API_URL)
    assert info["config_entry_state"] == "missing"
    assert info["last_update_success"] is None
    assert info["webhook_management_enabled"] is False
    assert info["webhook_registration_status"] == "not_attempted"
    assert info["api_endpoint_reachable"] is True
    _assert_no_secrets(info)


async def test_system_health_unloaded_entry(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test system health with an unloaded config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    entry.add_to_hass(hass)

    with _patch_reach(True) as mock_reach:
        info = await async_get_system_health_info(hass)

    mock_reach.assert_called_once_with(hass, VOIPMS_REST_API_URL)
    assert info["config_entry_state"] == "not_loaded"
    assert info["last_update_success"] is None
    _assert_no_secrets(info)


async def test_system_health_coordinator_success(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test system health reports successful coordinator refresh."""
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

    with _patch_reach(True) as mock_reach:
        info = await async_get_system_health_info(hass)

    mock_reach.assert_called_once_with(hass, VOIPMS_REST_API_URL)
    assert info["config_entry_state"] == "loaded"
    assert info["last_update_success"] is True
    assert info["webhook_management_enabled"] is True
    assert info["webhook_registration_status"] == "registered"
    _assert_no_secrets(info)


async def test_system_health_coordinator_failure(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test system health reports coordinator failure state."""
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

    entry.runtime_data.coordinator.last_update_success = False

    with _patch_reach(False):
        info = await async_get_system_health_info(hass)

    assert info["last_update_success"] is False
    assert info["config_entry_state"] == "loaded"
    _assert_no_secrets(info)


async def test_system_health_webhook_disabled(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test system health reports webhook management disabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        options={"manage_webhook": False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with _patch_reach(True):
        info = await async_get_system_health_info(hass)

    assert info["webhook_management_enabled"] is False
    assert info["webhook_registration_status"] == "disabled"
    mock_voipms_client.set_sms.assert_not_called()
    _assert_no_secrets(info)


async def test_system_health_webhook_failed(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test system health reports failed webhook registration."""
    mock_voipms_client.set_sms.return_value = {"status": "invalid_did"}

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

    with _patch_reach(True):
        info = await async_get_system_health_info(hass)

    assert info["webhook_registration_status"] == "failed"
    assert entry.runtime_data.webhook_failure_category == "invalid_did"
    _assert_no_secrets(info)


async def test_system_health_reach_url_is_base_only(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test endpoint health check receives only the base API URL."""
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

    with _patch_reach(True) as mock_reach:
        await async_get_system_health_info(hass)

    mock_reach.assert_called_once_with(hass, "https://voip.ms/api/v1/rest.php")
    called_url = mock_reach.call_args.args[1]
    assert "?" not in called_url
    assert "api_username" not in called_url
    assert "api_password" not in called_url
