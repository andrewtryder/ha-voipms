"""Test the VoIP.ms config flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.const import DOMAIN, CONF_DEFAULT_DID


async def test_form_success(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test we get the form and create an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    mock_voipms_client.get_balance.reset_mock()

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test_user"
    assert result2["data"] == {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_DEFAULT_DID: "5551234567",
    }

    mock_voipms_client.get_balance.assert_any_call()


async def test_form_invalid_auth(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test we handle invalid auth."""
    mock_voipms_client.get_balance.return_value = {"status": "invalid_credentials"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_credentials"}


async def test_form_ip_not_enabled(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test we map ip_not_enabled to a specific error."""
    mock_voipms_client.get_balance.return_value = {"status": "ip_not_enabled"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "ip_not_enabled"}


async def test_form_unknown_api_status(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test unknown API statuses fall back to invalid_auth."""
    mock_voipms_client.get_balance.return_value = {"status": "some_new_status"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant, mock_voipms_client) -> None:
    """Test we handle cannot connect error."""
    mock_voipms_client.get_balance.side_effect = VoipMsApiError("Connection error")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
