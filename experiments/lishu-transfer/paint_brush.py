"""Reconstruct existing lishu outlines with ordered pressure-controlled brush paths.

The SVG outlines initialize geometry only. Animation deposits overlapping elliptical
footprints; no source-mask clipping or whole-character replacement is used.
"""
from pathlib import Path
import argparse
import io
import json
import subprocess
import xml.etree.ElementTree as ET

import cairosvg
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parent
SIZE = 480
SCALE = 3
PAPER = (247, 245, 239)


def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)


def ink_image(ink, size):
    rgb = np.array(PAPER)[None, None, :] * (1-ink[..., None]) + 25*ink[..., None]
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).resize((size, size), Image.Resampling.LANCZOS)


def load_outlines(path):
    result = []
    for node in ET.parse(path).getroot().iter('{http://www.w3.org/2000/svg}path'):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480">' + ET.tostring(node, encoding='unicode') + '</svg>'
        png = cairosvg.svg2png(bytestring=svg.encode())
        result.append(np.asarray(Image.open(io.BytesIO(png)).convert('RGBA'))[:, :, 3]/255.)
    if not result:
        raise ValueError('No SVG stroke paths')
    return np.asarray(result)


def medial_path(mask, direction):
    """Longest endpoint geodesic prunes short skeleton branches from junction bulges."""
    skeleton = skeletonize(mask)
    yy, xx = np.where(skeleton)
    if len(xx) < 2:
        raise ValueError('Stroke too small for a path')
    index = np.full(mask.shape, -1, int)
    index[yy, xx] = np.arange(len(xx))
    rows, cols, weights = [], [], []
    for dy, dx in [(0, 1), (1, -1), (1, 0), (1, 1)]:
        y, x = yy+dy, xx+dx
        valid = (y >= 0) & (y < mask.shape[0]) & (x >= 0) & (x < mask.shape[1])
        a = np.where(valid)[0]
        b = index[y[valid], x[valid]]
        a, b = a[b >= 0], b[b >= 0]
        rows.extend(a); cols.extend(b); weights.extend([np.hypot(dx, dy)]*len(a))
    graph = coo_matrix((weights, (rows, cols)), shape=(len(xx), len(xx))).tocsr()
    graph = graph + graph.T
    endpoints = np.where(np.diff(graph.indptr) == 1)[0]
    if len(endpoints) < 2:
        raise ValueError('Stroke skeleton has no unambiguous endpoints')
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
            raise ValueError('Disconnected skeleton')
    points = np.column_stack([xx[route], yy[route]]).astype(float)
    if np.dot(points[-1]-points[0], direction) < 0:
        points = points[::-1]
    return points


def resample(points, spacing=.65):
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(arc) > 1e-6]
    arc, points = arc[keep], points[keep]
    if len(points) < 2:
        raise ValueError('Path has zero length')
    t = np.linspace(0, arc[-1], max(3, int(np.ceil(arc[-1]/spacing))+1))
    return np.column_stack([np.interp(t, arc, points[:, a]) for a in range(2)])


def fit_brush(layer, direction):
    mask = layer > .5
    raw = medial_path(mask, direction)
    distance = ndi.distance_transform_edt(mask)
    raw = ndi.gaussian_filter1d(raw, 3, axis=0, mode='nearest')
    median_radius = float(np.median(ndi.map_coordinates(distance, raw.T[::-1], order=1)))
    delta = raw[-1]-raw[0]
    length = np.linalg.norm(delta)
    unit = delta/max(length, 1e-6)
    deviations = np.abs((raw-raw[0]) @ np.array([-unit[1], unit[0]]))
    straight = length > median_radius*4 and np.quantile(deviations, .9) < max(4, median_radius*.55)
    if straight:
        # Keep endpoint direction, but remove centerline wobble entirely.
        path = resample(np.array([raw[0], raw[-1]]))
        kind = 'straight'
    else:
        # Few spatial knots remove skeleton stair steps while retaining real turns.
        simplified = cv2.approxPolyDP(raw.astype(np.float32), max(2.5, median_radius*.18), False)[:, 0]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(simplified, axis=0), axis=1))]
        path = resample(PchipInterpolator(arc, simplified)(np.linspace(0, arc[-1], 300)))
        kind = 'curved-or-turn'
    tangent = np.gradient(path, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
    normals = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    # Measure a contiguous cross-section around the path, never a distant stroke.
    offsets = np.arange(-90., 90.25, .5)
    probes = path[:, None, :] + normals[:, None, :]*offsets[None, :, None]
    inside = ndi.map_coordinates(layer, probes.reshape(-1, 2).T[::-1], order=1, mode='constant').reshape(len(path), -1) > .5
    mid = len(offsets)//2
    widths = []
    for row in inside:
        left = mid
        right = mid
        if not row[mid]:
            widths.append(1.)
            continue
        while left > 0 and row[left-1]: left -= 1
        while right < len(row)-1 and row[right+1]: right += 1
        widths.append(max(1., (offsets[right]-offsets[left])/2))
    # Low-frequency pressure curve: removes lumps, keeps terminal expansion.
    local_radius = ndi.map_coordinates(distance, path.T[::-1], order=1, mode='nearest')
    widths = np.minimum(widths, np.maximum(local_radius*1.12, 1.))
    smooth = ndi.gaussian_filter1d(np.asarray(widths), max(2, 6/.65), mode='nearest')
    knots = np.unique(np.r_[0, np.arange(12, len(path)-12, max(12, int(len(path)/12))), len(path)-1]).astype(int)
    radius = PchipInterpolator(knots, smooth[knots])(np.arange(len(path)))
    radius = np.maximum(radius, .7)
    # Broad pressing head and gradual lift. Terminal size follows the artwork;
    # a thin tail lifts, a broad ending deliberately retains a blunt finish.
    end_ratio = radius[-1]/max(np.quantile(radius, .75), 1)
    tail = end_ratio < .62
    if tail:
        n = max(4, int(len(path)*.10))
        radius[-n:] *= np.linspace(1, .18, n)**.7
    n = min(10, max(3, int(len(path)*.025)))
    # More time at initial pressure, heavy sections, and high-curvature turns.
    curvature = np.linalg.norm(np.gradient(tangent, axis=0), axis=1)
    cost = .65*(1 + .32*radius/max(np.median(radius), 1) + 5*curvature)
    cost[:n] *= 2.5
    cost[-n:] *= 1.8
    times = np.cumsum(cost); times = .085+.89*(times-times[0])/max(times[-1]-times[0], 1e-6)
    # Press in place before travelling; otherwise the stroke head is cut short.
    press_path = np.repeat(path[:1], 7, axis=0)
    press_radius = radius[0]*np.linspace(.12, .97, 7)
    path = np.vstack([press_path, path])
    radius = np.r_[press_radius, radius]
    times = np.r_[np.linspace(.008, .075, 7), times]
    return dict(kind=kind, path=path.tolist(), radius=radius.tolist(), times=times.tolist(),
                tail_lift=bool(tail), nib_aspect=.55)


class BrushPainter:
    """Persistent ink canvas; each footprint deposits ink once, including overlaps."""
    def __init__(self, stroke, size=SIZE, scale=SCALE):
        self.stroke = stroke
        self.size = size
        self.scale = scale
        self.canvas = np.zeros((size*scale, size*scale), np.uint8)
        self.cursor = 0
        self.path = np.asarray(stroke['path'])
        self.radius = np.asarray(stroke['radius'])
        self.times = np.asarray(stroke['times'])
        if len(self.path) < 2 or self.path.shape != (len(self.radius), 2) or len(self.times) != len(self.path):
            raise ValueError('Mismatched brush geometry')
        if not all(np.isfinite(x).all() for x in [self.path, self.radius, self.times]) or (self.radius <= 0).any() or (np.diff(self.times) < 0).any():
            raise ValueError('Invalid brush geometry')
        tangent = np.gradient(self.path, axis=0)
        moving = np.where(np.linalg.norm(tangent, axis=1) > 1e-6)[0]
        if not len(moving): raise ValueError('Stationary path has no direction')
        tangent[:moving[0]] = tangent[moving[0]]
        self.angles = np.degrees(np.arctan2(tangent[:, 1], tangent[:, 0]))

    def advance(self, progress):
        stop = np.searchsorted(self.times, np.clip(progress, 0, 1), side='right')
        if stop < self.cursor:
            raise ValueError('BrushPainter cannot move backwards; create a new painter')
        for k in range(self.cursor, stop):
            r = self.radius[k]*self.scale
            # Continuous subpixel ellipses avoid quantized radii / scalloped edges.
            center = tuple(self.path[k]*self.scale)
            aspect = self.stroke['nib_aspect']
            if k < 12:
                aspect = .95-(.95-aspect)*max(0,k-7)/5
            if not self.stroke['tail_lift'] and k > len(self.path)-10:
                aspect += (.95-aspect)*(k-(len(self.path)-10))/9
            axes = (max(.8, r*aspect), r)
            angle = np.radians(self.angles[k])
            t = np.linspace(0, 2*np.pi, 48, endpoint=False)
            xy = np.column_stack([axes[0]*np.cos(t), axes[1]*np.sin(t)])
            rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            polygon = (xy @ rotation.T + center)*16
            cv2.fillConvexPoly(self.canvas, np.round(polygon).astype(np.int32), 255, shift=4)
        self.cursor = stop
        return cv2.resize(self.canvas, (self.size, self.size), interpolation=cv2.INTER_AREA).astype(np.float32)/255


def complete(stroke):
    return BrushPainter(stroke).advance(1)


def render(rows, output):
    width, height, fps, step = 1440, 740, 30, .58
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{width}x{height}', '-framerate', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for row in rows:
            strokes = row['strokes']; painters = [BrushPainter(s) for s in strokes]
            union = np.zeros((SIZE, SIZE), np.float32)
            for f in range(int((len(strokes)*step+2.2)*fps)):
                elapsed = max(0, (f/fps-.5)/step)
                k = min(int(elapsed), len(strokes)-1)
                active = np.zeros_like(union)
                for i in range(k+1):
                    a = painters[i].advance(min(1, max(0, elapsed-i)))
                    union = np.maximum(union, a)
                    if i == k: active = a
                im = Image.new('RGB', (width, height), PAPER); d = ImageDraw.Draw(im)
                d.text((30, 20), 'LISHU / PRESSURE-CONTROLLED PAINT BRUSH', font=font(28), fill=(40,40,35))
                d.text((30, 65), f"{row['sheet'].upper()} / character {row['index']+1} / stroke {k+1}/{len(strokes)} / {strokes[k]['kind']}", font=font(20), fill=(120,90,50))
                for col, (label, ink) in enumerate([('PREVIOUS OUTLINE / REFERENCE', row['old'].max(0)), ('NEW BRUSH / LIVE PAINTING', union), ('ACTIVE STROKE / BRUSH PATH', active)]):
                    x = 30+480*col
                    d.text((x, 123), label, font=font(19), fill=(55,55,50))
                    im.paste(ink_image(ink, 420), (x, 165))
                pts = np.asarray(strokes[k]['path'])*420/SIZE + [990,165]
                d.line([tuple(p) for p in pts], fill=(175,105,60), width=2)
                painted = painters[k].cursor
                if painted:
                    x,y = pts[painted-1]; d.ellipse((x-4,y-4,x+4,y+4), fill=(180,65,45))
                d.text((30, 620), 'Straight shafts + smooth pressure + slower presses and turns + controlled lift.', font=font(22), fill=(65,65,55))
                d.text((30, 660), 'Ink is deposited by a moving elliptical tip. Complete crossing strokes overlap freely.', font=font(20), fill=(80,80,70))
                d.text((30, 701), 'Experimental reconstruction: shape changes are visible; brush paths and order remain inferred.', font=font(17), fill=(110,105,90))
                proc.stdin.write(im.tobytes())
            print('rendered', row['sheet'], row['char'], flush=True)
        proc.stdin.close()
        if proc.wait(): raise RuntimeError('ffmpeg failed')
    except BaseException:
        proc.kill(); proc.wait(); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT.parent/'stroke-ownership/ownership-characters.json').read_text())
    output = ROOT/'brush'; output.mkdir(exist_ok=True)
    rows = []; reports = []
    for sheet in ['reference', 'light']:
        for index, char in [(5,'清'), (6,'泉'), (7,'石')]:
            old = load_outlines(ROOT/'outlines'/f'{sheet}-{index:02}.svg')
            strokes = []
            for k, layer in enumerate(old):
                median = np.array(data[char]['medians'][k], float)
                direction = (median[-1]-median[0])*[1,-1]
                strokes.append(fit_brush(layer, direction))
            new = np.stack([complete(s) for s in strokes])
            a, b = new.max(0) > .5, old.max(0) > .5
            iou = float((a&b).sum()/(a|b).sum())
            record = dict(sheet=sheet, char=char, index=index, strokes=strokes)
            (output/f'{sheet}-{index:02}.json').write_text(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
            rows.append(dict(**record, old=old, new=new))
            reports.append(dict(sheet=sheet, char=char, silhouette_iou_to_previous_outline=iou,
                                straight_strokes=[k+1 for k,s in enumerate(strokes) if s['kind']=='straight']))
            print(sheet, char, 'IoU', round(iou, 3), flush=True)
    im = Image.new('RGB',(1440, 80+len(rows)*245),PAPER); d = ImageDraw.Draw(im)
    for col,label in enumerate(['PREVIOUS OUTLINE','BRUSH RECONSTRUCTION','FITTED BRUSH PATHS']):
        d.text((30+480*col, 22),label,font=font(23),fill=(45,45,40))
    for i,row in enumerate(rows):
        y = 80+i*245
        for col,a in enumerate([row['old'].max(0),row['new'].max(0),row['new'].max(0)*.22]):
            im.paste(ink_image(a,220),(120+480*col,y))
        for s in row['strokes']:
            pts = np.asarray(s['path'])*220/SIZE+[1080,y]
            d.line([tuple(p) for p in pts],fill=(170,85,45),width=2)
        d.text((20,y+210),f"{row['sheet']} / char {row['index']+1} / IoU {reports[i]['silhouette_iou_to_previous_outline']:.3f}",font=font(15),fill=(70,70,60))
    im.save(ROOT/'Lishu-Brush-Comparison.png')
    (output/'metrics.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    if args.video: render(rows, ROOT/'Lishu-Paint-Brush.mp4')


if __name__ == '__main__': main()
