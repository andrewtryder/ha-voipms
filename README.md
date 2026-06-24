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

### Common Issues

1. **API Authentication Failed**
   - Ensure your API credentials are correct
   - Check that your VoIP.ms account is active
   - Verify you have API access enabled

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