"""Compose bounded, overlapping stroke layers without leaking future arms."""

import numpy as np
from scipy import ndimage as ndi


def compose_layers(support, progress, ink, min_component=7):
    """Return layer membership, earliest exposure and first-paint owner.

    Each support is a complete stroke, including shared intersections. The
    flattened exposure map is equivalent to max-compositing all animated
    layers with the same source ink intensity. It does not accumulate darkness
    when a later stroke crosses already painted ink.
    """
    support = np.asarray(support, dtype=bool)
    progress = np.asarray(progress, dtype=np.float32)
    ink = np.asarray(ink, dtype=bool)
    if support.ndim != 3 or progress.shape != support.shape or ink.shape != support.shape[1:]:
        raise ValueError("Expected support/progress [stroke,y,x] and ink [y,x]")
    if not np.isfinite(progress[support]).all():
        raise ValueError("Stroke progress must be finite inside its support")
    layers = support & ink[None, :, :]
    for i, layer in enumerate(layers):
        labels, _ = ndi.label(layer)
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        layers[i] &= sizes[labels] >= min_component
    arrivals = np.where(
        layers,
        np.arange(len(layers))[:, None, None] + np.clip(progress, 0, 1) * 0.88,
        np.inf,
    )
    exposure = arrivals.min(axis=0).astype(np.float32)
    owner = arrivals.argmin(axis=0).astype(np.int16)
    owner[~np.isfinite(exposure)] = -1
    return layers, exposure, owner
