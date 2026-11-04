"""Test the VoIP.ms config flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.api import VoipMsApiError
from custom_components.voipms.config_flow import OptionsFlowHandler
from custom_components.voipms.const import CONF_DEFAULT_DID, DOMAIN


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


async def test_form_invalid_default_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test invalid default DID returns a field-level error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    bad_did = "555-123-4567"
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: bad_did,
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {CONF_DEFAULT_DID: "invalid_did"}
    mock_voipms_client.get_balance.assert_not_called()
    assert bad_did not in str(result2)


async def test_form_valid_e164_default_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test valid E.164 default DID is accepted."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "+15551234567",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_DEFAULT_DID] == "+15551234567"


async def test_options_flow_updates_manage_webhook(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test options flow updates manage_webhook via OptionsFlowWithReload."""
    assert issubclass(OptionsFlowHandler, config_entries.OptionsFlowWithReload)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        options={"manage_webhook": True},
        unique_id="test_user",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"manage_webhook": False},
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["manage_webhook"] is False


async def test_reconfigure_flow_success(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test successful reconfiguration flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "old_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        options={"manage_webhook": True},
        unique_id="test_user",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "new_password",
            CONF_DEFAULT_DID: "5559876543",
            "manage_webhook": False,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "new_password"
    assert entry.data[CONF_DEFAULT_DID] == "5559876543"
    assert entry.options["manage_webhook"] is False


async def test_reconfigure_flow_invalid_did(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test reconfiguration flow with invalid DID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "old_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        unique_id="test_user",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "new_password",
            CONF_DEFAULT_DID: "555-bad-did",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {CONF_DEFAULT_DID: "invalid_did"}


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test reconfiguration flow handles connection errors."""
    mock_voipms_client.get_balance.side_effect = VoipMsApiError("Connection error")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "old_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        unique_id="test_user",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "new_password",
            CONF_DEFAULT_DID: "5559876543",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow_invalid_auth(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test reconfiguration flow handles authentication errors."""
    mock_voipms_client.get_balance.side_effect = None
    mock_voipms_client.get_balance.return_value = {"status": "invalid_credentials"}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "old_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        unique_id="test_user",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "new_password",
            CONF_DEFAULT_DID: "5559876543",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_credentials"}


async def test_reconfigure_flow_unexpected_exception(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test reconfiguration flow handles unexpected exceptions."""
    mock_voipms_client.get_balance.side_effect = RuntimeError("Crash")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_user",
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "old_password",
            CONF_DEFAULT_DID: "5551234567",
        },
        unique_id="test_user",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "new_password",
            CONF_DEFAULT_DID: "5559876543",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
