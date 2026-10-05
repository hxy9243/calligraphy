"""Shared names for public catalog entries and locally registered styles."""

STYLE_ALIASES = {
    "mashanzheng-kai": "mashanzheng",
    "qiji-font-kai": "qiji-kai",
    "hanwang-lisu-medium": "lishu hanwang",
    "longcang-xingshu": "longcang",
    "tw-sung": "tw-sung",
    "genryu-min": "genryu-min",
    "genwan-min": "genwan-min",
    "cwtex-fangsong": "cwtex-fangsong",
    "hanwang-shinsu": "hanwang-shinsu",
}


def downloaded_catalog_entry(catalog, style):
    """Resolve the downloaded font using the same aliases as API admission."""
    canonical = STYLE_ALIASES.get(style, style)
    for entry in catalog:
        if entry.get("is_downloaded") != 1:
            continue
        catalog_id = entry.get("id")
        if (STYLE_ALIASES.get(catalog_id, catalog_id) == canonical
                or catalog_id == f"{canonical}-kai"):
            return entry
    return None
