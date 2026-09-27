"""Parse writing order without converting simplified/traditional characters."""
import re

PUNCTUATION_CHARS = set("，。！？、；：,.!?;:「」『』（）()“”‘’《》〈〉…—·")


def is_han(char: str) -> bool:
    """Return True if char belongs to the Unicode Han script."""
    if len(char) != 1:
        return False
    code = ord(char)
    return (
        (0x4E00 <= code <= 0x9FFF) or       # CJK Unified Ideographs
        (0x3400 <= code <= 0x4DBF) or       # CJK Extension A
        (0x20000 <= code <= 0x2A6DF) or     # CJK Extension B
        (0x2A700 <= code <= 0x2B73F) or     # CJK Extension C
        (0x2B740 <= code <= 0x2B81F) or     # CJK Extension D
        (0x2B820 <= code <= 0x2CEAF) or     # CJK Extension E
        (0x2CEB0 <= code <= 0x2EBEF) or     # CJK Extension F
        (0x30000 <= code <= 0x3134F) or     # CJK Extension G
        (0x31350 <= code <= 0x323AF) or     # CJK Extension H
        (0x2EBF0 <= code <= 0x2EE5F) or     # CJK Extension I
        (0xF900 <= code <= 0xFAFF) or       # CJK Compatibility Ideographs
        (0x2F800 <= code <= 0x2FA1F) or     # CJK Compatibility Ideographs Supplement
        (0x2E80 <= code <= 0x2EFF) or       # CJK Radicals Supplement
        (0x2F00 <= code <= 0x2FDF) or       # Kangxi Radicals
        code in (0x3005, 0x3007, 0x303B) or # Iteration marks, zero
        (0x3021 <= code <= 0x3029) or       # Hangzhou numerals
        (0x3038 <= code <= 0x303A)
    )


def is_punctuation(char: str) -> bool:
    return char in PUNCTUATION_CHARS


def parse_text(text: str, punctuation: str = "break") -> dict:
    """Parse writing order into lines of Han characters, omitted symbols and unique characters.
    
    Supports punctuation policies:
      - 'break': punctuation starts a new line if the current line has characters, but is omitted from glyphs
      - 'omit': punctuation is omitted without breaking lines
    """
    if not isinstance(text, str):
        raise TypeError("text must be a non-empty string")
    if not text.strip():
        raise ValueError("text must be a non-empty string")
    if punctuation not in ("break", "omit"):
        raise ValueError("punctuation must be break or omit")

    lines = [[]]
    omitted = []
    omitted_set = set()
    unsupported = []
    unsupported_set = set()

    def record_omitted(c: str):
        if c not in omitted_set:
            omitted_set.add(c)
            omitted.append(c)

    def record_unsupported(c: str):
        if c not in unsupported_set:
            unsupported_set.add(c)
            unsupported.append(c)

    def line_break():
        if lines[-1]:
            lines.append([])

    normalized = re.sub(r"\r\n?", "\n", text)
    for character in normalized:
        if character == "\n":
            line_break()
        elif character.isspace():
            record_omitted(character)
        elif is_han(character):
            lines[-1].append(character)
        elif is_punctuation(character):
            record_omitted(character)
            if punctuation == "break":
                line_break()
        else:
            record_unsupported(character)

    if unsupported:
        raise ValueError(
            f"Unsupported characters: {' '.join(unsupported)}. Use Han text, whitespace and supported punctuation."
        )

    nonempty = [line for line in lines if line]
    characters = [c for line in nonempty for c in line]
    if not characters:
        raise ValueError("text must contain at least one Han character")
    if len(characters) > 512:
        raise ValueError("text exceeds the 512-character single-page limit")

    unique_characters = list(dict.fromkeys(characters))
    return {
        "lines": nonempty,
        "characters": characters,
        "uniqueCharacters": unique_characters,
        "omitted": omitted,
    }
