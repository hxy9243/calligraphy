"""Traditional and Simplified Chinese bidirectional conversion using OpenCC."""
from typing import Any, Dict

try:
    import opencc
except ImportError:
    opencc = None


class ConversionUnavailableError(RuntimeError):
    """The required Chinese script conversion engine could not be loaded."""


_CONVERTERS: Dict[str, Any] = {}


def _get_converter(config: str):
    if opencc is None:
        raise ConversionUnavailableError(
            "Chinese script conversion requires opencc. Reinstall the declared Python dependencies."
        )
    if config not in _CONVERTERS:
        _CONVERTERS[config] = opencc.OpenCC(config)
    return _CONVERTERS[config]


def convert_text(text: str, target: str = "simp") -> str:
    """Convert Chinese text between Traditional and Simplified Chinese.

    Args:
        text: Input string.
        target: 'simp' or 'zh-hans' for Simplified, 'trad' or 'zh-hant' for Traditional.

    Returns:
        Converted string.

    Raises:
        ValueError: The target is not a supported script.
        ConversionUnavailableError: The required opencc dependency is unavailable.
    """
    configs = {
        "simp": "t2s",
        "zh-hans": "t2s",
        "trad": "s2t",
        "zh-hant": "s2t",
    }
    if target not in configs:
        raise ValueError(f"Unsupported script conversion target: {target}")
    if not text:
        return ""
    converter = _get_converter(configs[target])
    return converter.convert(text)
