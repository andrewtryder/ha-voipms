# VoIP.MS

## Overview

VoIP.MS is a Home Assistant integration that provides access to the VoIP.ms telephone service API. This integration allows you to manage your VoIP.ms phone service directly within Home Assistant.

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

After adding the integration, navigate to **Settings** → **Devices & Services** → **VoIP.MS** and click on "Configure".

You'll need to provide the following configuration parameters:

- **API Username**: Your VoIP.ms API username
- **API Password**: Your VoIP.ms API password
- **Default DID**: The phone number used for SMS and webhook registration

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
        entity_id: sensor.voip_ms_account_balance
        below: 5
    action:
      - service: notify.notify
        data:
          message: "Your VoIP.ms balance is running low: {{ states('sensor.voip_ms_account_balance') }}"
```

Inbound SMS messages fire a `voipms_inbound_sms` event on the Home Assistant event bus and appear in **Activity** (logbook). Listen for that event in **Developer Tools → Events** or use it as an automation trigger.

## Sensors

The integration provides the following sensors:

- **Account Balance**: Current account balance
- **Inbound Calls (24h)**: Inbound calls in the last 24 hours
- **Outbound Calls (24h)**: Outbound calls in the last 24 hours

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
| `success` | Credentials work — delete any existing VoIP.MS config entry, restart HA, and re-add the integration |
| `invalid_credentials` | Reset the API password in the VoIP.ms portal and retry |
| `ip_not_enabled` | Allowlist your HA public IP in VoIP.ms API settings |
| `api_not_enabled` | Enable the API in the VoIP.ms portal |
| Timeout or non-JSON body | Fix outbound HTTPS/DNS from the HA host; check proxies and firewalls |

#### 4. Remove stale config entries

The integration allows only one entry per API username. If credentials changed or a prior attempt left a broken entry:

1. **Settings → Devices & Services → VoIP.MS** — delete the entry
2. Restart Home Assistant
3. Re-add the integration with current credentials

There is no reconfigure flow yet; credential changes require removing and re-adding the integration.

#### 5. Credential hygiene

- Paste credentials directly from the VoIP.ms portal — avoid trailing spaces
- Passwords with `&`, `+`, or `%` are URL-encoded automatically; re-type if copied from a mobile device with smart quotes
- After changing the API password in VoIP.ms, remove and re-add the integration

### Inbound SMS not received

If you send a text to your VoIP.ms number but nothing appears in Home Assistant, work through these steps in order.

#### 1. Confirm you are on a current version

Check the integration version shown in **Settings → Devices & Services → VoIP.MS**. It should match the latest [GitHub release](https://github.com/andrewtryder/ha-voipms/releases) (v1.3.1 or newer). If it still shows an old version such as `1.0.0`, update via HACS and restart Home Assistant.

#### 2. Update and reload the integration

Updating files alone is not enough — the SMS webhook is re-registered only when the integration loads:

1. **HACS** → **VoIP.MS** → Download/Update (or select the latest release)
2. Restart Home Assistant
3. **Settings → Devices & Services → VoIP.MS** → **Reload**

#### 3. Check startup logs for webhook registration

After reload, search logs for `Registered VoIP.ms webhook`. A successful registration looks like:

```
Registered VoIP.ms webhook https://your-ha-url/api/webhook/voipms_...?to={TO}&from={FROM}&message={MESSAGE}&id={ID}&date={TIMESTAMP}: {'status': 'success'}
```

If you see `Failed to register webhook with VoIP.ms`, check API credentials, the Default DID, and that your HA outbound IP is allowlisted in the VoIP.ms portal.

#### 4. Enable debug logging for webhooks

Inbound SMS delivery logs at `INFO` level and may be hidden by default filters. Add this to `configuration.yaml`, or use **Settings → System → Logs → Configure loggers**:

```yaml
logger:
  default: warning
  logs:
    custom_components.voipms_custom: debug
    homeassistant.components.webhook: debug
```

Restart Home Assistant, send a test SMS, then check logs for:

| Log message | Meaning |
|---|---|
| `Received VoIP.ms SMS from ...` | Webhook delivered successfully; check **Activity** and **Developer Tools → Events** for `voipms_inbound_sms` |
| `Webhook ... only supports ... methods but GET was received` | Old integration version — update to v1.3.1+ and reload |
| `Received remote request for local webhook` | External URL not reachable; fix network or Nabu Casa setup |
| No `voipms_custom` or `webhook` entries | VoIP.ms may not be reaching your HA instance |

#### 5. Verify external URL reachability

VoIP.ms delivers SMS via HTTP GET to your Home Assistant **external** URL. Local requests from `127.0.0.1` (for example, opening the webhook URL in a browser on the HA host) are not VoIP.ms delivery.

1. Set **Settings → System → Network → External URL** to an address reachable from the internet, or use **Nabu Casa**
2. Confirm the URL is accessible from outside your LAN (not just locally)
3. In the VoIP.ms portal (**DID Numbers → Manage DID → SMS/MMS**), confirm the URL callback includes `{TO}`, `{FROM}`, and `{MESSAGE}` query templates

The integration registers this URL automatically via the API when you reload. You can also verify it matches the URL shown in the `Registered VoIP.ms webhook` log line.

#### 6. Listen for the inbound SMS event

In **Developer Tools → Events**, start listening for `voipms_inbound_sms`, then send a test SMS. A successful delivery fires an event with `to`, `from`, `message`, `id`, and `date` fields and adds an entry to **Activity**.

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
