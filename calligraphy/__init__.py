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
from .paint_brush import BrushPainter
from .stroke_layers import compose_layers
from .widget import create_vector_player

__all__ = [
    "BrushPainter",
    "ContactBrush",
    "STYLE_CONFIGS",
    "STYLE_PRESETS",
    "compose_layers",
    "create_animation_gif",
    "create_vector_player",
    "get_style_config",
    "render_character_svg",
    "render_scene_svg",
    "render_style_comparison_svg",
    "render_timeline_images",
    "resolve_style_expansion",
    "trace_polyline",
]
__version__ = "0.1.0"
