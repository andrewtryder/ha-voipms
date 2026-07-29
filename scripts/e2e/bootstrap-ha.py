import asyncio
import os
import aiohttp
import json
import sys

HA_URL = "http://localhost:8123"

async def bootstrap():
    async with aiohttp.ClientSession() as session:
        print("Starting Home Assistant onboarding...")
        
        # 1. Create admin user
        onboarding_user_payload = {
            "name": "Admin",
            "username": "admin",
            "password": "Password123!",
            "client_id": f"{HA_URL}/",
            "language": "en"
        }
        async with session.post(f"{HA_URL}/api/onboarding/users", json=onboarding_user_payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            auth_code = data.get("auth_code")
            if not auth_code:
                print("Failed to get auth_code from onboarding.")
                sys.exit(1)
        print("Admin user created.")

        # 2. Get access token
        token_payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": HA_URL + "/"
        }
        async with session.post(f"{HA_URL}/auth/token", data=token_payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            access_token = data.get("access_token")
            if not access_token:
                print("Failed to get access_token.")
                sys.exit(1)
                
        # Write token to file for later scripts
        os.makedirs("artifacts", exist_ok=True)
        with open("artifacts/ha_token.txt", "w") as f:
            f.write(access_token)
        print("Access token acquired and saved to artifacts/ha_token.txt (will be sanitized/removed later).")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # 3. Complete onboarding
        core_config_payload = {
            "location_name": "E2E Test",
            "time_zone": "America/New_York",
            "elevation": 0,
            "unit_system": "metric",
            "currency": "USD",
            "country": "US",
            "language": "en"
        }
        async with session.post(f"{HA_URL}/api/onboarding/core_config", json=core_config_payload, headers=headers) as resp:
            resp.raise_for_status()
        
        analytics_payload = {}
        async with session.post(f"{HA_URL}/api/onboarding/analytics", json=analytics_payload, headers=headers) as resp:
            # Not strict if this fails
            pass
            
        async with session.post(f"{HA_URL}/api/onboarding/integration", json={}, headers=headers) as resp:
            pass

        print("Onboarding complete.")

        # 4. Wait for HACS to initialize
        print("Waiting for HACS to initialize...")
        for _ in range(30):
            async with session.get(f"{HA_URL}/api/states/sensor.hacs", headers=headers) as resp:
                if resp.status == 200:
                    break
            await asyncio.sleep(2)
        else:
            print("Warning: sensor.hacs not found, HACS may not be fully loaded, or it's still initializing.")

        # 5. Configure VoIP.ms integration
        print("Starting VoIP.ms config flow...")
        username = os.environ["VOIPMS_API_USERNAME"]
        password = os.environ["VOIPMS_API_PASSWORD"]
        default_did = os.environ["VOIPMS_DEFAULT_DID"]
        
        async with session.post(f"{HA_URL}/api/config/config_entries/flow", json={"handler": "voipms"}, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            flow_id = data["flow_id"]
            
        voipms_config = {
            "username": username,
            "password": password,
            "default_did": default_did
        }
        
        async with session.post(f"{HA_URL}/api/config/config_entries/flow/{flow_id}", json=voipms_config, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            
            if data.get("type") == "create_entry":
                print("VoIP.ms config entry created successfully.")
                entry_id = data["result"]["entry_id"]
            else:
                print(f"Failed to create config entry: {data}")
                sys.exit(1)
        
        # Set manage_webhook to false in options flow if possible, or update the entry.
        # Actually, if we just update the config entry options via HA API (not options flow, but directly if possible)
        # Wait, the best way is through Options flow, or we can just accept that the config flow creates the webhook?
        # The user said: "If the branch supports an option that disables automatic webhook management, set that option before or immediately after loading the entry."
        # We can update the config entry options via the config_entries API if it exists, or via options flow.
        
        print("Setting manage_webhook: false via options flow...")
        async with session.post(f"{HA_URL}/api/config/config_entries/options/flow", json={"handler": entry_id}, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                opt_flow_id = data["flow_id"]
                async with session.post(f"{HA_URL}/api/config/config_entries/options/flow/{opt_flow_id}", json={"manage_webhook": False}, headers=headers) as resp2:
                    if resp2.status == 200:
                        print("Successfully disabled manage_webhook.")
                    else:
                        print("Failed to submit manage_webhook option.")
            else:
                print("Options flow not supported or failed to initiate. manage_webhook will remain default.")

        print("Bootstrap complete.")

if __name__ == "__main__":
    asyncio.run(bootstrap())
