<p align="center">
  <img src="https://voip.ms/resources/img/logo.svg" alt="VoIP.ms" width="260">
</p>

# VoIP.MS for Home Assistant

<p align="center">
  <a href="https://github.com/andrewtryder/ha-voipms/actions/workflows/ci.yml"><img src="https://github.com/andrewtryder/ha-voipms/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/andrewtryder/ha-voipms/releases"><img src="https://img.shields.io/github/v/release/andrewtryder/ha-voipms?label=release" alt="Latest release"></a>
  <a href="https://hacs.xyz/docs/faq/custom_repositories"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS custom repository"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2024.11.0%2B-41BDF5.svg" alt="Home Assistant 2024.11.0+">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/andrewtryder/ha-voipms" alt="License"></a>
</p>

Bring VoIP.ms account data, SMS, and call activity into Home Assistant.

This custom integration uses the VoIP.ms REST API to expose account sensors, SIP registration status, inbound SMS events, call events, and an SMS sending service.

## Features

- Account balance, inbound calls, outbound calls, voicemail count, last SMS, and last call sensors.
- SIP subaccount registration binary sensors.
- Incoming SMS webhook support with Home Assistant events, logbook entries, persistent notifications, and a last-SMS sensor.
- Call activity events, logbook entries, persistent notifications, and a last-call sensor.
- `voipms.send_sms` service for automations, scripts, and dashboards.
- Optional Lovelace SMS card.

## Requirements

- Home Assistant `2024.11.0` or newer.
- A VoIP.ms account with the REST/JSON API enabled.
- VoIP.ms API username and API password.
- A default DID for SMS and webhook registration.

## Installation

### HACS

1. Open **HACS** in Home Assistant.
2. Add this repository as a custom integration repository:

   ```text
   https://github.com/andrewtryder/ha-voipms
   ```

3. Install **VoIP.MS** from HACS.
4. Restart Home Assistant.

### Manual

Copy the integration into your Home Assistant `custom_components` directory:

```bash
cp -r custom_components/voipms /config/custom_components/
```

Restart Home Assistant after copying the files.

## Configuration

1. In Home Assistant, go to **Settings → Devices & services**.
2. Add **VoIP.MS**.
3. Enter your VoIP.ms API username, API password, and default DID.

The integration polls VoIP.ms every 5 minutes.

## Entities and events

### Sensors

| Entity | Description |
| --- | --- |
| Account Balance | Current VoIP.ms balance |
| Inbound Calls (24h) | Inbound call count from the last 24 hours |
| Outbound Calls (24h) | Outbound call count from the last 24 hours |
| Voicemails | Current voicemail message count |
| Last SMS | Most recent inbound SMS details |
| Last Call | Most recent tracked call details |

### Binary sensors

A connectivity binary sensor is created for each SIP subaccount returned by VoIP.ms. Each sensor shows whether the subaccount is currently registered.

### Events

| Event | When it fires |
| --- | --- |
| `voipms_inbound_sms` | A valid inbound SMS is received |
| `voipms_inbound_call` | A new inbound call record is detected |
| `voipms_outbound_call` | A new outbound call record is detected |

## Sending SMS

Use the `voipms.send_sms` service:

```yaml
service: voipms.send_sms
data:
  to: "5559876543"
  message: "Hello from Home Assistant"
  did: "5551234567" # optional; defaults to the configured DID
```

## Receiving SMS

When the integration loads, it attempts to register the VoIP.ms SMS callback URL automatically using your Home Assistant external URL.

A valid inbound SMS will:

- Fire a `voipms_inbound_sms` event.
- Add a Home Assistant logbook entry.
- Create a persistent notification.
- Update the Last SMS sensor.

If automatic registration fails, configure the callback manually in the VoIP.ms portal with this shape:

```text
https://YOUR_HOME_ASSISTANT_URL/api/webhook/WEBHOOK_ID?to={TO}&from={FROM}&message={MESSAGE}&id={ID}&date={TIMESTAMP}
```

Your Home Assistant external URL must be reachable from the internet, or available through Home Assistant Cloud.

## Optional Lovelace card

A compact Send SMS card is bundled at:

```text
frontend/dist/voipms-sms-card.js
```

Add it as a JavaScript module resource in Home Assistant:

```text
/local/voipms-sms-card.js
```

Example card configuration:

```yaml
type: custom:voipms-sms-card
title: Send SMS
did: "5551234567"
to: "5559876543"
```

## Troubleshooting

### Authentication fails

- Confirm the VoIP.ms API is enabled under **SOAP and REST/JSON API**.
- Use the API username and API password, not necessarily your VoIP.ms portal login.
- If IP restriction is enabled in VoIP.ms, allow your Home Assistant outbound public IP.
- Remove and re-add the integration after changing API credentials.

### Data is not updating

- Check **Settings → System → Logs** for `custom_components.voipms` messages.
- Verify Home Assistant can reach `https://voip.ms` over HTTPS.
- Confirm the integration is configured and not in a failed state.

### Inbound SMS is not received

- Update to the latest release and restart Home Assistant.
- Confirm **Settings → System → Network → External URL** is reachable externally.
- Reload the VoIP.MS integration so it can re-register the SMS webhook.
- Check the VoIP.ms DID SMS callback settings for `{TO}`, `{FROM}`, and `{MESSAGE}` placeholders.

Enable debug logging when needed:

```yaml
logger:
  default: warning
  logs:
    custom_components.voipms: debug
    homeassistant.components.webhook: debug
```

## Development

Install dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Run checks:

```bash
ruff format --check .
ruff check .
PYTHONPATH=. coverage run -m pytest
```

## Support

- [VoIP.ms API documentation](https://voip.ms/m/apidocs.php)
- [GitHub issues](https://github.com/andrewtryder/ha-voipms/issues)
- [Home Assistant community](https://community.home-assistant.io/)

## License

MIT License. See [LICENSE](LICENSE).
