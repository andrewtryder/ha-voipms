#!/usr/bin/env python3
"""Bootstrap a Home Assistant instance for E2E testing."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import aiohttp

HA_URL = "http://localhost:8123"
ARTIFACTS = Path("artifacts")


async def _write_text(path: Path, content: str) -> None:
    await asyncio.to_thread(path.write_text, content)


async def bootstrap() -> None:
    async with aiohttp.ClientSession() as session:
        print("Starting Home Assistant onboarding...")

        onboarding_user_payload = {
            "name": "Admin",
            "username": "admin",
            "password": "Password123!",
            "client_id": f"{HA_URL}/",
            "language": "en",
        }
        async with session.post(
            f"{HA_URL}/api/onboarding/users", json=onboarding_user_payload
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            auth_code = data.get("auth_code")
            if not auth_code:
                print("Failed to get auth_code from onboarding.")
                sys.exit(1)
        print("Admin user created.")

        token_payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": HA_URL + "/",
        }
        async with session.post(f"{HA_URL}/auth/token", data=token_payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            access_token = data.get("access_token")
            if not access_token:
                print("Failed to get access_token.")
                sys.exit(1)

        await asyncio.to_thread(ARTIFACTS.mkdir, exist_ok=True)
        await _write_text(ARTIFACTS / "ha_token.txt", access_token)
        print(
            "Access token acquired and saved to artifacts/ha_token.txt "
            "(will be sanitized/removed later)."
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        core_config_payload = {
            "location_name": "E2E Test",
            "time_zone": "America/New_York",
            "elevation": 0,
            "unit_system": "metric",
            "currency": "USD",
            "country": "US",
            "language": "en",
        }
        async with session.post(
            f"{HA_URL}/api/onboarding/core_config",
            json=core_config_payload,
            headers=headers,
        ) as resp:
            resp.raise_for_status()

        async with session.post(
            f"{HA_URL}/api/onboarding/analytics",
            json={},
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                print(f"Warning: analytics onboarding returned {resp.status}")

        async with session.post(
            f"{HA_URL}/api/onboarding/integration", json={}, headers=headers
        ) as resp:
            if resp.status >= 400:
                print(f"Warning: integration onboarding returned {resp.status}")

        print("Onboarding complete.")

        print("Waiting for HACS to initialize...")
        for _ in range(30):
            async with session.get(
                f"{HA_URL}/api/states/sensor.hacs", headers=headers
            ) as resp:
                if resp.status == 200:
                    break
            await asyncio.sleep(2)
        else:
            print(
                "Warning: sensor.hacs not found, HACS may not be fully loaded, "
                "or it's still initializing."
            )

        print("Starting VoIP.ms config flow...")
        username = os.environ["VOIPMS_API_USERNAME"]
        password = os.environ["VOIPMS_API_PASSWORD"]
        default_did = os.environ["VOIPMS_DEFAULT_DID"]

        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow",
            json={"handler": "voipms"},
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            flow_id = data["flow_id"]

        voipms_config = {
            "username": username,
            "password": password,
            "default_did": default_did,
            "manage_webhook": False,
        }

        async with session.post(
            f"{HA_URL}/api/config/config_entries/flow/{flow_id}",
            json=voipms_config,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

            if data.get("type") == "create_entry":
                print("VoIP.ms config entry created successfully.")
            else:
                print(f"Failed to create config entry: {data}")
                sys.exit(1)

        print("Bootstrap complete.")


if __name__ == "__main__":
    asyncio.run(bootstrap())
