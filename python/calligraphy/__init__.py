"""Reusable geometry and brush engines for calligraphy rendering."""

from .brush_grammar import ContactBrush
from .paint_brush import BrushPainter
from .stroke_layers import compose_layers

__all__ = ["BrushPainter", "ContactBrush", "compose_layers"]
__version__ = "0.1.0"
