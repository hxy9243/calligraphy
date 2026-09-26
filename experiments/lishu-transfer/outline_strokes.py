"""Geometry-first experiment: periodic cubic outlines, no source-ink clipping.

Uses the previous refined decomposition as initialization, not as a final mask.
The largest component of each stroke is retained. Small detached marks and ink
texture are intentionally excluded in this geometry-only experiment.
"""
import argparse
import hashlib
import json
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline

from experiment import ROOT, TEXT, PAPER, font, ink_image
from smooth_strokes import assemble, frame


def fit_outline(layer, smoothing):
    contours, _ = cv2.findContours((layer > .35).astype('uint8'), cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError('Cannot fit an empty stroke')
    contour = max(contours, key=cv2.contourArea)[:, 0].astype(float)
    contour = np.vstack([contour, contour[0]])
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(contour, axis=0), axis=1))]
    if arc[-1] < 4:
        raise ValueError('Stroke is too small to fit')
    # Uniform arc-length samples make smoothing independent of contour direction.
    n = max(16, int(np.ceil(arc[-1])))
    t = np.arange(n) * arc[-1] / n
    points = np.column_stack([np.interp(t, arc, contour[:, a]) for a in range(2)])
    points = ndi.gaussian_filter1d(points, smoothing * n / arc[-1], axis=0, mode='wrap')
    count = max(8, int(np.ceil(arc[-1] / 12)))
    knot_t = np.linspace(0, n, count + 1)
    closed = np.vstack([points, points[0]])
    knots = np.column_stack([np.interp(knot_t, np.arange(n+1), closed[:, a]) for a in range(2)])
    spline = CubicSpline(knot_t, knots, bc_type='periodic')
    derivatives = spline(knot_t, 1)
    segments = []
    for i in range(count):
        dt = knot_t[i+1] - knot_t[i]
        segments.append([knots[i], knots[i]+derivatives[i]*dt/3,
                         knots[i+1]-derivatives[i+1]*dt/3, knots[i+1]])
    return np.asarray(segments)


def sample_outline(segments, count=16):
    t = np.linspace(0, 1, count, endpoint=False)[None, :, None]
    p = segments[:, :, None, :]
    return ((1-t)**3*p[:,0] + 3*(1-t)**2*t*p[:,1] +
            3*(1-t)*t*t*p[:,2] + t**3*p[:,3]).reshape(-1, 2)


def rasterize(segments, shape):
    scale = 3
    canvas = np.zeros((shape[0]*scale, shape[1]*scale), np.uint8)
    points = sample_outline(segments)
    cv2.fillPoly(canvas, [np.round(points*scale).astype(np.int32)], 255)
    return cv2.resize(canvas, (shape[1], shape[0]), interpolation=cv2.INTER_AREA).astype(np.float32)/255


def svg_path(segments):
    def xy(p): return f'{p[0]:.3f},{p[1]:.3f}'
    return 'M '+xy(segments[0,0])+' '+ ' '.join(
        'C '+' '.join(xy(p) for p in s[1:]) for s in segments)+' Z'


def metrics(layers, target):
    union = layers.max(0) > .5
    ink = target > .5
    return {'silhouette_iou': float((union & ink).sum()/max((union | ink).sum(),1)),
            'missing_ink_fraction': float((ink & ~union).sum()/max(ink.sum(),1)),
            'added_ink_fraction': float((union & ~ink).sum()/max(ink.sum(),1)),
            'mean_absolute_opacity_error': float(np.abs(layers.max(0)-target).mean())}


def decompose(old, smoothing):
    curves = [fit_outline(layer, smoothing) for layer in old['layers']]
    layers = np.asarray([rasterize(c, old['target'].shape) for c in curves])
    phases = []
    for original, phase in zip(old['layers'], old['phase']):
        # Extend the existing writing direction to newly filled outline pixels.
        nearest = ndi.distance_transform_edt(original <= .35, return_distances=False, return_indices=True)
        phases.append(phase[tuple(nearest)])
    return assemble(layers, np.asarray(phases), old['target']), curves


def validate_outline(sample):
    previous = frame(sample, 0)
    assert not previous.any()
    for t in np.linspace(0, len(sample['layers']), len(sample['layers'])*8+1):
        current = frame(sample, t)
        assert np.isfinite(current).all() and current.min() >= 0 and current.max() <= 1
        assert np.all(current+1e-7 >= previous)
        previous = current
    assert np.array_equal(previous, sample['layers'].max(0))
    assert (np.diff(sample['completed'], axis=0).sum((1,2)) > .01).all()


def audit(rows):
    im = Image.new('RGB', (1440, 80+len(rows)*260), PAPER)
    d = ImageDraw.Draw(im)
    labels = ['PREVIOUS', 'SMOOTH OUTLINES', 'OVERLAY', 'OLD STROKE', 'NEW STROKE']
    for col, label in enumerate(labels): d.text((col*288+18,20),label,font=font(19),fill=(40,40,40))
    for row, r in enumerate(rows):
        y = 70+row*260; old=r['old']; new=r['new']; k=r['focus']
        for col, a in [(0,old['target']),(1,new['completed'][-1]),(3,old['layers'][k]),(4,new['layers'][k])]:
            im.paste(ink_image(a,230),(col*288+25,y))
        overlay=ink_image(old['target']*.3,230).convert('RGB'); od=ImageDraw.Draw(overlay)
        for c in r['curves']:
            p=sample_outline(c)*230/480
            od.line([tuple(v) for v in np.vstack([p,p[0]])],fill=(180,65,45),width=1)
        im.paste(overlay,(601,y))
        d.text((25,y+230),f"{r['sheet']} / char {r['index']+1} / stroke {k+1} / IoU {r['metrics']['silhouette_iou']:.3f}",font=font(16),fill=(70,70,65))
    im.save(ROOT/'Outline-Comparison.png')
    all_im=Image.new('RGB',(1440,65+len(rows)*210),PAPER); d=ImageDraw.Draw(all_im)
    d.text((20,15),'Every stroke: previous above / explicit smooth outline below',font=font(23),fill=(40,40,40))
    for row,r in enumerate(rows):
        for side,s in enumerate([r['old'],r['new']]):
            y=60+row*210+side*100
            all_im.paste(ink_image(s['target'],85),(10,y))
            for k,layer in enumerate(s['layers']):
                x=110+k*105; all_im.paste(ink_image(layer,85),(x,y))
                d.text((x,y+82),str(k+1),font=font(12),fill=(65,65,60))
    all_im.save(ROOT/'Outline-All-Strokes.png')


def render(rows):
    w,h=1200,760; fps=24; step=.5
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
        '-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',
        str(ROOT/'Lishu-Smooth-Outlines.mp4')],stdin=subprocess.PIPE)
    try:
        for r in rows:
            n=len(r['new']['layers'])
            for f in range(int((n*step+2)*fps)):
                elapsed=max(0,(f/fps-.5)/step); k=min(int(elapsed),n-1)
                im=Image.new('RGB',(w,h),PAPER); d=ImageDraw.Draw(im)
                d.text((25,20),'LISHU / CLOSED BEZIER OUTLINE EXPERIMENT',font=font(26),fill=(40,40,40))
                d.text((25,65),f"{r['sheet'].upper()} / character {r['index']+1} / stroke {k+1}/{n} / silhouette IoU {r['metrics']['silhouette_iou']:.3f}",font=font(19),fill=(90,80,60))
                for col,(label,s) in enumerate([('PREVIOUS: PIXEL-EXACT',r['old']),('SMOOTH: GEOMETRY-FIRST',r['new'])]):
                    x=col*600+30
                    d.text((x,110),label,font=font(21),fill=(50,50,45))
                    im.paste(ink_image(frame(s,elapsed),360),(x+70,145))
                    im.paste(ink_image(s['layers'][k],170),(x+165,510))
                d.text((25,700),'Below: isolated current stroke. Smooth outlines overlap freely; no final-character replacement.',font=font(18),fill=(70,70,60))
                d.text((25,730),'Solid-ink geometry test: texture is omitted, and source reconstruction is approximate.',font=font(17),fill=(100,90,75))
                proc.stdin.write(im.tobytes())
            print('rendered',r['sheet'],r['index'],flush=True)
        proc.stdin.close()
        if proc.wait(): raise RuntimeError('ffmpeg failed')
    except BaseException:
        proc.kill(); proc.wait(); raise


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--video',action='store_true'); args=parser.parse_args()
    rows=[]; report=[]; output=ROOT/'outlines'; output.mkdir(exist_ok=True)
    for sheet in ['reference','light']:
        for char,focus in [('清',5),('泉',1),('石',1)]:
            j=TEXT.index(char); path=ROOT/'work/refined'/f'{sheet}-{j:02}.npz'
            with np.load(path) as z: old=assemble(z['layers'],z['phase'],z['target'])
            trials=[]
            for strength in [2.,4.,7.]:
                s,c=decompose(old,strength); m=metrics(s['layers'],s['target'])
                trials.append((strength,s,c,m))
            # Shared union constraint chooses the smoothest admissible candidate.
            # This is a coarse candidate search, not a joint control-point optimizer.
            eligible=[t for t in trials if t[3]['silhouette_iou']>=.94]
            chosen=eligible[-1] if eligible else max(trials,key=lambda t:t[3]['silhouette_iou'])
            strength,new,curves,m=chosen; validate_outline(new)
            r=dict(sheet=sheet,index=j,focus=focus,old=old,new=new,curves=curves,metrics=m); rows.append(r)
            paths='\n'.join(f'<path id="stroke-{k+1}" d="{svg_path(c)}"/>' for k,c in enumerate(curves))
            (output/f'{sheet}-{j:02}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 480"><g fill="#171715">{paths}</g></svg>\n')
            report.append(dict(sheet=sheet,char=char,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                selected_smoothing_pixels=strength,meets_iou_floor=bool(eligible),metrics=m,
                candidates=[dict(smoothing_pixels=t[0],**t[3]) for t in trials]))
    (ROOT/'outline-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    audit(rows)
    if args.video: render(rows)
    print(json.dumps([dict(sheet=r['sheet'],char=TEXT[r['index']],**r['metrics']) for r in rows],ensure_ascii=False,indent=2))


if __name__=='__main__': main()
