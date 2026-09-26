"""Apply the lishu guided brush reconstruction to the 40-character Kai study."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'lishu-transfer'))
from paint_brush import BrushPainter, fit_brush, complete, font, ink_image, PAPER, SIZE
from smooth_strokes import registered_fields, smooth_decomposition
from outline_strokes import fit_outline, rasterize
from ownership_prepare import TEXT, DATA

STYLES = ['Yan', 'Liu', 'Zhao']
OUT = ROOT/'brush-work'


def build(resume=False):
    OUT.mkdir(exist_ok=True)
    inputs = np.load(ROOT/'glyphs.npz')
    summary = []
    for style in STYLES:
        for j, (char, gray) in enumerate(zip(TEXT, inputs[style])):
            cache=OUT/f'{style}-{j:02}.json'
            if resume and cache.exists() and (OUT/f'{style}-{j:02}.npz').exists():
                row=load(style,j);strokes=row['strokes'];target=row['target'];union=row['paint']
                contributions=[];previous=np.zeros_like(union)
                for stroke in strokes:
                    nxt=np.maximum(previous,complete(stroke));contributions.append(float((nxt-previous).sum()));previous=nxt
            else:
                warped, phase = registered_fields(gray, char)
                target = cv2.resize((255-gray)/255., (SIZE,SIZE), interpolation=cv2.INTER_CUBIC).clip(0,1).astype('float32')
                layers, _, _ = smooth_decomposition(warped, phase, target)
                strokes = []
                for k, layer in enumerate(layers):
                    # Same outline initialization as lishu, at a fixed moderate smoothing.
                    outline = rasterize(fit_outline(layer, 4), target.shape)
                    median = np.asarray(DATA[char]['medians'][k], float)
                    direction = (median[-1]-median[0])*[1,-1]
                    strokes.append(fit_brush(outline, direction))
                union = np.zeros_like(target)
                contributions = []
                for stroke in strokes:
                    ink = complete(stroke)
                    next_union = np.maximum(union,ink)
                    contributions.append(float((next_union-union).sum()))
                    union = next_union
            a,b = union>.5,target>.5
            record = dict(style=style,index=j,char=char,strokes=strokes)
            (OUT/f'{style}-{j:02}.json').write_text(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
            np.savez_compressed(OUT/f'{style}-{j:02}.npz',target=target,paint=union)
            summary.append(dict(style=style,index=j,char=char,strokes=len(strokes),
                                input_pixels_sha256=hashlib.sha256(gray.tobytes()).hexdigest(),
                                silhouette_iou=float((a&b).sum()/max((a|b).sum(),1)),
                                straight_strokes=sum(s['kind']=='straight' for s in strokes),
                                no_new_ink_strokes=[k+1 for k,v in enumerate(contributions) if v<.01]))
            print(style,j,char,round(summary[-1]['silhouette_iou'],3),flush=True)
    (ROOT/'kai-brush-metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')


def load(style,j):
    row = json.loads((OUT/f'{style}-{j:02}.json').read_text())
    with np.load(OUT/f'{style}-{j:02}.npz') as a:
        row.update(target=a['target'],paint=a['paint'])
    return row


def audit():
    # Same characters as the lishu trial; no selection by output score.
    im=Image.new('RGB',(1440,1000),PAPER); d=ImageDraw.Draw(im)
    d.text((25,15),'KAI / SAME GUIDED BRUSH RULES ACROSS THREE STYLES',font=font(27),fill=(40,40,35))
    for col,style in enumerate(STYLES):
        x=col*480
        d.text((x+25,65),style.upper()+'-INSPIRED',font=font(22),fill=(115,85,50))
        d.text((x+20,100),'Source              Brush              Path',font=font(18),fill=(75,75,65))
        for line,j in enumerate([15,16,17]):
            row=load(style,j);y=145+line*275
            for k,ink in enumerate([row['target'],row['paint'],row['paint']*.2]):
                im.paste(ink_image(ink,150),(x+k*160,y))
            for s in row['strokes']:
                p=np.asarray(s['path'])*150/SIZE+[x+320,y]
                d.line([tuple(v) for v in p],fill=(170,90,45),width=1)
            d.text((x+20,y+175),f"Character {j+1}: {len(row['strokes'])} ordered strokes",font=font(17),fill=(90,90,75))
    d.text((25,962),'Generated style interpretations. Geometry/pressure are inferred; artwork is not reproduced exactly.',font=font(19),fill=(90,90,75))
    im.save(ROOT/'Kai-Guided-Brush-Comparison.png')


def render():
    w,h,fps,step=1440,1080,30,.26
    all_rows={style:[load(style,j) for j in range(len(TEXT))] for style in STYLES}
    thumbnails={style:[ink_image(row['paint'],73) for row in all_rows[style]] for style in STYLES}
    output=ROOT/'Kai-Guided-Brush.mp4'
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
        '-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    try:
        for j,char in enumerate(TEXT):
            rows=[all_rows[s][j] for s in STYLES]
            n=len(rows[0]['strokes'])
            painters=[[BrushPainter(s) for s in row['strokes']] for row in rows]
            unions=[np.zeros((SIZE,SIZE),np.float32) for _ in rows]
            seconds=n*step+.5+(3 if j==len(TEXT)-1 else 0)
            for f in range(int(np.ceil(seconds*fps))):
                elapsed=max(0,(f/fps-.16)/step);k=min(int(elapsed),n-1)
                im=Image.new('RGB',(w,h),PAPER);d=ImageDraw.Draw(im)
                d.text((25,15),'KAI / GUIDED PAINT BRUSH',font=font(27),fill=(40,40,35))
                d.text((800,22),f'Character {j+1}/40  |  Stroke {k+1}/{n}',font=font(20),fill=(115,85,50))
                for col,(style,row) in enumerate(zip(STYLES,rows)):
                    x=col*480
                    d.text((x+25,64),style.upper()+'-INSPIRED',font=font(22),fill=(115,85,50))
                    for i in range(k+1):
                        a=painters[col][i].advance(min(1,max(0,elapsed-i)))
                        unions[col]=np.maximum(unions[col],a)
                    im.paste(ink_image(unions[col],295),(x+10,104))
                    # Only the active guide is overlaid; completed ink stays untouched.
                    p=np.asarray(row['strokes'][k]['path'])*295/SIZE+[x+10,104]
                    d.line([tuple(v) for v in p],fill=(178,105,60),width=1)
                    cursor=painters[col][k].cursor
                    if cursor:
                        px,py=p[cursor-1];d.ellipse((px-3,py-3,px+3,py+3),fill=(175,65,40))
                    im.paste(ink_image(row['target'],145),(x+315,155))
                    d.text((x+335,312),'SOURCE',font=font(15),fill=(100,100,85))
                    for q in range(j+1):
                        rr,cc=divmod(q,5)
                        thumbnail=thumbnails[style][q] if q<j else ink_image(unions[col],73)
                        im.paste(thumbnail,(x+30+cc*84,420+rr*77))
                d.text((25,1045),'Moving tip + smooth pressure + preserved overlap. Source art and writing paths are inferred.',font=font(18),fill=(95,95,80))
                proc.stdin.write(im.tobytes())
            print('video',j+1,'/40',flush=True)
        proc.stdin.close()
        if proc.wait():raise RuntimeError('ffmpeg failed')
    except BaseException:
        proc.kill();proc.wait();raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',action='store_true')
    p.add_argument('--reuse',action='store_true',help='Use existing brush-work outputs')
    p.add_argument('--resume',action='store_true',help='Continue an interrupted build using existing glyphs')
    a=p.parse_args()
    if not a.reuse: build(resume=a.resume)
    audit()
    if a.video:render()


if __name__=='__main__':main()
