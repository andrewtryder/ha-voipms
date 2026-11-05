# SMS webhooks, actions, and Lovelace card

Return to the [README](../README.md) for installation and first-time setup.

## Sending SMS (`voipms.send_sms`)

Use the `voipms.send_sms` action in automations, scripts, or dashboards:

```yaml
action: voipms.send_sms
data:
  to: "5559876543"
  message: "Hello from Home Assistant"
  did: "5551234567" # optional; defaults to the configured Default DID
```

- `to` and `did` must be canonical 10-digit NANPA (`5559876543`) or E.164 (`+15559876543`) phone numbers.
- `message` must be 1 to 160 characters. Longer messages are rejected rather than split or converted to MMS.
- Sending SMS through VoIP.ms may incur per-message carrier or account charges on your VoIP.ms balance.

## Receiving SMS and webhook configuration

Inbound SMS requires an externally reachable Home Assistant URL (through **Settings → System → Network → External URL** or Home Assistant Cloud) so VoIP.ms can deliver webhook callbacks.

When **Manage SMS webhook automatically** (`manage_webhook`) is enabled (the default), the integration registers the callback URL on your configured Default DID during startup:

```text
https://YOUR_HOME_ASSISTANT_URL/api/webhook/voipms_<ENTRY_ID>?to={TO}&from={FROM}&id={ID}&date={TIMESTAMP}
```

When a callback arrives with `id={ID}`, the integration fetches and verifies the full SMS message content from the authenticated VoIP.ms REST API (`getSMS`) before firing events. Legacy manual callback URLs that include `&message={MESSAGE}` in the query string are also accepted.

A validated inbound SMS:

- Fires a `voipms_inbound_sms` event on the Home Assistant event bus.
- Writes a Home Assistant logbook entry.
- Creates a persistent notification.
- Updates the **Last SMS** sensor (`sensor.voipms_last_sms`).

If you prefer not to let Home Assistant update your DID callback setting automatically, turn off **Manage SMS webhook automatically** during setup or in **Configure**, and configure the callback URL manually in the VoIP.ms portal.

## Call events

When polling detects new call records, the integration updates the **Last Call** sensor and fires:

- `voipms_inbound_call` when a new inbound call record is detected.
- `voipms_outbound_call` when a new outbound call record is detected.

## Optional Lovelace SMS card

The integration bundles a compact custom Lovelace card (`custom:voipms-sms-card`) and serves it from `/voipms-frontend/voipms-sms-card.js` when loaded.

1. In Home Assistant, go to **Settings → Dashboards**, open the top-right menu, and select **Resources**.
2. Add `/voipms-frontend/voipms-sms-card.js` as a **JavaScript module**.
3. Add a manual card to your dashboard:

```yaml
type: custom:voipms-sms-card
title: Send SMS
did: "5551234567"
to: "5559876543"
```

## Debug logging

To inspect API polling or webhook handling in **Settings → System → Logs**, enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.voipms: debug
    homeassistant.components.webhook: debug
```
