"""Canonical studio composition shared by editor, still and video render paths."""
from calligraphy.spec import Appearance, SceneSpec, Transforms


def scene_spec_from_params(text, style, params):
    return SceneSpec(
        text=text, style=style,
        layout={
            "width": params.get("width", 720),
            "height": params.get("height", 960),
            "direction": params.get("direction", "vertical-rl"),
            "characters_per_line": params.get("characters_per_line"),
            "gap": float(params.get("spacing", params.get("gap", 0.18))),
            "font_size": params.get("font_size"),
            "fit": params.get("fit", True),
        },
        timing={
            "stroke_seconds": params.get("stroke_seconds", 0.18),
            "character_gap": params.get("character_gap", 0.15),
            "intro": params.get("intro", 0.5),
            "outro": params.get("outro", 1.0),
        },
        punctuation=params.get("punctuation", "omit"),
        appearance=Appearance.from_dict({"paper": params.get("paper", "#f8f3e9"),
                                         "ink": params.get("ink", "#1c1b18")}),
        transforms=Transforms(scale=params.get("scale", 1.0),
                              stretch=params.get("stretch", 1.0),
                              rotation=params.get("rotation", 0.0)),
    )
