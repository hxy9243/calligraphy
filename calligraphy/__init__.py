"""Reusable geometry and brush engines for calligraphy rendering."""
import importlib

__version__ = "0.1.0"

_LAZY_MODULES = {
    "Appearance": ".spec",
    "BrushPainter": ".paint_brush",
    "ContactBrush": ".brush_grammar",
    "ContactScene": ".contact_renderer",
    "FontLayerScene": ".font_layers",
    "LayerStore": ".font_layers",
    "RenderPlan": ".spec",
    "STYLE_CONFIGS": ".animation",
    "STYLE_PRESETS": ".animation",
    "SceneSpec": ".spec",
    "TemplateScene": ".renderer",
    "Transforms": ".spec",
    "compose_layers": ".stroke_layers",
    "create_animation_gif": ".animation",
    "create_scene": ".renderer",
    "create_text_plan": ".text",
    "create_vector_player": ".widget",
    "export_png": ".renderer",
    "export_still": ".renderer",
    "export_svg": ".renderer",
    "export_video": ".renderer",
    "get_style_config": ".animation",
    "layout_text": ".text",
    "load_bundled_glyphs": ".text",
    "parse_text": ".text",
    "prepare_character_layers": ".font_layers",
    "render_character_svg": ".animation",
    "render_scene_svg": ".animation",
    "render_style_comparison_svg": ".animation",
    "render_timeline_images": ".animation",
    "resolve_glyphs": ".text",
    "resolve_style_expansion": ".animation",
    "trace_polyline": ".animation",
    "validate_glyph": ".text",
}

__all__ = sorted(_LAZY_MODULES.keys())


def __getattr__(name: str):
    if name in _LAZY_MODULES:
        module = importlib.import_module(_LAZY_MODULES[name], __name__)
        val = getattr(module, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY_MODULES.keys()))
