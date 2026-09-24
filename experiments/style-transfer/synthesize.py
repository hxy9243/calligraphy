"""Generate and animate new 永 from known stroke topology and a Kai scan's style statistics.

One exemplar is insufficient to learn the writer's full style. This transfers
ink density, optical weight and sampled texture, retaining the target's known
geometry; it is a visible baseline for future annotation-driven style learning.
"""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
KAI=ROOT/'experiments'/'kai-four'
sys.path.insert(0,str(KAI))
import render as base
import mask_warp as warp

SIZE=512
FPS=24
DURATION=8
STYLE_INDEX=1  # Yan Zhenqing comparison scan
STROKE_DATA=ROOT/'data'/'yong.json'
OUT=HERE/'yan-inspired-yong.mp4'


def style_measure(index):
    crop=np.asarray(Image.open(base.SOURCE).convert('L'))
    x0,y0,x1,y1,bright,threshold=base.ROIS[index]
    source=crop[y0:y1,x0:x1]
    ink=base.ink_mask(source,bright,threshold)
    reference=np.asarray(Image.open(base.TEMPLATE).convert('L'))<100
    density=float(ink.mean()/reference.mean())
    return source,ink,density,bright,threshold


def create_masks(density):
    data=json.loads(STROKE_DATA.read_text())
    raw=[np.asarray(Image.open(HERE/'strokes-永'/f'{i:02d}.png').convert('RGBA'))[:,:,3]>120 for i in range(len(data['strokes']))]
    original=np.any(np.stack(raw),axis=0)
    target=min(.34,original.mean()*density)
    # Search one signed-distance offset shared by all strokes. The output's
    # union ink coverage matches the exemplar's relative visual weight.
    signed=[ndi.distance_transform_edt(~m)-ndi.distance_transform_edt(m) for m in raw]
    lo,hi=-5.0,8.0
    for _ in range(18):
        mid=(lo+hi)/2
        fraction=np.any(np.stack([d<=mid for d in signed]),axis=0).mean()
        if fraction<target:lo=mid
        else:hi=mid
    offset=(lo+hi)/2
    rng=np.random.default_rng(42)
    rough=ndi.gaussian_filter(rng.normal(size=(SIZE,SIZE)),2.2)
    rough/=max(rough.std(),1e-4)
    rough=rough.clip(-2,2)*.55
    masks=[d<=offset+rough for d in signed]
    return data,masks,{"relative_ink_density":round(density,3),"width_offset_px":round(offset,2),
                       "target_ink_fraction":round(float(target),3),"achieved_ink_fraction":round(float(np.any(np.stack(masks),axis=0).mean()),3)}


def make_ink(source, bright, threshold):
    """Reuse the source's scanned luminance distribution as ink grain."""
    rng=np.random.default_rng(23)
    h,w=source.shape
    # Sampling a gently shifted source tile preserves dark/light grain without
    # copying the exemplar's recognizable 書 silhouette into the new 永.
    noise=ndi.gaussian_filter(rng.normal(size=(SIZE,SIZE)),2.4)
    noise/=max(noise.std(),1e-3)
    paper=np.array([246,240,224],np.float32)[None,None,:]+rng.normal(0,1.7,(SIZE,SIZE,1))
    strength=(source[base.ink_mask(source,bright,threshold)]-threshold)/(245-threshold) if bright else (threshold-source[base.ink_mask(source,bright,threshold)])/threshold
    average=float(np.clip(np.mean(strength),0.12,0.95))
    alpha=np.clip(.86+.025*noise+(.04*average),.76,.97)
    dark=np.array([48,42,36],np.float32)[None,None,:]
    ink=paper*(1-alpha[:,:,None])+dark*alpha[:,:,None]
    return np.uint8(np.clip(paper,0,255)),np.uint8(np.clip(ink,0,255))


def sweep_mask(mask,path,phase):
    if phase<=0:return np.zeros(mask.shape,bool)
    if phase>=1:return mask
    count=max(2,int(len(path)*phase))
    thick=ndi.distance_transform_edt(mask)
    sweep=Image.new('L',(SIZE,SIZE));draw=ImageDraw.Draw(sweep)
    for x,y in path[:count]:
        if 0<=x<SIZE and 0<=y<SIZE:
            radius=max(6,2.1*thick[int(y),int(x)])
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    return mask & (np.asarray(sweep)>0)


def stroke_paths(data):
    paths=[]
    for median in data['medians']:
        points=np.array([[x*SIZE/1024,(900-y)*SIZE/1024] for x,y in median],np.float32)
        paths.append(warp.smooth_path(points))
    return paths


def compose(character,reference,title):
    canvas=Image.new('RGB',(1000,740),(247,242,231));draw=ImageDraw.Draw(canvas)
    heading=ImageFont.truetype(base.FONT,28);label=ImageFont.truetype(base.FONT,18)
    draw.text((66,36),'STYLE TRANSFER STUDY / KAI',font=heading,fill='#473f37')
    draw.text((66,82),title,font=label,fill='#776c5c')
    draw.line((66,117,934,117),fill='#cbbda9',width=2)
    draw.text((66,144),'REFERENCE  ·  SHU',font=label,fill='#706659')
    draw.text((550,144),'GENERATED  ·  YONG',font=label,fill='#706659')
    draw.rectangle((66,181,450,565),fill='#f7f1e3')
    draw.rectangle((550,181,934,565),fill='#f7f1e3')
    canvas.paste(reference.resize((360,360),Image.Resampling.BICUBIC),(78,193))
    canvas.paste(character.resize((360,360),Image.Resampling.BICUBIC),(562,193))
    draw.line((66,610,934,610),fill='#cbbda9',width=2)
    draw.text((67,640),'KNOWN TARGET STROKES  ·  EXAMPLE-BASED WEIGHT + TEXTURE  ·  NOT AN AUTHENTIC YAN GLYPH',font=label,fill='#786d5c')
    return canvas


def render():
    source,src_ink,density,bright,threshold=style_measure(STYLE_INDEX)
    data,masks,diagnostics=create_masks(density)
    paper,ink_rgb=make_ink(source,bright,threshold)
    background=np.asarray(paper)
    paths=stroke_paths(data)
    x0,y0,x1,y1,_,_=base.ROIS[STYLE_INDEX]
    # Reference display: invert light-on-dark photocopy, then give it ink tone.
    reference_gray=np.asarray(Image.open(base.SOURCE).convert('L'))[y0:y1,x0:x1]
    ref_ink=base.ink_mask(reference_gray,bright,threshold)
    ref_rgb=np.full((*ref_ink.shape,3),[247,241,228],np.uint8)
    ref_rgb[ref_ink]=[55,47,40]
    reference=Image.fromarray(ref_rgb)
    final=np.any(np.stack(masks),axis=0)
    final_tile=Image.fromarray(np.where(final[:,:,None],ink_rgb,background))
    compose(final_tile,reference,'Yan Zhenqing scan -> style cues -> ordered YONG geometry').save(HERE/'yan-inspired-yong.png')
    ffmpeg=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1000x740',
         '-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-movflags','+faststart',str(OUT)],stdin=subprocess.PIPE)
    try:
        for frame in range(DURATION*FPS):
            t=frame/FPS
            visible=np.zeros((SIZE,SIZE),bool)
            for i,(mask,path) in enumerate(zip(masks,paths)):
                phase=np.clip((t-.75-i*1.08)/.88,0,1)
                visible|=sweep_mask(mask,path,phase)
            tile=Image.fromarray(np.where(visible[:,:,None],ink_rgb,background))
            image=compose(tile,reference,'Yan Zhenqing scan -> style cues -> ordered YONG geometry')
            ffmpeg.stdin.write(image.tobytes())
    finally:
        ffmpeg.stdin.close()
        if ffmpeg.wait():raise RuntimeError('FFmpeg encode failed')
    diagnostics.update({"source":"Yan Zhenqing 書 scan","target":"永","target_stroke_count":len(masks),
       "source_ink_fraction":round(float(src_ink.mean()),3),"method":"stroke outlines + global width + rough edge + source ink-tone stats"})
    (HERE/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    print(json.dumps(diagnostics,indent=2));print(f'Wrote {OUT}')


if __name__=='__main__':render()
