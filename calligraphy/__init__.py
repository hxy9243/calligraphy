"""Reusable geometry and brush engines for calligraphy rendering."""

from .animation import (
    STYLE_CONFIGS,
    STYLE_PRESETS,
    create_animation_gif,
    get_style_config,
    render_character_svg,
    render_scene_svg,
    render_style_comparison_svg,
    render_timeline_images,
    resolve_style_expansion,
    trace_polyline,
)
from .brush_grammar import ContactBrush
from .contact_renderer import ContactScene
from .font_layers import FontLayerScene, LayerStore, prepare_character_layers
from .paint_brush import BrushPainter
from .renderer import (
    TemplateScene,
    create_scene,
    export_png,
    export_still,
    export_svg,
    export_video,
)
from .spec import Appearance, RenderPlan, SceneSpec, Transforms
from .stroke_layers import compose_layers
from .text import (
    create_text_plan,
    layout_text,
    load_bundled_glyphs,
    parse_text,
    resolve_glyphs,
    validate_glyph,
)
from .widget import create_vector_player

__all__ = [
    "Appearance",
    "BrushPainter",
    "ContactBrush",
    "ContactScene",
    "FontLayerScene",
    "LayerStore",
    "RenderPlan",
    "STYLE_CONFIGS",
    "STYLE_PRESETS",
    "SceneSpec",
    "TemplateScene",
    "Transforms",
    "compose_layers",
    "create_animation_gif",
    "create_scene",
    "create_text_plan",
    "create_vector_player",
    "export_png",
    "export_still",
    "export_svg",
    "export_video",
    "get_style_config",
    "layout_text",
    "load_bundled_glyphs",
    "parse_text",
    "prepare_character_layers",
    "render_character_svg",
    "render_scene_svg",
    "render_style_comparison_svg",
    "render_timeline_images",
    "resolve_glyphs",
    "resolve_style_expansion",
    "trace_polyline",
    "validate_glyph",
]
__version__ = "0.1.0"
