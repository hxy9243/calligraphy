"""Replay one inferred stroke, optionally with disconnected contact segments."""
import numpy as np
from .brush_grammar import ContactBrush, complete, validate


class ContactStroke:
    def __init__(self, stroke):
        # Derived ownership keeps source alpha exact; guides remain editable.
        ownership = stroke.get('ownership', {})
        self.clip = self._ownership_rows(ownership.get('clip', []), 2)
        self.patches = self._ownership_rows(ownership.get('patches', []), 3)
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

    @staticmethod
    def _ownership_rows(rows, width):
        data = np.asarray(rows, dtype=np.float64)
        if data.size == 0:
            return np.empty((0, width))
        if (data.ndim != 2 or data.shape[1] != width or not np.isfinite(data).all()
                or np.any(data[:, 0] != np.floor(data[:, 0]))
                or np.any(data[:, 0] < 0) or np.any(data[:, 0] >= 480 * 480)
                or np.any(data[:, 1:] < 0) or np.any(data[:, 1:] > 1)
                or len(np.unique(data[:, 0])) != len(data)):
            raise ValueError('Invalid contact ownership pixels')
        return data

    def advance(self, progress):
        mask = np.zeros((480, 480), np.float32)
        for start, end, painter in self.segments:
            if progress >= start:
                mask = np.maximum(mask, painter.advance(min(1, (progress - start) / (end - start))))
        flat = mask.ravel()
        indices = self.clip[:, 0].astype(np.intp)
        flat[indices] = np.minimum(flat[indices], self.clip[:, 1])
        active = self.patches[self.patches[:, 2] <= progress]
        indices = active[:, 0].astype(np.intp)
        flat[indices] = np.maximum(flat[indices], active[:, 1])
        return mask


def complete_stroke(stroke):
    if 'segments' not in stroke and 'ownership' not in stroke:
        return complete(stroke)
    return ContactStroke(stroke).advance(1)
