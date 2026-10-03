"""Traditional and Simplified Chinese bidirectional conversion using zhconv."""
from typing import Dict

try:
    import zhconv
    _HAS_ZHCONV = True
except ImportError:
    _HAS_ZHCONV = False


def convert_text(text: str, target: str = "simp") -> str:
    """Convert Chinese text between Traditional and Simplified Chinese.
    
    Args:
        text: Input string.
        target: 'simp' or 'zh-hans' for Simplified, 'trad' or 'zh-hant' for Traditional.
        
    Returns:
        Converted string.
    """
    if not text:
        return ""
    if _HAS_ZHCONV:
        locale = "zh-hans" if target in ("simp", "zh-hans") else "zh-hant"
        return zhconv.convert(text, locale)
    return text
