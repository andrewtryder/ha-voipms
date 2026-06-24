# VoIP.ms Custom Integration

<p align="center">
  <img src="custom_components/voipms_custom/brand/logo.png" alt="VoIP.ms" width="180">
</p>

This repository contains the **VoIP.ms Custom Integration** for Home Assistant, enabling call handling, SMS messaging, and balance monitoring with the VoIP.ms API.

## Local Development

### Prerequisites

- Python 3.12+
- Docker (for Hassfest)

### Installation

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Testing

Run the test suite:

```bash
PYTHONPATH=. coverage run -m pytest
coverage report
```

### Quality Checks

- Format: `ruff format --check .`
- Lint: `ruff check .`

### Hassfest Validation (Home Assistant structure)

Validate the integration structure for Home Assistant compatibility:

```bash
docker run --rm -v "$(pwd):/github/workspace" ghcr.io/home-assistant/hassfest
```

### Docker Compose Development

Run a local Home Assistant instance with this integration:

```bash
docker compose up -d
```

The integration will be mounted at `$(pwd)/custom_components/voipms_custom` inside the Home Assistant container.

### HACS Publishing Notes

- This integration requires a **public GitHub repository** to pass validation with the HACS Action
- The repository visibility must be public before merging PRs that will be published to HACS
- A GitHub release must exist for HACS default store inclusion
- Integration brand assets live in `custom_components/voipms_custom/brand/`

### Integration Features

- Call detail recording (CDR)
- SMS sending and receiving
- Balance monitoring
- Webhook-based notifications
