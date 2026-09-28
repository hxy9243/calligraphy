"""Glyph validation and resolution for Hanzi characters."""
import json
import math
import re
import urllib.parse
import urllib.request
from importlib.resources import files
from pathlib import Path
from typing import Dict, Any, Optional

from concurrent.futures import ThreadPoolExecutor

from .guides import GuideCache, get_default_guide_cache
from .input import parse_text

GLYPH_DATA_VERSION = "2.0.1"

_SVG_PATH_REGEX = re.compile(r"^[MmZzLlHhVvCcSsQqTtAa\d\s.,+\-eE]+$")


def load_bundled_glyphs() -> Dict[str, Any]:
    """Load bundled character records from GuideCache or fallback files."""
    cache = get_default_guide_cache()
    if len(cache) > 0:
        return {c: cache.get(c) for c in cache.characters()}
    try:
        data_dir = files("calligraphy").joinpath("assets/data")
        yong_bytes = data_dir.joinpath("yong.json").read_bytes()
        poem_bytes = data_dir.joinpath("poem-characters.json").read_bytes()
    except Exception:
        # Fallback to repo root
        root = Path(__file__).resolve().parent.parent.parent / "assets" / "data"
        yong_bytes = (root / "yong.json").read_bytes()
        poem_bytes = (root / "poem-characters.json").read_bytes()
    yong = json.loads(yong_bytes)
    poem = json.loads(poem_bytes)
    return {**poem, "永": yong}


bundled_glyphs = load_bundled_glyphs


def validate_glyph(character: str, glyph: Any) -> Dict[str, Any]:
    """Validate that glyph has 1–128 matching stroke SVG paths and median polylines."""
    if not isinstance(glyph, dict):
        raise TypeError(f"Invalid glyph {character}: expected a dictionary")
    strokes = glyph.get("strokes")
    medians = glyph.get("medians")
    if (
        not isinstance(strokes, list)
        or not (1 <= len(strokes) <= 128)
        or not isinstance(medians, list)
        or len(strokes) != len(medians)
    ):
        raise TypeError(f"Invalid glyph {character}: expected 1–128 matching strokes and medians")

    for i, (path, median) in enumerate(zip(strokes, medians)):
        if (
            not isinstance(path, str)
            or not path.lstrip().startswith(("M", "m"))
            or not _SVG_PATH_REGEX.match(path)
        ):
            raise TypeError(f"Invalid glyph {character}: stroke {i + 1} must be SVG path data")
        if not isinstance(median, list) or len(median) < 2:
            raise TypeError(f"Invalid glyph {character}: median {i + 1} needs finite [x,y] points")
        for point in median:
            if (
                not isinstance(point, (list, tuple))
                or len(point) != 2
                or isinstance(point[0], bool)
                or isinstance(point[1], bool)
                or not isinstance(point[0], (int, float))
                or not isinstance(point[1], (int, float))
                or not math.isfinite(point[0])
                or not math.isfinite(point[1])
            ):
                raise TypeError(f"Invalid glyph {character}: median {i + 1} needs finite [x,y] points")

    return glyph


def resolve_glyphs(
    text: str,
    glyphs: Optional[Dict[str, Any]] = None,
    fetch_missing: bool = False,
    punctuation: str = "break",
    fetch_func=None,
) -> Dict[str, Any]:
    """Resolve Han characters to stroke/median template records."""
    parsed = parse_text(text, punctuation=punctuation)
    glyphs_was_none = glyphs is None
    if glyphs is None:
        glyphs = load_bundled_glyphs()

    result = {}
    missing = []
    for character in parsed["uniqueCharacters"]:
        if character in glyphs:
            result[character] = validate_glyph(character, glyphs[character])
        else:
            missing.append(character)

    if missing and not fetch_missing:
        raise ValueError(
            f"Missing glyphs: {' '.join(missing)}. Supply glyph data or explicitly enable fetching."
        )

    newly_fetched = {}
    if fetch_func is not None:
        for character in missing:
            data = fetch_func(character)
            valid = validate_glyph(character, data)
            result[character] = valid
            newly_fetched[character] = valid
    elif missing:
        def _fetch_single(char: str):
            encoded = urllib.parse.quote(char)
            url = f"https://cdn.jsdelivr.net/npm/hanzi-writer-data@{GLYPH_DATA_VERSION}/{encoded}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "calligraphy-engine/0.1.0"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    if resp.status != 200:
                        raise ValueError(f"Could not fetch glyph {char}: HTTP {resp.status}")
                    raw = json.loads(resp.read().decode("utf-8"))
                    return char, raw
            except Exception as e:
                raise ValueError(f"Could not fetch glyph {char}: {e}") from e

        with ThreadPoolExecutor(max_workers=min(12, len(missing))) as executor:
            for char, raw_data in executor.map(_fetch_single, missing):
                valid = validate_glyph(char, raw_data)
                result[char] = valid
                newly_fetched[char] = valid

    # Persist newly fetched characters to default GuideCache so future resolutions are instant
    if newly_fetched and glyphs_was_none:
        cache = get_default_guide_cache()
        for char, rec in newly_fetched.items():
            cache.put(char, rec)
        try:
            cache.save()
        except Exception:
            pass

    return result
