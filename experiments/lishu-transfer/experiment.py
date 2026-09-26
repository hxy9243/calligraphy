"""Reproduce the Kai -> generated Lishu registration experiment offline.

Run ownership_templates.mjs first. Artwork is committed; no generation API needed.
"""
from pathlib import Path
import argparse
import json
import hashlib
import importlib.metadata
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage.registration import optical_flow_tvl1

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'stroke-ownership'
sys.path.insert(0, str(BASE))
from ownership_prepare import process, template, S
from stroke_layers import compose_layers

TEXT = '明月松間照清泉石上流'
PAPER = (247, 245, 239)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def bbox(mask):
    y, x = np.where(mask)
    if not len(x):
        raise ValueError('Empty glyph or template')
    return x.min(), y.min(), x.max() + 1, y.max() + 1


def extract_cells(path, size=S):
    """2x5 sheet; move column cuts to nearby whitespace, preserve aspect ratio."""
    image = np.array(Image.open(path).convert('L'))
    height, width = image.shape
    result = []
    for row in range(2):
        band = image[round(row*height/2):round((row+1)*height/2)]
        projection = (band < 150).sum(0)
        cuts = [0]
        for col in range(1,5):
            expected = round(col*width/5)
            radius = round(width/5*.15)
            candidates = np.arange(expected-radius,expected+radius+1)
            blank = candidates[projection[candidates] == 0]
            if not len(blank):
                raise ValueError(f'No whitespace at row {row}, boundary {col}')
            cuts.append(int(blank[np.argmin(abs(blank-expected))]))
        cuts.append(width)
        for col in range(5):
            cell = band[:,cuts[col]:cuts[col+1]]
            ink = cell < 150
            if ink[0].any() or ink[-1].any() or ink[:, 0].any() or ink[:, -1].any():
                raise ValueError(f'Ink touches cell border at {row}, {col}')
            x0, y0, x1, y1 = bbox(ink)
            crop = cell[max(0,y0-2):y1+2, max(0,x0-2):x1+2]
            scale = (size*(S-20)/S)/max(crop.shape)
            small = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            canvas = np.full((size,size),255,np.uint8)
            oy, ox = (size-small.shape[0])//2, (size-small.shape[1])//2
            canvas[oy:oy+small.shape[0],ox:ox+small.shape[1]] = small
            result.append(canvas)
    return np.array(result)


def fit_template(layers, progress, ink):
    """Apply one shared anisotropic affine transform to masks AND progress."""
    sx0, sy0, sx1, sy1 = bbox(layers.max(0) > .5)
    tx0, ty0, tx1, ty1 = bbox(ink)
    yy, xx = np.mgrid[:S,:S]
    xs = (xx-tx0)*(sx1-sx0-1)/max(tx1-tx0-1,1) + sx0
    ys = (yy-ty0)*(sy1-sy0-1)/max(ty1-ty0-1,1) + sy0
    coords = np.array([ys,xs])
    fitted = np.stack([ndi.map_coordinates(a,coords,order=1,mode='constant') for a in layers])
    phase = np.stack([ndi.map_coordinates(a,coords,order=1,mode='nearest') for a in progress])
    return fitted, phase


def adapted(gray, char):
    layers, phase = template(char)
    target = (255-gray)/255.
    layers, phase = fit_template(layers, phase, gray < 150)
    flow = optical_flow_tvl1(ndi.gaussian_filter(target,1.5),
                            ndi.gaussian_filter(layers.max(0),1.5),
                            attachment=12,tightness=.3,num_warp=8,num_iter=12)
    yy, xx = np.mgrid[:S,:S]
    coords = np.array([yy+flow[0],xx+flow[1]])
    warped = np.stack([ndi.map_coordinates(a,coords,order=1,mode='constant') for a in layers])
    progress = np.stack([ndi.map_coordinates(a,coords,order=1,mode='nearest') for a in phase])
    support = np.stack([ndi.binary_dilation(a>.20,iterations=1) for a in warped])
    memberships, exposure, owner = compose_layers(support,progress,target>.20)
    original = target.astype(np.float32)
    retained = original*(owner>=0)
    return dict(original=original,retained=retained,owner=owner,
                memberships=memberships,exposure=exposure,n=len(layers),
                dropped=float(original[owner<0].sum()/max(original.sum(),1)),
                empty=[i+1 for i,a in enumerate(memberships) if not a.any()])


def reveal(sample, elapsed):
    return sample['retained'] * np.clip((elapsed-sample['exposure'])/.09,0,1)


def ink_image(ink, size):
    rgb = np.array(PAPER)[None,None,:]*(1-ink[...,None]) + 25*ink[...,None]
    return Image.fromarray(np.uint8(np.clip(rgb,0,255))).resize((size,size),Image.Resampling.LANCZOS)


def font(size):
    return ImageFont.truetype(FONT,size)


def validate(sample):
    accepted = sample['owner'] >= 0
    assert np.isfinite(sample['exposure'][accepted]).all()
    assert np.isinf(sample['exposure'][~accepted]).all()
    assert np.all(sample['retained'] <= sample['original'])
    assert np.array_equal(sample['memberships'].any(0), accepted)
    previous = reveal(sample,0)
    assert not previous.any()
    for t in np.linspace(0,sample['n']+1,2*sample['n']+3):
        current = reveal(sample,t)
        assert np.all(current>=previous)
        previous = current
    assert np.array_equal(previous,sample['retained'])


def audits(name, samples):
    # Each row is a character; left-to-right target, baseline, adapted, omitted,
    # and first-paint owner (color changes expose mistaken branch ownership).
    width = 1000
    im = Image.new('RGB',(width,100+10*175),PAPER)
    draw = ImageDraw.Draw(im)
    for i,label in enumerate(['Target','Main baseline','Aspect fit','Omitted (red)','First owner']):
        draw.text((i*200+12,20),label,font=font(19),fill=(40,40,40))
    palette = np.array([(31,119,180),(255,127,14),(44,160,44),(214,39,40),
                        (148,103,189),(140,86,75),(227,119,194),(127,127,127),
                        (188,189,34),(23,190,207),(80,40,140),(140,90,0)])
    for j,(a,b) in enumerate(zip(samples['baseline'],samples['aspect'])):
        y = 70+j*175
        for i,ink in enumerate([a['original'],a['retained'],b['retained']]):
            im.paste(ink_image(ink,150),(i*200+25,y))
        loss = b['original']-b['retained']
        rgb = np.array(ink_image(b['original'],S))
        rgb[loss>.2] = (220,40,40)
        im.paste(Image.fromarray(rgb).resize((150,150)),(625,y))
        rgb = np.full((S,S,3),255,np.uint8)
        valid = b['owner']>=0
        rgb[valid] = palette[b['owner'][valid]%len(palette)]
        im.paste(Image.fromarray(rgb).resize((150,150)),(825,y))
        draw.text((212,y+150),f"{100*(1-a['dropped']):.1f}% ink",font=font(14),fill=(50,50,50))
        draw.text((412,y+150),f"{100*(1-b['dropped']):.1f}% ink",font=font(14),fill=(50,50,50))
    im.save(ROOT/f'audit-{name}.png')
    # All stroke boundaries for selected difficult glyphs, both methods.
    selected = [1,3,5,6,8]
    contact = Image.new('RGB',(1300,80+len(selected)*240),PAPER)
    d = ImageDraw.Draw(contact)
    d.text((20,15),f'{name}: top row baseline / bottom row aspect fit; one frame per completed stroke',font=font(18),fill=(40,40,40))
    for row,j in enumerate(selected):
        for m,method in enumerate(['baseline','aspect']):
            sample = samples[method][j]
            for k in range(sample['n']):
                x,y = 20+k*100,70+row*240+m*115
                contact.paste(ink_image(reveal(sample,k+1),95),(x,y))
                d.text((x,y+95),f'{j+1}:{k+1}',font=font(12),fill=(70,70,70))
    contact.save(ROOT/f'strokes-{name}.png')


def render(all_samples, path, fps=24):
    step, gap, lead, hold = .30,.35,.8,3
    timeline=[]
    cursor=0.
    for name in ['reference','light']:
        for j,sample in enumerate(all_samples[name]['aspect']):
            duration=lead+sample['n']*step+gap
            timeline.append((cursor,cursor+duration,name,j))
            cursor+=duration
        cursor+=hold
    width,height=1440,900
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0','-an',
        '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
    try:
        for frame in range(int(np.ceil(cursor*fps))):
            t=frame/fps
            segment=max((s for s in timeline if s[0]<=t),key=lambda s:s[0])
            start,end,name,j=segment
            elapsed=max(0,(t-start-lead)/step)
            samples=all_samples[name]
            a,b=samples['baseline'][j],samples['aspect'][j]
            im=Image.new('RGB',(width,height),PAPER);d=ImageDraw.Draw(im)
            d.text((35,22),'KAI TO LISHU / SCRIPT TRANSFER EXPERIMENT',font=font(30),fill=(40,40,40))
            subtitle='A: reference-conditioned / heavier ink' if name=='reference' else 'B: text-only / lighter clerical forms'
            d.text((35,67),subtitle,font=font(21),fill=(115,95,64))
            for col,label in enumerate(['TARGET ARTWORK','UNCHANGED PIPELINE','ASPECT-FITTED TEMPLATE']):
                x=35+col*480
                d.text((x,124),label,font=font(20),fill=(65,65,60))
                ink=[a['original'],reveal(a,elapsed),reveal(b,elapsed)][col]
                im.paste(ink_image(ink,350),(x+32,165))
                if col:
                    s=[a,b][col-1]
                    d.text((x,535),f"Retained ink: {100*(1-s['dropped']):.1f}%",font=font(18),fill=(90,90,85))
                for k in range(10):
                    row,pos=divmod(k,5)
                    s=samples['baseline' if col<2 else 'aspect'][k]
                    ink=s['original'] if col==0 else s['retained'] if k<j else reveal(s,elapsed) if k==j else np.zeros((S,S))
                    im.paste(ink_image(ink,78),(x+pos*87,610+row*95))
            d.text((35,827),f'Character {j+1}/10  |  Stroke {min(int(elapsed)+1,b["n"])}/{b["n"]}  |  Shared intersections preserved',font=font(20),fill=(55,55,50))
            d.text((35,862),'Reconstruction from generated artwork. Retention is not stroke accuracy. No final whole-glyph reveal.',font=font(17),fill=(110,110,100))
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        if proc.wait()!=0:
            raise RuntimeError('FFmpeg failed')
    except BaseException:
        proc.kill();proc.wait();raise
    return {'duration_seconds':cursor,'fps':fps,'stroke_seconds':step,'resolution':[width,height]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',action='store_true')
    args=parser.parse_args()
    work=ROOT/'work';work.mkdir(exist_ok=True)
    glyphs={'kai':np.load(BASE/'glyphs.npz')['Yan'][10:20],
            'reference':extract_cells(ROOT/'target-lishu.png'),
            'light':extract_cells(ROOT/'target-lishu-light.png')}
    report={'text':TEXT,'samples':[],'summary':{},'metric_warning':'Ink retention is not ownership or historical stroke-order accuracy.',
            'versions':{p:importlib.metadata.version(p) for p in ['numpy','scipy','Pillow','scikit-image','opencv-python-headless']},
            'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'target-lishu.png',ROOT/'target-lishu-light.png',BASE/'glyphs.npz',BASE/'ownership-characters.json']}}
    all_samples={}
    for name,images in glyphs.items():
        methods={}
        for method,fn in [('baseline',process),('aspect',adapted)]:
            samples=[]
            for j,(char,gray) in enumerate(zip(TEXT,images)):
                s=fn(gray,char);validate(s);samples.append(s)
                np.savez_compressed(work/f'{name}-{method}-{j:02}.npz',**{k:v for k,v in s.items() if k!='empty'})
                record={'target':name,'method':method,'index':j,'char':char,
                        'retained_ink':1-s['dropped'],'empty_strokes':s['empty'],
                        'stroke_count':s['n'],
                        'no_first_paint_strokes':[k+1 for k in range(s['n']) if not (s['owner']==k).any()]}
                report['samples'].append(record)
                print(name,method,char,round(record['retained_ink']*100,2),s['empty'],flush=True)
            methods[method]=samples
            report['summary'][f'{name}/{method}']={
                'mean_retained_ink':float(np.mean([1-s['dropped'] for s in samples])),
                'worst_retained_ink':float(min(1-s['dropped'] for s in samples)),
                'empty_stroke_count':sum(len(s['empty']) for s in samples),
                'mean_ink_bbox_width_height':float(np.mean([(lambda b:(b[2]-b[0])/(b[3]-b[1]))(bbox(im<150)) for im in images]))}
        all_samples[name]=methods
        audits(name,methods)
    (ROOT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.video:
        report['video']=render(all_samples,ROOT/'Lishu-Transfer-Comparison.mp4')
    (ROOT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':
    main()
