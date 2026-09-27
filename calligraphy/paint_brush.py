"""Pressure-controlled elliptical brush fitting and monotonic ink deposition."""

import io
import xml.etree.ElementTree as ET

import cairosvg
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from skimage.morphology import skeletonize

SIZE = 480
SCALE = 3
PAPER = (247, 245, 239)


def ink_image(ink, size):
    """Render a normalized ink mask on the default paper color."""
    rgb = np.array(PAPER)[None, None, :] * (1 - ink[..., None]) + 25 * ink[..., None]
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).resize(
        (size, size), Image.Resampling.LANCZOS
    )


def load_outlines(path):
    """Rasterize each SVG path as an independent normalized stroke layer."""
    result = []
    for node in ET.parse(path).getroot().iter("{http://www.w3.org/2000/svg}path"):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480">'
            + ET.tostring(node, encoding="unicode")
            + "</svg>"
        )
        png = cairosvg.svg2png(bytestring=svg.encode())
        result.append(np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))[:, :, 3] / 255.0)
    if not result:
        raise ValueError("No SVG stroke paths")
    return np.asarray(result)


def medial_path(mask, direction):
    """Return the longest endpoint geodesic, pruning short skeleton branches."""
    skeleton = skeletonize(mask)
    yy, xx = np.where(skeleton)
    if len(xx) < 2:
        if not mask.any():
            raise ValueError("Stroke too small for a path")
        my, mx = np.where(mask)
        center = np.array([mx.mean(), my.mean()])
        direction = np.asarray(direction, float)
        direction = direction / max(np.linalg.norm(direction), 1e-6)
        if not direction.any():
            direction = np.array([1.0, 0.0])
        return np.array([center - 0.5 * direction, center + 0.5 * direction])
    index = np.full(mask.shape, -1, int)
    index[yy, xx] = np.arange(len(xx))
    rows, cols, weights = [], [], []
    for dy, dx in [(0, 1), (1, -1), (1, 0), (1, 1)]:
        y, x = yy + dy, xx + dx
        valid = (y >= 0) & (y < mask.shape[0]) & (x >= 0) & (x < mask.shape[1])
        a = np.where(valid)[0]
        b = index[y[valid], x[valid]]
        a, b = a[b >= 0], b[b >= 0]
        rows.extend(a)
        cols.extend(b)
        weights.extend([np.hypot(dx, dy)] * len(a))
    graph = coo_matrix((weights, (rows, cols)), shape=(len(xx), len(xx))).tocsr()
    graph = graph + graph.T
    endpoints = np.where(np.diff(graph.indptr) == 1)[0]
    if len(endpoints) < 2:
        raise ValueError("Stroke skeleton has no unambiguous endpoints")
    distances = dijkstra(graph, indices=endpoints)
    candidates = distances[:, endpoints]
    candidates[~np.isfinite(candidates)] = -1
    a, b = np.unravel_index(candidates.argmax(), candidates.shape)
    start, end = endpoints[a], endpoints[b]
    _, previous = dijkstra(graph, indices=start, return_predecessors=True)
    route = [end]
    while route[-1] != start:
        route.append(int(previous[route[-1]]))
        if route[-1] < 0:
            raise ValueError("Disconnected skeleton")
    points = np.column_stack([xx[route], yy[route]]).astype(float)
    if np.dot(points[-1] - points[0], direction) < 0:
        points = points[::-1]
    return points


def resample(points, spacing=0.65):
    """Resample a polyline at approximately uniform arc-length spacing."""
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(arc) > 1e-6]
    arc, points = arc[keep], points[keep]
    if len(points) < 2:
        raise ValueError("Path has zero length")
    t = np.linspace(0, arc[-1], max(3, int(np.ceil(arc[-1] / spacing)) + 1))
    return np.column_stack([np.interp(t, arc, points[:, axis]) for axis in range(2)])


def fit_brush(layer, direction, guide=None):
    """Fit a centerline, pressure curve and timing to one stroke layer."""
    mask = layer > 0.5
    if guide is None:
        raw = medial_path(mask, direction)
    else:
        guide = np.asarray(guide, float)
        if (
            guide.ndim != 2
            or guide.shape[1] != 2
            or len(guide) < 2
            or not np.isfinite(guide).all()
        ):
            raise ValueError("Guide needs at least two finite [x,y] points")
        raw = resample(guide, 1.0)
    distance = ndi.distance_transform_edt(mask)
    raw = ndi.gaussian_filter1d(raw, 3, axis=0, mode="nearest")
    median_radius = float(np.median(ndi.map_coordinates(distance, raw.T[::-1], order=1)))
    delta = raw[-1] - raw[0]
    length = np.linalg.norm(delta)
    unit = delta / max(length, 1e-6)
    deviations = np.abs((raw - raw[0]) @ np.array([-unit[1], unit[0]]))
    straight = length > median_radius * 4 and np.quantile(deviations, 0.9) < max(
        4, median_radius * 0.55
    )
    if straight:
        path = resample(np.array([raw[0], raw[-1]]))
        kind = "straight"
    else:
        simplified = cv2.approxPolyDP(
            raw.astype(np.float32), max(2.5, median_radius * 0.18), False
        )[:, 0]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(simplified, axis=0), axis=1))]
        path = resample(PchipInterpolator(arc, simplified)(np.linspace(0, arc[-1], 300)))
        kind = "curved-or-turn"
    tangent = np.gradient(path, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
    normals = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    offsets = np.arange(-90.0, 90.25, 0.5)
    probes = path[:, None, :] + normals[:, None, :] * offsets[None, :, None]
    inside = ndi.map_coordinates(
        layer, probes.reshape(-1, 2).T[::-1], order=1, mode="constant"
    ).reshape(len(path), -1) > 0.5
    mid = len(offsets) // 2
    widths = []
    for row in inside:
        left = mid
        right = mid
        if not row[mid]:
            widths.append(1.0)
            continue
        while left > 0 and row[left - 1]:
            left -= 1
        while right < len(row) - 1 and row[right + 1]:
            right += 1
        widths.append(max(1.0, (offsets[right] - offsets[left]) / 2))
    local_radius = ndi.map_coordinates(distance, path.T[::-1], order=1, mode="nearest")
    widths = np.minimum(widths, np.maximum(local_radius * 1.12, 1.0))
    smooth = ndi.gaussian_filter1d(np.asarray(widths), max(2, 6 / 0.65), mode="nearest")
    knots = np.unique(
        np.r_[0, np.arange(12, len(path) - 12, max(12, int(len(path) / 12))), len(path) - 1]
    ).astype(int)
    radius = PchipInterpolator(knots, smooth[knots])(np.arange(len(path)))
    radius = np.maximum(radius, 0.7)
    end_ratio = radius[-1] / max(np.quantile(radius, 0.75), 1)
    tail = end_ratio < 0.62
    if tail:
        n = max(4, int(len(path) * 0.10))
        radius[-n:] *= np.linspace(1, 0.18, n) ** 0.7
    n = min(10, max(3, int(len(path) * 0.025)))
    curvature = np.linalg.norm(np.gradient(tangent, axis=0), axis=1)
    cost = 0.65 * (1 + 0.32 * radius / max(np.median(radius), 1) + 5 * curvature)
    cost[:n] *= 2.5
    cost[-n:] *= 1.8
    times = np.cumsum(cost)
    times = 0.085 + 0.89 * (times - times[0]) / max(times[-1] - times[0], 1e-6)
    press_path = np.repeat(path[:1], 7, axis=0)
    press_radius = radius[0] * np.linspace(0.12, 0.97, 7)
    path = np.vstack([press_path, path])
    radius = np.r_[press_radius, radius]
    times = np.r_[np.linspace(0.008, 0.075, 7), times]
    return {
        "kind": kind,
        "path": path.tolist(),
        "radius": radius.tolist(),
        "times": times.tolist(),
        "tail_lift": bool(tail),
        "nib_aspect": 0.55,
    }


class BrushPainter:
    """Persistent ink canvas; each footprint deposits ink once, including overlaps."""

    def __init__(self, stroke, size=SIZE, scale=SCALE):
        self.stroke = stroke
        self.size = size
        self.scale = scale
        self.canvas = np.zeros((size * scale, size * scale), np.uint8)
        self.cursor = 0
        self.path = np.asarray(stroke["path"])
        self.radius = np.asarray(stroke["radius"])
        self.times = np.asarray(stroke["times"])
        if (
            len(self.path) < 2
            or self.path.shape != (len(self.radius), 2)
            or len(self.times) != len(self.path)
        ):
            raise ValueError("Mismatched brush geometry")
        if (
            not all(np.isfinite(value).all() for value in [self.path, self.radius, self.times])
            or (self.radius <= 0).any()
            or (np.diff(self.times) < 0).any()
        ):
            raise ValueError("Invalid brush geometry")
        tangent = np.gradient(self.path, axis=0)
        moving = np.where(np.linalg.norm(tangent, axis=1) > 1e-6)[0]
        if not len(moving):
            raise ValueError("Stationary path has no direction")
        tangent[: moving[0]] = tangent[moving[0]]
        self.angles = np.degrees(np.arctan2(tangent[:, 1], tangent[:, 0]))

    def advance(self, progress):
        stop = np.searchsorted(self.times, np.clip(progress, 0, 1), side="right")
        if stop < self.cursor:
            raise ValueError("BrushPainter cannot move backwards; create a new painter")
        for k in range(self.cursor, stop):
            radius = self.radius[k] * self.scale
            center = tuple(self.path[k] * self.scale)
            aspect = self.stroke["nib_aspect"]
            if k < 12:
                aspect = 0.95 - (0.95 - aspect) * max(0, k - 7) / 5
            if not self.stroke["tail_lift"] and k > len(self.path) - 10:
                aspect += (0.95 - aspect) * (k - (len(self.path) - 10)) / 9
            axes = (max(0.8, radius * aspect), radius)
            angle = np.radians(self.angles[k])
            theta = np.linspace(0, 2 * np.pi, 48, endpoint=False)
            xy = np.column_stack([axes[0] * np.cos(theta), axes[1] * np.sin(theta)])
            rotation = np.array(
                [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
            )
            polygon = (xy @ rotation.T + center) * 16
            cv2.fillConvexPoly(
                self.canvas, np.round(polygon).astype(np.int32), 255, shift=4
            )
        self.cursor = stop
        return cv2.resize(
            self.canvas, (self.size, self.size), interpolation=cv2.INTER_AREA
        ).astype(np.float32) / 255


def complete(stroke):
    return BrushPainter(stroke).advance(1)


__all__ = [
    "BrushPainter",
    "PAPER",
    "SCALE",
    "SIZE",
    "complete",
    "fit_brush",
    "ink_image",
    "load_outlines",
    "medial_path",
    "resample",
]
