"""Traditional and Simplified Chinese bidirectional conversion using zhconv."""
try:
    import zhconv
except ImportError:
    zhconv = None


class ConversionUnavailableError(RuntimeError):
    """The required Chinese script conversion engine could not be loaded."""


def convert_text(text: str, target: str = "simp") -> str:
    """Convert Chinese text between Traditional and Simplified Chinese.
    
    Args:
        text: Input string.
        target: 'simp' or 'zh-hans' for Simplified, 'trad' or 'zh-hant' for Traditional.
        
    Returns:
        Converted string.

    Raises:
        ValueError: The target is not a supported script.
        ConversionUnavailableError: The required zhconv dependency is unavailable.
    """
    locales = {"simp": "zh-hans", "zh-hans": "zh-hans", "trad": "zh-hant", "zh-hant": "zh-hant"}
    if target not in locales:
        raise ValueError(f"Unsupported script conversion target: {target}")
    if not text:
        return ""
    if zhconv is None:
        raise ConversionUnavailableError(
            "Chinese script conversion requires zhconv. Reinstall the declared Python dependencies."
        )
    return zhconv.convert(text, locales[target])
