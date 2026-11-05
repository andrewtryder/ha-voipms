# VoIP.MS for Home Assistant

<img src="custom_components/voipms/brand/logo.png" alt="VoIP.MS integration logo" width="180">

Monitor your VoIP.ms account balance, SIP subaccount registration, call activity, and SMS messages in Home Assistant, with optional outbound SMS sending.

[![Latest release](https://img.shields.io/github/v/release/andrewtryder/ha-voipms?style=flat-square)](https://github.com/andrewtryder/ha-voipms/releases/latest)
[![CI on main](https://img.shields.io/github/actions/workflow/status/andrewtryder/ha-voipms/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/andrewtryder/ha-voipms/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/andrewtryder/ha-voipms?style=flat-square)](LICENSE)
[![HACS custom integration](https://img.shields.io/badge/HACS-Custom-orange?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrewtryder&repository=ha-voipms&category=integration)

## What is this integration?

This unofficial custom integration connects Home Assistant to the VoIP.ms REST API. It polls account and call activity every 5 minutes and can receive inbound SMS messages through a Home Assistant webhook.

## What can I do with it?

- **Works with basic setup:** view account balance, 24-hour inbound and outbound call counts, voicemail count, last call details, and a connectivity binary sensor for each SIP subaccount.
- **Send SMS messages:** use the `voipms.send_sms` action in automations, scripts, or dashboards to send 1–160 character text messages from your DID.
- **Receive incoming SMS (requires external URL):** trigger `voipms_inbound_sms` events, logbook entries, persistent notifications, and updates to the **Last SMS** sensor when your Home Assistant external URL is reachable by VoIP.ms.
- **Optional Lovelace card (requires dashboard resource):** add the bundled `custom:voipms-sms-card` resource to send SMS messages from a dashboard card. See [SMS webhooks, actions, and Lovelace card](docs/sms-and-lovelace.md).

## Requirements and compatibility

- Home Assistant **2026.3.0 or newer** and HACS.
- A VoIP.ms account with the **SOAP and REST/JSON API** enabled in the VoIP.ms portal.
- Your VoIP.ms API username, API password, and outbound Home Assistant IP address allowed in the VoIP.ms API settings.
- An SMS-capable default DID (10-digit NANPA or E.164 format) on your VoIP.ms account.
- For inbound SMS webhooks: an externally reachable Home Assistant URL or Home Assistant Cloud.

## Install with HACS

1. In HACS, add `https://github.com/andrewtryder/ha-voipms` as a custom repository in the **Integration** category, or use the HACS badge above.
2. Find and install **VoIP.MS**.
3. Restart Home Assistant.

For manual installation, copy `custom_components/voipms` from a release into your Home Assistant configuration's `custom_components` directory and restart Home Assistant.

## First-time setup

1. Go to **Settings → Devices & services → Add integration** and select **VoIP.MS**.
2. Enter your VoIP.ms API username, API password, and default DID.
3. Keep **Manage SMS webhook automatically** enabled if you want Home Assistant to register its external webhook URL on your default DID, or turn it off to manage DID callback settings yourself.

You can update your API password, default DID, or automatic webhook setting later from the integration's **Reconfigure** or **Configure** menu.

## What you'll see in Home Assistant

| Entity or event | Description |
| --- | --- |
| Account Balance | Current VoIP.ms account balance |
| Inbound Calls (24h) / Outbound Calls (24h) | Call counts over the last 24 hours |
| Voicemails | Current voicemail message count |
| Last SMS / Last Call | Most recent inbound SMS and tracked call details |
| SIP Subaccount binary sensors | Registration connectivity status for each SIP subaccount |
| `voipms_inbound_sms`, `voipms_inbound_call`, `voipms_outbound_call` | Events fired when an inbound SMS arrives or new call records are detected |

## Common problems and troubleshooting

- **Authentication fails:** confirm the REST/JSON API is enabled in the VoIP.ms portal, use your API password (which can differ from your portal login password), and allow your Home Assistant outbound public IP address in VoIP.ms API IP restrictions.
- **Inbound SMS is not received:** confirm **Settings → System → Network → External URL** is reachable from the internet, then reload the integration or check the DID SMS URL callback in the VoIP.ms portal. See [SMS webhooks, actions, and Lovelace card](docs/sms-and-lovelace.md).
- **SMS send fails:** verify `to` and `did` use 10-digit NANPA (`5559876543`) or E.164 (`+15559876543`) format and the message is 1–160 characters.
- **Data is not updating:** check **Settings → System → Logs** for `custom_components.voipms` messages and confirm Home Assistant can reach `https://voip.ms` over HTTPS.

## Limitations, safety, and privacy

- **SMS billing and external delivery:** calling `voipms.send_sms` sends a real text message through VoIP.ms and can incur per-message usage charges on your account. Avoid unconstrained automation loops that could send repeated messages.
- **Webhook changes:** when automatic webhook management is enabled, loading the integration updates the SMS callback URL on your configured default DID in VoIP.ms.
- **Account security and privacy:** API credentials are stored in the Home Assistant configuration entry. Phone numbers, call metadata, and SMS content handled by the integration can appear in Home Assistant states, events, logbook entries, notifications, and backups. Never share API passwords, webhook URLs, or unredacted logs in public issues.

## More documentation

- [SMS webhooks, actions, and Lovelace card](docs/sms-and-lovelace.md)
- [Local development, quality checks, and contributing](CONTRIBUTING.md)
- [Agent and editor instructions](AGENTS.md)

## Support and license

Report reproducible bugs through [GitHub issues](https://github.com/andrewtryder/ha-voipms/issues). See the [VoIP.ms API documentation](https://voip.ms/m/apidocs.php) for provider API details.

This is an unofficial community project and is not affiliated with, endorsed by, or sponsored by VoIP.ms. Distributed under the [MIT License](LICENSE).
