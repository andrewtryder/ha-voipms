# VoIP.ms assets

Generated fallback files are included here. To generate from the official VoIP.ms SVG URLs, copy `tools/build_voipms_assets.py` into the repo root under `tools/`, install dependencies, and run it from the repository root.

```bash
python -m pip install cairosvg pillow
python tools/build_voipms_assets.py
```

Recommended README logo markup after generation:

```html
<p align="center">
  <img src="images/voipms-logo.svg" alt="VoIP.ms" width="360">
</p>
```

Repository target paths:

```text
custom_components/voipms_custom/brand/icon.png
custom_components/voipms_custom/brand/logo.png
images/voipms-logo.svg
images/voipms-logo.png
```

Note: the included fallback icon is built from the open-source Dashboard Icons `voip-ms.svg`. Run the script to generate from the official URLs you provided.
