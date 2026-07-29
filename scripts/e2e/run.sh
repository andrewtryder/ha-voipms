#!/usr/bin/env bash
set -Eeuo pipefail

# Configuration and environment setup
export COMPOSE_PROJECT_NAME="voipms_e2e_$$"
export HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant}"
export HA_VERSION="${HA_VERSION:-stable}"
export INTEGRATION_REF="${INTEGRATION_REF:-}"
export E2E_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-600}"

# Load .env if present (for local testing)
if [ -f ".env" ]; then
    set +x # ensure tracing is off for secrets
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[^#]*= ]]; then
            export "$line"
        fi
    done < ".env"
fi

# Assert required env vars
: "${VOIPMS_API_USERNAME:?Environment variable VOIPMS_API_USERNAME is required}"
: "${VOIPMS_API_PASSWORD:?Environment variable VOIPMS_API_PASSWORD is required}"
: "${VOIPMS_DEFAULT_DID:?Environment variable VOIPMS_DEFAULT_DID is required}"
: "${HACS_GITHUB_TOKEN:?Environment variable HACS_GITHUB_TOKEN is required}"

# Create required directories (clean config first)
rm -rf .e2e/config
mkdir -p .e2e/config artifacts

# Define cleanup
cleanup() {
    echo "Starting cleanup..."
    set +e
    
    # Collect artifacts
    ./scripts/e2e/collect-artifacts.sh
    
    # Bring down docker compose
    docker compose -f scripts/e2e/docker-compose.yml down -v
    echo "Cleanup complete."
}
trap cleanup EXIT

echo "Setting up local directories and components..."
python3 scripts/e2e/setup-local.py

echo "Starting Home Assistant E2E environment..."
# Start HA
docker compose -f scripts/e2e/docker-compose.yml up -d

# Wait for HA to be ready
echo "Waiting for Home Assistant to become responsive..."
./scripts/e2e/wait-for-ha.sh

# Bootstrap HA config flows
echo "Bootstrapping Home Assistant flows..."
# Create a temporary venv for testing dependencies
python3 -m venv .e2e/venv
source .e2e/venv/bin/activate
python3 -m pip install -q aiohttp
python3 scripts/e2e/bootstrap-ha.py

# Run assertions
echo "Running E2E assertions..."
python3 scripts/e2e/assert-ha.py

echo "E2E tests completed successfully!"
