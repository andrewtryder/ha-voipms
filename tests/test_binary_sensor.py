"""Test VoIP.ms binary sensors for SIP registration."""

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.voipms.const import DOMAIN, CONF_DEFAULT_DID


async def test_registration_binary_sensors(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test registration binary sensors are created for subaccounts."""
    mock_voipms_client.get_sub_accounts.return_value = {
        "status": "success",
        "subaccounts": [
            {
                "account": "100001_ata",
                "description": "Home ATA",
                "device_type": "ata",
                "callerid_number": "5551234567",
                "protocol": "sip",
            },
            {
                "account": "100001_softphone",
                "description": "Mobile Softphone",
                "device_type": "softphone",
                "callerid_number": "5551234567",
                "protocol": "sip",
            },
        ],
    }

    def reg_side_effect(*, account):
        if "ata" in account:
            return {"status": "success", "registered": "yes"}
        return {"status": "success", "registered": "no"}

    mock_voipms_client.get_registration_status.side_effect = reg_side_effect

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

    ata_state = hass.states.get("binary_sensor.voip_ms_sip_100001_ata")
    assert ata_state is not None
    assert ata_state.state == "on"
    assert ata_state.attributes.get("description") == "Home ATA"
    assert ata_state.attributes.get("device_type") == "ata"
    assert ata_state.attributes.get("callerid_number") == "5551234567"
    assert ata_state.attributes.get("protocol") == "sip"

    softphone_state = hass.states.get("binary_sensor.voip_ms_sip_100001_softphone")
    assert softphone_state is not None
    assert softphone_state.state == "off"
    assert softphone_state.attributes.get("description") == "Mobile Softphone"
    assert softphone_state.attributes.get("device_type") == "softphone"


async def test_no_subaccounts_creates_no_binary_sensors(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that no binary sensors are created when there are no subaccounts."""
    mock_voipms_client.get_sub_accounts.return_value = {
        "status": "success",
        "subaccounts": [],
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

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = hass.states.async_all("binary_sensor")
    registration_states = [
        s for s in states if s.entity_id.startswith("binary_sensor.voip_ms_sip")
    ]
    assert len(registration_states) == 0


async def test_registration_status_updates_on_poll(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test binary sensor state updates when registration status changes."""
    mock_voipms_client.get_sub_accounts.return_value = {
        "status": "success",
        "subaccounts": [
            {
                "account": "100001_ata",
                "description": "Home ATA",
                "device_type": "ata",
                "callerid_number": "5551234567",
                "protocol": "sip",
            },
        ],
    }
    mock_voipms_client.get_registration_status.return_value = {
        "status": "success",
        "registered": "yes",
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

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ata_state = hass.states.get("binary_sensor.voip_ms_sip_100001_ata")
    assert ata_state is not None
    assert ata_state.state == "on"

    mock_voipms_client.get_registration_status.return_value = {
        "status": "success",
        "registered": "no",
    }

    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ata_state = hass.states.get("binary_sensor.voip_ms_sip_100001_ata")
    assert ata_state is not None
    assert ata_state.state == "off"


async def test_registration_binary_sensor_attributes_present(
    hass: HomeAssistant, mock_voipms_client
) -> None:
    """Test that extra state attributes are populated on the binary sensor."""
    mock_voipms_client.get_sub_accounts.return_value = {
        "status": "success",
        "subaccounts": [
            {
                "account": "100001_ata",
                "description": "Home ATA",
                "device_type": "ata",
                "callerid_number": "5551234567",
                "protocol": "sip",
            },
        ],
    }
    mock_voipms_client.get_registration_status.return_value = {
        "status": "success",
        "registered": "yes",
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

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ata_state = hass.states.get("binary_sensor.voip_ms_sip_100001_ata")
    assert ata_state is not None
    assert ata_state.state == "on"
    assert ata_state.attributes.get("description") == "Home ATA"
    assert ata_state.attributes.get("device_type") == "ata"
    assert ata_state.attributes.get("callerid_number") == "5551234567"
    assert ata_state.attributes.get("protocol") == "sip"
