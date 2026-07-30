#!/usr/bin/env python3
"""Assert Home Assistant E2E state after bootstrap."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

HA_URL = "http://localhost:8123"
ARTIFACTS = Path("artifacts")


async def _read_text(path: Path) -> str:
    return await asyncio.to_thread(path.read_text)


async def _write_text(path: Path, content: str) -> None:
    await asyncio.to_thread(path.write_text, content)


async def check_assertions() -> None:
    token_path = ARTIFACTS / "ha_token.txt"
    try:
        access_token = (await _read_text(token_path)).strip()
    except OSError:
        print("ha_token.txt not found. Did bootstrap succeed?")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("Running assertions...")

        async with session.get(f"{HA_URL}/api/config/config_entries/entry") as resp:
            resp.raise_for_status()
            entries = await resp.json()
            voipms_entry = next((e for e in entries if e["domain"] == "voipms"), None)
            if not voipms_entry:
                print("Error: VoIP.ms config entry not found.")
                sys.exit(1)

            if voipms_entry["state"] != "loaded":
                print(
                    "Error: VoIP.ms config entry is not loaded. "
                    f"State: {voipms_entry['state']}"
                )
                sys.exit(1)

            print("VoIP.ms config entry is LOADED.")
            await _write_text(
                ARTIFACTS / "config-entry-state.json",
                json.dumps(voipms_entry, indent=2),
            )

        await asyncio.sleep(5)

        async with session.get(f"{HA_URL}/api/states") as resp:
            resp.raise_for_status()
            states = await resp.json()

            summary = []
            expected_keywords = ["balance", "voicemail", "last_sms", "last_call"]
            found_keywords = dict.fromkeys(expected_keywords, False)

            for state in states:
                entity_id = state["entity_id"]
                if (
                    "voipms" in entity_id
                    or "voicemail" in entity_id
                    or "balance" in entity_id
                ):
                    summary.append({"entity_id": entity_id, "state": state["state"]})
                    if state["state"] == "unavailable":
                        print(f"Warning: Entity {entity_id} is unavailable.")
                    for key in expected_keywords:
                        if key in entity_id:
                            found_keywords[key] = True

            await _write_text(
                ARTIFACTS / "entity-summary.json",
                json.dumps(summary, indent=2),
            )

            for key, found in found_keywords.items():
                if not found:
                    print(
                        f"Warning: Expected entity related to '{key}' not found. "
                        f"Entities found: {[e['entity_id'] for e in summary]}"
                    )

            print(f"Found {len(summary)} VoIP.ms related entities.")

        async with session.get(f"{HA_URL}/api/services") as resp:
            resp.raise_for_status()
            services = await resp.json()

            voipms_services = next(
                (s for s in services if s["domain"] == "voipms"), None
            )
            if not voipms_services:
                print("Error: VoIP.ms services domain not found.")
                sys.exit(1)

            if "send_sms" not in voipms_services["services"]:
                print("Error: voipms.send_sms service not registered.")
                sys.exit(1)

            print("Service voipms.send_sms is registered.")
            await _write_text(
                ARTIFACTS / "service-summary.json",
                json.dumps(voipms_services, indent=2),
            )

        print("Restarting Home Assistant to test config entry persistence...")
        async with session.post(f"{HA_URL}/api/services/homeassistant/restart") as resp:
            resp.raise_for_status()

        print("Waiting for HA to come back...")
        await asyncio.sleep(10)

        for _ in range(60):
            try:
                async with session.get(
                    f"{HA_URL}/api/config/config_entries/entry"
                ) as resp:
                    if resp.status == 200:
                        entries = await resp.json()
                        voipms_entry = next(
                            (e for e in entries if e["domain"] == "voipms"), None
                        )
                        if voipms_entry and voipms_entry["state"] == "loaded":
                            print(
                                "Success: VoIP.ms config entry remained LOADED "
                                "after restart."
                            )
                            break
            except (aiohttp.ClientError, TimeoutError, OSError) as err:
                print(f"Waiting for Home Assistant restart: {err}")
            await asyncio.sleep(2)
        else:
            print(
                "Error: Home Assistant did not come back with a LOADED voipms "
                "entry after restart."
            )
            sys.exit(1)

        print("All E2E assertions passed.")
        await _write_text(
            ARTIFACTS / "test-summary.txt", "All E2E assertions passed.\n"
        )


if __name__ == "__main__":
    asyncio.run(check_assertions())
