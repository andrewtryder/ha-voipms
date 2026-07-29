#!/usr/bin/env bash
set -Eeuo pipefail

TIMEOUT="${E2E_TIMEOUT_SECONDS:-600}"
INTERVAL=5
ELAPSED=0

echo "Polling Home Assistant on http://localhost:8123/ ..."
while true; do
    if curl -s -f http://localhost:8123/ > /dev/null; then
        echo "Home Assistant is ready!"
        break
    fi
    
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "Error: Timeout waiting for Home Assistant to start."
        exit 1
    fi
    
    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done
