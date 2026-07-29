#!/usr/bin/env bash
set -Eeuo pipefail

echo "Collecting artifacts..."
mkdir -p artifacts

# Collect Docker compose logs
if command -v docker > /dev/null; then
    docker compose -f scripts/e2e/docker-compose.yml logs --no-color > artifacts/docker-compose.log || true
    
    # Get HA version from image
    if [ -n "${COMPOSE_PROJECT_NAME:-}" ]; then
        docker inspect "${COMPOSE_PROJECT_NAME}_ha" --format '{{.Config.Image}}' > artifacts/ha-image-digest.txt || true
    fi
fi

# Collect and sanitize Home Assistant logs
if [ -f .e2e/config/home-assistant.log ]; then
    cp .e2e/config/home-assistant.log artifacts/home-assistant.raw.log
    
    # Sanitize secrets
    USERNAME_VAR="${VOIPMS_API_USERNAME:-}"
    PASSWORD_VAR="${VOIPMS_API_PASSWORD:-}"
    DID_VAR="${VOIPMS_DEFAULT_DID:-}"
    
    # Use python for safer replacement to avoid sed syntax issues with special chars
    python3 -c "
import os
import sys

def sanitize_file(filepath):
    if not os.path.exists(filepath):
        return
        
    with open(filepath, 'r') as f:
        content = f.read()
        
    replacements = {
        os.environ.get('VOIPMS_API_PASSWORD', ''): '***PASSWORD***',
        os.environ.get('VOIPMS_API_USERNAME', ''): '***USERNAME***',
        os.environ.get('VOIPMS_DEFAULT_DID', ''): '***DID***',
        os.environ.get('HACS_GITHUB_TOKEN', ''): '***GITHUB_TOKEN***'
    }
    
    for secret, replacement in replacements.items():
        if secret and len(secret) > 3:  # Don't replace tiny strings by accident
            content = content.replace(secret, replacement)
            
    with open(filepath.replace('.raw.', '.'), 'w') as f:
        f.write(content)

sanitize_file('artifacts/home-assistant.raw.log')
" || true
    
    # Clean up raw
    rm -f artifacts/home-assistant.raw.log
fi

# Get sha256 of installed files
if command -v sha256sum > /dev/null; then
    find .e2e/config/custom_components/voipms -type f -exec sha256sum {} + > artifacts/installed-files.sha256 || true
elif command -v shasum > /dev/null; then
    find .e2e/config/custom_components/voipms -type f -exec shasum -a 256 {} + > artifacts/installed-files.sha256 || true
fi

# Sanitize json files
for json_file in artifacts/*.json; do
    if [ -f "$json_file" ]; then
        python3 -c "
import os
import json
import sys

filepath = sys.argv[1]
with open(filepath, 'r') as f:
    content = f.read()
    
replacements = {
    os.environ.get('VOIPMS_API_PASSWORD', ''): '***PASSWORD***',
    os.environ.get('VOIPMS_API_USERNAME', ''): '***USERNAME***',
    os.environ.get('VOIPMS_DEFAULT_DID', ''): '***DID***'
}

for secret, replacement in replacements.items():
    if secret and len(secret) > 3:
        content = content.replace(secret, replacement)
        
with open(filepath, 'w') as f:
    f.write(content)
" "$json_file" || true
    fi
done

# Remove HA token from artifacts
rm -f artifacts/ha_token.txt

echo "Artifacts collected in artifacts/"
