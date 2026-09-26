"""Editable, explicit path corrections layered over automatic stroke ribbons.

Control coordinates refer to the normalized target, not the original sheet.
Untouched glyphs retain the automatic method. Every layer is still constrained
to source ink, and max compositing still reconstructs that source exactly.
"""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator

from experiment import ROOT, TEXT, PAPER, extract_cells, ink_image, font
from smooth_strokes import (SIZE, registered_fields, ribbon_envelope,
                            rasterize_ribbon, assemble, frame, validate, smoothstep)


def load_controls(path):
    config=json.loads(path.read_text())
    if config.get('schema_version')!=1 or config.get('coordinate_size',0)<=0:
        raise ValueError('Unsupported controls schema or coordinate size')
    for sheet,chars in config['sheets'].items():
        if sheet not in ['reference','light']:raise ValueError('Unknown sheet')
        for char,strokes in chars.items():
            if char not in TEXT:raise ValueError('Unknown character')
            for key,record in strokes.items():
                if not key.isdigit() or int(key)<1:raise ValueError('Stroke indices are 1-based')
                points=np.asarray(record['points'],float)
                if points.ndim!=2 or points.shape[1]!=3 or len(points)<2:
                    raise ValueError('Controls need at least two [x,y,radius] points')
                if not np.isfinite(points).all() or (points[:,2]<=0).any():
                    raise ValueError('Controls must be finite with positive radii')
                if (points[:,:2]<0).any() or (points[:,:2]>=config['coordinate_size']).any():
                    raise ValueError('Control coordinates outside normalized canvas')
                if (np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1)<1e-4).any():
                    raise ValueError('Consecutive control points must be distinct')
                for junction in record.get('junctions',[]):
                    box=np.asarray(junction['box'],float)
                    if box.shape!=(4,) or not np.isfinite(box).all() or (box<0).any() or (box>config['coordinate_size']).any():
                        raise ValueError('Invalid junction box')
                    if box[0]>=box[2] or box[1]>=box[3]:raise ValueError('Empty junction box')
                    if not isinstance(junction['recipient'],int) or junction['recipient']<1 or junction['recipient']==int(key):
                        raise ValueError('Junction recipient must be a different stroke')
    return config


def controlled_envelope(record, coordinate_size, shape):
    controls=np.asarray(record['points'],float)
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(controls[:,:2],axis=0),axis=1))]
    parameter=np.linspace(0,distance[-1],160)
    path=PchipInterpolator(distance,controls[:,:2])(parameter)
    radius=PchipInterpolator(distance,controls[:,2])(parameter)
    return rasterize_ribbon(path,radius,(coordinate_size,coordinate_size),shape)


def corrected_decomposition(warped, phases, target, records, coordinate_size=480):
    if any(int(k)>len(warped) for k in records):
        raise ValueError('Correction refers to a nonexistent stroke')
    if any(j['recipient']>len(warped) for r in records.values() for j in r.get('junctions',[])):
        raise ValueError('Junction recipient refers to a nonexistent stroke')
    scores=[];progress=[];distances=[]
    for k,(support,phase) in enumerate(zip(warped,phases),start=1):
        if str(k) in records:
            mask,p=controlled_envelope(records[str(k)],coordinate_size,target.shape)
        else:
            mask,p=ribbon_envelope(support,phase,target.shape)
        sd=ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask)
        sd=ndi.gaussian_filter(sd,.7)
        distances.append(sd)
        scores.append(-np.logaddexp(0,-sd/.65));progress.append(p)
    scores=np.asarray(scores,np.float32)
    alpha=np.exp(scores-scores.max(0));alpha[alpha<1/255]=0
    layers=(alpha*target[None]).astype(np.float32)
    for key,record in records.items():
        k=int(key)-1
        # Coverage normalization can re-inflate a deliberately narrowed ribbon.
        # Pin its boundary only at explicitly annotated junctions, and transfer
        # clipped source ink to the named crossing stroke instead of dropping it.
        cap=smoothstep((distances[k]+.75)/1.5)
        for junction in record.get('junctions',[]):
            x0,y0,x1,y1=np.round(np.asarray(junction['box'])*np.array([target.shape[1],target.shape[0]]*2)/coordinate_size).astype(int)
            region=np.s_[y0:y1,x0:x1]
            previous=layers[k][region].copy()
            clipped=np.minimum(previous,(target*cap)[region])
            recipient=junction['recipient']-1
            changed=clipped<previous
            layers[recipient][region]=np.maximum(layers[recipient][region],np.where(changed,previous,0))
            layers[k][region]=clipped
    return assemble(layers,np.asarray(progress,np.float32),target)


def fragment_metrics(layers):
    """Diagnostic only: natural drybrush can produce genuine disconnected pieces."""
    rows=[]
    for k,layer in enumerate(layers):
        labels,n=ndi.label(layer>.5)
        sizes=np.bincount(labels.ravel());sizes[0]=0
        kept=sizes>=9
        count=int(kept.sum())
        largest=int(sizes.argmax()) if n else 0
        detached=float(layer[(labels!=largest)&kept[labels]].sum()) if n else 0
        rows.append({'stroke':k+1,'components_ge_9_pixels':count,'detached_core_ink':detached})
    return rows


def audit(samples, old, config):
    selected=[(name,TEXT.index(char),int(k)-1) for name,chars in config['sheets'].items()
              for char,records in chars.items() for k in records]
    width=1440;row_height=235
    image=Image.new('RGB',(width,80+row_height*len(selected)),PAPER);d=ImageDraw.Draw(image)
    for x,label in [(30,'Target / corrected stroke'),(510,'Automatic ribbon'),(990,'Edited ribbon')]:
        d.text((x,20),label,font=font(24),fill=(40,40,40))
    for row,(name,j,k) in enumerate(selected):
        s=samples[name][j];b=old[name][j];y=70+row*row_height
        for col,ink in enumerate([s['target'],b['layers'][k],s['layers'][k]]):
            image.paste(ink_image(ink,210),(120+col*480,y))
        d.text((35,y+208),f'{name} / character {j+1} / stroke {k+1}',font=font(15),fill=(70,70,65))
    image.save(ROOT/'Junction-Corrections-Audit.png')
    # A compact selection includes both improvements and a difficult junction.
    detail=Image.new('RGB',(1440,80+235*4),PAPER)
    detail.paste(image.crop((0,0,1440,80)),(0,0))
    for row,index in enumerate(range(min(4,len(selected)))):
        detail.paste(image.crop((0,70+index*235,1440,70+(index+1)*235)),(0,70+row*235))
    detail.save(ROOT/'Junction-Corrections-Detail.png')
    affected=sum(len(chars) for chars in config['sheets'].values())
    all_strokes=Image.new('RGB',(1440,70+affected*220),PAPER);d=ImageDraw.Draw(all_strokes)
    d.text((20,15),'Every stroke of affected glyphs: automatic above / corrected below (including receiving strokes)',font=font(20),fill=(40,40,40))
    row=0
    for name in ['reference','light']:
        for char in config['sheets'][name]:
            j=TEXT.index(char)
            for side,s in enumerate([old[name][j],samples[name][j]]):
                y=65+row*220+side*105
                all_strokes.paste(ink_image(s['target'],90),(15,y))
                for k,layer in enumerate(s['layers']):
                    x=115+k*108
                    all_strokes.paste(ink_image(layer,90),(x,y))
                    d.text((x,y+87),str(k+1),font=font(11),fill=(60,60,55))
            row+=1
    all_strokes.save(ROOT/'Junction-All-Strokes.png')


def render(samples, old, config):
    fps=30;step=.6;lead=.6;gap=.6;hold=1.2
    timeline=[];cursor=0
    correction_count=sum(len(strokes) for chars in config['sheets'].values() for strokes in chars.values())
    glyph_count=sum(len(chars) for chars in config['sheets'].values())
    for name in ['reference','light']:
        for char in config['sheets'][name]:
            j=TEXT.index(char);n=len(samples[name][j]['layers'])
            timeline.append((cursor,name,j));cursor+=lead+n*step+gap+hold
    w,h=1440,820
    out=ROOT/'Lishu-Junction-Refinement.mp4'
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-an',
        '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    try:
        for f in range(int(np.ceil(cursor*fps))):
            t=f/fps;start,name,j=max((s for s in timeline if s[0]<=t),key=lambda s:s[0])
            s=samples[name][j];b=old[name][j];n=len(s['layers'])
            elapsed=max(0,(t-start-lead)/step);k=min(int(elapsed),n-1)
            im=Image.new('RGB',(w,h),PAPER);d=ImageDraw.Draw(im)
            d.text((30,20),'LISHU / EDITABLE STROKE-BOUNDARY CORRECTIONS',font=font(28),fill=(40,40,40))
            changed=str(k+1) in config['sheets'][name].get(TEXT[j],{})
            d.text((30,66),f'{name.upper()} / character {j+1}/10 / stroke {k+1}/{n} / '+('EDITED PATH' if changed else 'AUTOMATIC PATH'),font=font(19),fill=(125,98,55))
            for col,label in enumerate(['AUTOMATIC RIBBONS','WITH TARGETED CORRECTIONS','ISOLATED CURRENT STROKE']):
                x=30+col*480;d.text((x,120),label,font=font(18),fill=(55,55,50))
                ink=[frame(b,elapsed),frame(s,elapsed),s['layers'][k]][col]
                im.paste(ink_image(ink,375),(x+30,158))
            for col in range(2):
                x=30+col*480
                ink=b['layers'][k] if col==0 else s['layers'][k]
                im.paste(ink_image(ink,140),(x+150,560))
                d.text((x+80,710),'Complete isolated stroke for inspection',font=font(16),fill=(100,100,90))
            im.paste(ink_image(s['target'],150),(1125,555))
            d.text((1110,715),'Target character',font=font(16),fill=(100,100,90))
            d.text((30,766),f'{correction_count} explicit path corrections across {glyph_count} glyphs. Source ink and full reconstruction are preserved.',font=font(19),fill=(70,70,60))
            d.text((30,795),'Corrections are authored for these samples; they are not a general automatic solution or verified historical ductus.',font=font(15),fill=(105,105,95))
            proc.stdin.write(im.tobytes())
            if f%900==0:print('video',round(t,1),'/',round(cursor,1),flush=True)
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('FFmpeg failed')
    except BaseException:
        proc.kill();proc.wait();raise
    return {'seconds':cursor,'fps':fps,'resolution':[w,h]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',action='store_true')
    args=parser.parse_args();config=load_controls(ROOT/'stroke-controls.json')
    work=ROOT/'work/refined';work.mkdir(parents=True,exist_ok=True)
    samples={};old={}
    report={'provenance':config['provenance'],'controls_sha256':hashlib.sha256((ROOT/'stroke-controls.json').read_bytes()).hexdigest(),
            'versions':{p:importlib.metadata.version(p) for p in ['numpy','scipy','Pillow','scikit-image','opencv-python-headless']},'samples':[]}
    for name,path in [('reference','target-lishu.png'),('light','target-lishu-light.png')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=config.get('source_sha256',{}).get(name):
            raise ValueError(f'Controls do not match the {name} source image')
        small=extract_cells(ROOT/path);samples[name]=[];old[name]=[]
        for j,(char,gray) in enumerate(zip(TEXT,small)):
            # Saved baseline is produced by smooth_strokes.py, so comparison
            # uses identical target pixels and the previous automatic result.
            baseline=ROOT/'work/smooth'/f'{name}-{j:02}.npz'
            if not baseline.exists():raise FileNotFoundError('Run smooth_strokes.py first')
            with np.load(baseline) as data:
                b=assemble(data['layers'],data['phase'],data['target'])
            records=config['sheets'][name].get(char,{})
            if records:
                warped,phase=registered_fields(gray,char)
                s=corrected_decomposition(warped,phase,b['target'],records,config['coordinate_size'])
            else:
                s=b
            check=validate(s)
            report['samples'].append({'sheet':name,'char':char,'index':j,'edited_strokes':sorted(map(int,records)),
                                     **check,'old_fragments':fragment_metrics(b['layers']),
                                     'new_fragments':fragment_metrics(s['layers'])})
            samples[name].append(s);old[name].append(b)
            np.savez_compressed(work/f'{name}-{j:02}.npz',layers=s['layers'],phase=s['phase'],target=s['target'])
            print(name,char,'edited',list(records),'error',check['max_reconstruction_error'],flush=True)
    audit(samples,old,config)
    (ROOT/'refinement-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.video:
        report['video']=render(samples,old,config)
        (ROOT/'refinement-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
