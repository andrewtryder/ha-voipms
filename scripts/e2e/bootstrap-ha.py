import asyncio
import os
import aiohttp
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

        # 2. Get access token
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

        # Write token to file for later scripts
        os.makedirs("artifacts", exist_ok=True)
        with open("artifacts/ha_token.txt", "w") as f:
            f.write(access_token)
        print(
            "Access token acquired and saved to artifacts/ha_token.txt (will be sanitized/removed later)."
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # 3. Complete onboarding
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

        analytics_payload = {}
        async with session.post(
            f"{HA_URL}/api/onboarding/analytics",
            json=analytics_payload,
            headers=headers,
        ) as resp:
            # Not strict if this fails
            pass

        async with session.post(
            f"{HA_URL}/api/onboarding/integration", json={}, headers=headers
        ) as resp:
            pass

        print("Onboarding complete.")

        # 4. Wait for HACS to initialize
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
                "Warning: sensor.hacs not found, HACS may not be fully loaded, or it's still initializing."
            )

        # 5. Configure VoIP.ms integration
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
