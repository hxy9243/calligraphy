"""Replay one inferred stroke, optionally with disconnected contact segments."""
import numpy as np
from .brush_grammar import ContactBrush, complete, validate


class ContactStroke:
    def __init__(self, stroke):
        if 'segments' not in stroke:
            self.segments = [(0., 1., ContactBrush(stroke))]
        else:
            segments = stroke['segments']
            if not isinstance(segments, list) or not segments:
                raise ValueError('Expected nonempty contact segments')
            self.segments = []
            for item in segments:
                start, end = item['start'], item['end']
                if not np.isfinite([start, end]).all() or not 0 <= start < end <= 1:
                    raise ValueError('Contact segment progress must satisfy 0 <= start < end <= 1')
                validate(item['stroke'])
                self.segments.append((start, end, ContactBrush(item['stroke'])))

    def advance(self, progress):
        mask = np.zeros((480, 480), np.float32)
        for start, end, painter in self.segments:
            if progress >= start:
                mask = np.maximum(mask, painter.advance(min(1, (progress - start) / (end - start))))
        return mask


def complete_stroke(stroke):
    if 'segments' not in stroke:
        return complete(stroke)
    return ContactStroke(stroke).advance(1)
