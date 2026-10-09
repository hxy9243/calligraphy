"""Private font assets and fixed raster samples for the browser catalog."""
import io
import json
import os
from hashlib import sha256
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .style_catalog import STYLE_ALIASES, downloaded_catalog_entry

ROOT = Path(__file__).resolve().parent.parent
BLOCKED_STYLES = {"shutifang-liugongquan-kai"}


def allowed_style(style):
    canonical = STYLE_ALIASES.get(style, style)
    if os.environ.get("CALLIGRAPHY_DEMO_ALL_FONTS") == "1":
        return True
    configured = os.environ.get("CALLIGRAPHY_PUBLIC_STYLES", "")
    return canonical not in BLOCKED_STYLES and (not configured or canonical in configured.split(","))


def private_catalog():
    catalog = json.loads((ROOT / "data/calligraphy_fonts.json").read_text())
    # A public source checkout omits separately provisioned private font inputs.
    for entry in catalog:
        if entry.get("is_downloaded") == 1 and not (ROOT / entry["file_path"]).is_file():
            entry["is_downloaded"] = 0
    return catalog


def public_catalog():
    # Paths and font-download links are never included in the public API.
    return [{k: v for k, v in entry.items() if k not in {"file_path", "license_path", "source_url", "download_url"}}
            for entry in private_catalog() if allowed_style(entry["id"])]


def validate_style(style):
    canonical = STYLE_ALIASES.get(style, style)
    if not allowed_style(canonical):
        raise ValueError("此字体未开放使用 / Style is not available in this demo.")
    if canonical not in {"kai", "yan"} and not downloaded_catalog_entry(private_catalog(), canonical):
        from calligraphy.font_pipeline import style_path
        if not style_path(canonical).exists():
            raise ValueError("未知字体 / Unknown style.")
    return canonical


@lru_cache(maxsize=128)
def font_sample(style):
    """Only a fixed glyph is rendered; no font bytes or arbitrary input escape."""
    if not allowed_style(style):
        raise ValueError("Unavailable style")
    canonical = STYLE_ALIASES.get(style, style)
    saved = ROOT / 'data/font_samples' / (sha256(canonical.encode()).hexdigest() + '.png')
    if saved.exists():
        return saved.read_bytes()
    if canonical in {'kai', 'yan'}:
        from .editor_preview import cached_preview
        return cached_preview(json.dumps(dict(text='永', style=canonical, width=128, height=128,
            font_size=100, direction='vertical-rl', spacing=.18, fit=True, punctuation='omit', lines=[['永']]), sort_keys=True))
    entry = downloaded_catalog_entry(private_catalog(), style)
    if not entry:
        raise ValueError("Unknown font")
    font_path = (ROOT / entry["file_path"]).resolve()
    if not font_path.is_relative_to(ROOT / "data/fonts"):
        raise ValueError("Invalid font asset")
    font = ImageFont.truetype(str(font_path), 100)
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), "永", font=font)
    draw.text(((128 - box[2] + box[0]) / 2 - box[0], (128 - box[3] + box[1]) / 2 - box[1]), "永", font=font, fill="#1c1b18")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
