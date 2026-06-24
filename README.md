# VoIP.ms Custom

## Overview

VoIP.ms Custom is a Home Assistant integration that provides access to the VoIP.ms telephone service API. This integration allows you to manage your VoIP.ms phone service directly within Home Assistant.

## Installation

### Using HACS (Home Assistant Community Store)

1. Make sure the **HACS** integration is enabled in your Home Assistant instance.
2. Go to **HACS** → **Integrations** → **Repository Manager**.
3. Click on the **<>+** button in the top right corner.
4. Select "Custom Repository" and enter the following details:
   - **Repository URL**: `https://github.com/andrewtryder/ha-voipms`
   - **Category**: Integration
5. Click "Submit" and wait for the integration to be installed.

### Manual Installation

Add the integration directory to your Home Assistant configuration:
```bash
cp -r custom_components/voipms_custom /config/custom_components/
```

Restart Home Assistant after installation.

## Configuration

After adding the integration, navigate to **Configuration** → **Integrations** → **VoIP.ms Custom** and click on "Configure".

You'll need to provide the following configuration parameters:

- **API Username**: Your VoIP.ms API username
- **API Password**: Your VoIP.ms API password

The integration will automatically populate various sensors related to your VoIP.ms account including:

- Current balance
- Call history
- Number usage
- Service status

## Usage

Once configured, the integration will automatically update sensors with data from your VoIP.ms account. You can use these sensors in your automations and dashboards:

```yaml
automation:
  - alias: Check VoIP Balance
    trigger:
      - platform: numeric_state
        entity_id: sensor.voipms_balance
        below: 5
    action:
      - service: notify.notify
        data:
          message: "Your VoIP.ms balance is running low: {{ states('sensor.voipms_balance') }}"
```

## Sensors

The integration provides the following sensors:

- **VoIP.ms Balance**: Current account balance
- **VoIP.ms Calls Today**: Number of calls made today
- **VoIP.ms Usage Today**: Data usage today
- **VoIP.ms Status**: Current service status
- **VoIP.ms Last Updated**: Last time data was updated

## Troubleshooting

### Setup authentication errors

If setup fails with **Invalid authentication**, **Failed to connect**, or a more specific message, work through these steps in order.

#### 1. Enable debug logging

Add this to `configuration.yaml`, or use **Settings → System → Logs → Configure loggers**:

```yaml
logger:
  default: warning
  logs:
    custom_components.voipms_custom: debug
```

Restart Home Assistant, retry adding the integration, then check **Settings → System → Logs** (or `home-assistant.log`):

| Log message | Meaning |
|---|---|
| `Connection error:` | Network, HTTP, or JSON parse failure — not a bad password |
| `VoIP.ms auth failed:` | API reachable; the logged JSON shows the VoIP.ms `status` value |
| `Unexpected exception` | Check the stack trace for an integration or environment issue |

#### 2. Confirm VoIP.ms API credentials

Use **API credentials**, not necessarily your web portal login:

1. Log in at [voip.ms](https://voip.ms)
2. Go to **Main Menu → SOAP and REST/JSON API**
3. Confirm the **API is enabled**
4. Copy the **API Username** and **API Password** shown there
5. If **IP restriction** is enabled, add your Home Assistant instance's **outbound public IP**

The **Default DID** field does not affect authentication during setup.

#### 3. Test the API outside Home Assistant

Run this from a machine on the same outbound network as Home Assistant (ideally the HA host via SSH or the Terminal add-on):

```bash
curl -sS -G "https://voip.ms/api/v1/rest.php" \
  --data-urlencode "api_username=YOUR_API_USERNAME" \
  --data-urlencode "api_password=YOUR_API_PASSWORD" \
  --data-urlencode "method=getBalance" \
  --data-urlencode "content_type=json"
```

| Response `status` | Next step |
|---|---|
| `success` | Credentials work — delete any existing VoIP.ms config entry, restart HA, and re-add the integration |
| `invalid_credentials` | Reset the API password in the VoIP.ms portal and retry |
| `ip_not_enabled` | Allowlist your HA public IP in VoIP.ms API settings |
| `api_not_enabled` | Enable the API in the VoIP.ms portal |
| Timeout or non-JSON body | Fix outbound HTTPS/DNS from the HA host; check proxies and firewalls |

#### 4. Remove stale config entries

The integration allows only one entry per API username. If credentials changed or a prior attempt left a broken entry:

1. **Settings → Devices & Services → VoIP.ms Custom** — delete the entry
2. Restart Home Assistant
3. Re-add the integration with current credentials

There is no reconfigure flow yet; credential changes require removing and re-adding the integration.

#### 5. Credential hygiene

- Paste credentials directly from the VoIP.ms portal — avoid trailing spaces
- Passwords with `&`, `+`, or `%` are URL-encoded automatically; re-type if copied from a mobile device with smart quotes
- After changing the API password in VoIP.ms, remove and re-add the integration

### Common Issues

1. **API Authentication Failed**
   - Follow the [setup authentication errors](#setup-authentication-errors) steps above
   - Ensure your VoIP.ms account is active

2. **Data Not Updating**
   - Check if the sensors are in the "unknown" state
   - Verify network connectivity
   - Ensure the integration is configured correctly

3. **Missing Sensors**
   - Restart Home Assistant after installation
   - Check that the integration shows as "configured"
   - Verify the integration is not in a "failed" state

### Getting Help

- **Documentation**: https://voip.ms/m/apidocs.php
- **Issue Tracker**: https://github.com/andrewtryder/ha-voipms/issues
- **Community**: Join the Home Assistant community forums

## Development

### Prerequisites

- Home Assistant Core
- Python 3.12+

### Installation

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Testing

Run the test suite to ensure everything is working correctly:

```bash
coverage run -m pytest
```

### Code Style

This project uses `ruff` for linting and formatting. Run these commands before committing:

```bash
ruff check .
ruff format --check .
```

## Support

This integration is maintained by [andrewtryder](https://github.com/andrewtryder). Please report any issues or feature requests on the issue tracker.

## License

This project is licensed under the MIT License.