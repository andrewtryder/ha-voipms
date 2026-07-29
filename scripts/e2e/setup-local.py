#!/usr/bin/env python3
import os
import shutil
import urllib.request
import zipfile
import json
import subprocess


def main():
    e2e_dir = os.path.abspath(".e2e/config")
    hacs_dir = os.path.join(e2e_dir, "custom_components", "hacs")
    voipms_dir = os.path.join(e2e_dir, "custom_components", "voipms")

    os.makedirs(hacs_dir, exist_ok=True)
    os.makedirs(voipms_dir, exist_ok=True)

    print("Downloading latest HACS release...")
    hacs_zip = "hacs.zip"
    try:
        # Fetch latest release URL
        req = urllib.request.Request(
            "https://api.github.com/repos/hacs/integration/releases/latest"
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            zip_url = next(
                asset["browser_download_url"]
                for asset in data["assets"]
                if asset["name"] == "hacs.zip"
            )
            hacs_version = data["tag_name"]

        print(f"Downloading HACS {hacs_version} from {zip_url}")
        urllib.request.urlretrieve(zip_url, hacs_zip)

        with zipfile.ZipFile(hacs_zip, "r") as zip_ref:
            zip_ref.extractall(hacs_dir)

        # Store version for artifacts
        os.makedirs("artifacts", exist_ok=True)
        with open("artifacts/hacs-version.txt", "w") as f:
            f.write(hacs_version)
    finally:
        if os.path.exists(hacs_zip):
            os.remove(hacs_zip)

    print("Copying local voipms integration...")
    src_voipms = os.path.abspath("custom_components/voipms")
    if os.path.exists(src_voipms):
        shutil.rmtree(voipms_dir)
        shutil.copytree(src_voipms, voipms_dir)

    # Get current git sha
    try:
        git_sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("utf-8")
            .strip()
        )
        with open("artifacts/integration-git-sha.txt", "w") as f:
            f.write(git_sha)
        print(f"Integration tested at commit {git_sha}")
    except Exception as e:
        print(f"Warning: Could not get git SHA: {e}")

    # Setup HACS config entry in .storage to bypass device flow
    storage_dir = os.path.join(e2e_dir, ".storage")
    os.makedirs(storage_dir, exist_ok=True)

    # We create a base core.config_entries file if it doesn't exist
    config_entries_path = os.path.join(storage_dir, "core.config_entries")

    hacs_token = os.environ.get("HACS_GITHUB_TOKEN", "")
    hacs_entry = {
        "entry_id": "hacs_e2e_test_entry",
        "version": 1,
        "minor_version": 1,
        "domain": "hacs",
        "title": "HACS",
        "data": {"token": hacs_token},
        "options": {},
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "unique_id": "123456",
        "disabled_by": None,
    }

    config_entries = {
        "version": 1,
        "minor_version": 1,
        "key": "core.config_entries",
        "data": {"entries": [hacs_entry]},
    }

    with open(config_entries_path, "w") as f:
        json.dump(config_entries, f, indent=2)

    print("Injected HACS config entry into .storage")


if __name__ == "__main__":
    main()
