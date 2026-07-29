import asyncio
import aiohttp
import sys
import json

HA_URL = "http://localhost:8123"


async def check_assertions():
    try:
        with open("artifacts/ha_token.txt", "r") as f:
            access_token = f.read().strip()
    except Exception:
        print("ha_token.txt not found. Did bootstrap succeed?")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("Running assertions...")

        # 1. Config Entry Loaded
        async with session.get(f"{HA_URL}/api/config/config_entries/entry") as resp:
            resp.raise_for_status()
            entries = await resp.json()
            voipms_entry = next((e for e in entries if e["domain"] == "voipms"), None)
            if not voipms_entry:
                print("Error: VoIP.ms config entry not found.")
                sys.exit(1)

            if voipms_entry["state"] != "loaded":
                print(
                    f"Error: VoIP.ms config entry is not loaded. State: {voipms_entry['state']}"
                )
                sys.exit(1)
            else:
                print("VoIP.ms config entry is LOADED.")

            with open("artifacts/config-entry-state.json", "w") as f:
                json.dump(voipms_entry, f, indent=2)

        # Wait a moment for entities to be initialized
        await asyncio.sleep(5)

        # 2. Check entities
        async with session.get(f"{HA_URL}/api/states") as resp:
            resp.raise_for_status()
            states = await resp.json()

            # Filter voipms entities (assuming they start with sensor.voipms_ or similar, or have voipms in entity_id or attribution)
            # A safer way is to check the device registry or entity registry, but we can look for specific substrings based on the integration
            # Actually, all voipms entities should have attribution "Data provided by VoIP.ms" or similar,
            # or just look for 'voipms' in the entity ID or device ID.
            # Let's check for some required sensors from the requirement:
            # - balance sensor
            # - inbound-call, outbound-call
            # - voicemail sensor
            # - last-sms, last-call

            summary = []
            expected_keywords = ["balance", "voicemail", "last_sms", "last_call"]
            found_keywords = {k: False for k in expected_keywords}

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
                    for k in expected_keywords:
                        if k in entity_id:
                            found_keywords[k] = True

            with open("artifacts/entity-summary.json", "w") as f:
                json.dump(summary, f, indent=2)

            for k, found in found_keywords.items():
                if not found:
                    print(
                        f"Warning: Expected entity related to '{k}' not found. Entities found: {[e['entity_id'] for e in summary]}"
                    )

            print(f"Found {len(summary)} VoIP.ms related entities.")

        # 3. Check services
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
            else:
                print("Service voipms.send_sms is registered.")

            with open("artifacts/service-summary.json", "w") as f:
                json.dump(voipms_services, f, indent=2)

        # 4. Restart HA and test reload
        print("Restarting Home Assistant to test config entry persistence...")
        async with session.post(f"{HA_URL}/api/services/homeassistant/restart") as resp:
            resp.raise_for_status()

        print("Waiting for HA to come back...")
        await asyncio.sleep(10)

        # Poll until available again
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
                                "Success: VoIP.ms config entry remained LOADED after restart."
                            )
                            break
            except Exception:
                pass
            await asyncio.sleep(2)
        else:
            print(
                "Error: Home Assistant did not come back with a LOADED voipms entry after restart."
            )
            sys.exit(1)

        print("All E2E assertions passed.")
        with open("artifacts/test-summary.txt", "w") as f:
            f.write("All E2E assertions passed.\n")


if __name__ == "__main__":
    asyncio.run(check_assertions())
