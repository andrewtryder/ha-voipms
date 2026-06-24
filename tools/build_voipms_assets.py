#!/usr/bin/env python3
"""Build VoIP.ms assets for Home Assistant/HACS and README.

Run from the root of andrewtryder/ha-voipms:

    python tools/build_voipms_assets.py

This script downloads the official SVGs, renders padded PNG assets, and writes:

    custom_components/voipms_custom/brand/icon.png
    custom_components/voipms_custom/brand/logo.png
    images/voipms-logo.png
    images/voipms-logo.svg

Dependencies:

    pip install cairosvg pillow
"""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path
from typing import Tuple

import cairosvg
from PIL import Image, ImageChops

BRAND_SOURCE_URL = "https://voip.ms/resources/img/logo-black.svg"
README_SOURCE_URL = "https://voip.ms/resources/img/logo.svg"

ROOT = Path.cwd()
BRAND_DIR = ROOT / "custom_components" / "voipms_custom" / "brand"
IMAGES_DIR = ROOT / "images"
TOOLS_DIR = ROOT / "tools"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 asset builder for Home Assistant custom integration"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - explicit known URLs
        return response.read()


def render_svg(svg_bytes: bytes, output_width: int = 2048) -> Image.Image:
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=output_width)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def trim_transparent_or_background(image: Image.Image) -> Image.Image:
    """Trim transparent padding; fall back to trimming solid background."""
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        return image.crop(bbox)

    # Fallback for SVGs rendered onto a solid background.
    bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    return image.crop(bbox) if bbox else image


def make_square_asset(
    svg_bytes: bytes, size: int, padding_ratio: float = 0.12
) -> Image.Image:
    rendered = trim_transparent_or_background(render_svg(svg_bytes, output_width=2048))
    available = int(size * (1 - 2 * padding_ratio))
    scale = min(available / rendered.width, available / rendered.height)
    new_size: Tuple[int, int] = (
        max(1, round(rendered.width * scale)),
        max(1, round(rendered.height * scale)),
    )
    resized = rendered.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    canvas.alpha_composite(
        resized, ((size - new_size[0]) // 2, (size - new_size[1]) // 2)
    )
    return canvas


def make_readme_png(svg_bytes: bytes, width: int = 720) -> Image.Image:
    rendered = trim_transparent_or_background(
        render_svg(svg_bytes, output_width=width * 2)
    )
    height = max(1, round(rendered.height * (width / rendered.width)))
    return rendered.resize((width, height), Image.Resampling.LANCZOS)


def ensure_gitkeep(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    gitkeep = path / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def main() -> int:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading brand SVG: {BRAND_SOURCE_URL}")
    brand_svg = fetch(BRAND_SOURCE_URL)
    print(f"Downloading README SVG: {README_SOURCE_URL}")
    readme_svg = fetch(README_SOURCE_URL)

    # Keep the README SVG in the repo so README rendering is crisp.
    (IMAGES_DIR / "voipms-logo.svg").write_bytes(readme_svg)

    icon = make_square_asset(brand_svg, 256)
    logo = make_square_asset(brand_svg, 512)
    readme_png = make_readme_png(readme_svg, width=720)

    icon.save(BRAND_DIR / "icon.png", optimize=True)
    logo.save(BRAND_DIR / "logo.png", optimize=True)
    readme_png.save(IMAGES_DIR / "voipms-logo.png", optimize=True)

    print("Wrote:")
    print(f"  {BRAND_DIR / 'icon.png'}")
    print(f"  {BRAND_DIR / 'logo.png'}")
    print(f"  {IMAGES_DIR / 'voipms-logo.svg'}")
    print(f"  {IMAGES_DIR / 'voipms-logo.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
