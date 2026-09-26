"""Kaishu brush test for the requested Su Shi excerpt, with active stroke guides."""
from pathlib import Path
import argparse
import io
import json
import subprocess
import sys

import cairosvg
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'lishu-transfer'))
from paint_brush import fit_brush, BrushPainter, complete, ink_image, font, PAPER, SIZE

LINES=['人有悲歡離合','月有陰晴圓缺','此事古難全','但願人長久','千里共嬋娟']
PUNCTUATION=['，','，','。','，','。']
TEXT=''.join(LINES)
WORK=ROOT/'work'


def build():
    WORK.mkdir(exist_ok=True)
    data=json.loads((ROOT/'characters.json').read_text())
    report=[]
    for char in dict.fromkeys(TEXT):
        d=data[char];strokes=[];source=[]
        for outline,median in zip(d['strokes'],d['medians']):
            svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480"><g transform="scale(.46875) translate(0 900) scale(1 -1)"><path d="{outline}"/></g></svg>'
            png=cairosvg.svg2png(bytestring=svg.encode())
            layer=np.asarray(Image.open(io.BytesIO(png)).convert('RGBA'))[:,:,3]/255.
            points=np.asarray(median,float);points[:,1]=900-points[:,1];points*=.46875
            stroke=fit_brush(layer,points[-1]-points[0],guide=points)
            strokes.append(stroke);source.append(layer)
        paint=np.zeros((SIZE,SIZE),np.float32)
        contributions=[]
        for s in strokes:
            nxt=np.maximum(paint,complete(s));contributions.append(float((nxt-paint).sum()));paint=nxt
        target=np.max(source,axis=0)
        a,b=paint>.5,target>.5
        (WORK/f'{char}.json').write_text(json.dumps(strokes,ensure_ascii=False,separators=(',',':'))+'\n')
        np.savez_compressed(WORK/f'{char}.npz',paint=paint,target=target)
        report.append(dict(char=char,stroke_count=len(strokes),silhouette_iou=float((a&b).sum()/max((a|b).sum(),1)),
                           no_new_ink_strokes=[k+1 for k,v in enumerate(contributions) if v<.01]))
        print(char,len(strokes),round(report[-1]['silhouette_iou'],3),flush=True)
    (ROOT/'metrics.json').write_text(json.dumps(dict(text=TEXT,lines=[a+b for a,b in zip(LINES,PUNCTUATION)],
        source='Hanzi Writer Data 2.0.1 / Arphic regular-script stroke outlines and ordered medians',
        brush='Guided pressure-controlled deposition; solid ink; approximate reconstruction',characters=report),ensure_ascii=False,indent=2)+'\n')


def load():
    result={}
    for c in dict.fromkeys(TEXT):
        with np.load(WORK/f'{c}.npz') as z:
            result[c]=dict(strokes=json.loads((WORK/f'{c}.json').read_text()),paint=z['paint'],target=z['target'])
        result[c]['small']=ink_image(result[c]['paint'],132)
    return result


def locations():
    cells=[]
    for row,line in enumerate(LINES):
        left=(1080-(len(line)*132+30))//2
        for col,c in enumerate(line):cells.append((c,left+col*132,180+row*145,row,col))
    return cells


def punctuation(draw,row,last_x,y):
    # Small hand-drawn punctuation avoids relying on a CJK system font.
    px,py=last_x+138,y+103
    if PUNCTUATION[row]=='，':
        draw.ellipse((px,py,px+6,py+7),fill=(45,43,37));draw.line((px+5,py+5,px+1,py+14),fill=(45,43,37),width=2)
    else:draw.ellipse((px,py,px+9,py+9),outline=(45,43,37),width=2)


def backdrop():
    im=Image.new('RGB',(1080,1440),PAPER);d=ImageDraw.Draw(im)
    d.line((68,78,1012,78),fill=(200,185,158),width=1)
    d.text((70,99),'SU SHI  /  MID-AUTUMN VERSE',font=font(22),fill=(123,103,72))
    d.text((755,101),'KAISHU STUDY',font=font(18),fill=(123,103,72))
    d.line((68,937,1012,937),fill=(206,191,167),width=1)
    d.text((70,965),'CURRENT CHARACTER',font=font(19),fill=(120,102,75))
    d.text((650,965),'ACTIVE BRUSH STROKE',font=font(19),fill=(120,102,75))
    return im


def draw_poem(im,data,cells,index,current=None):
    d=ImageDraw.Draw(im)
    for q,(c,x,y,row,col) in enumerate(cells):
        if q>index:break
        image=ink_image(current,132) if q==index and current is not None else data[c]['small']
        im.paste(image,(x,y))
        if col==len(LINES[row])-1 and (q<index or current is None):punctuation(d,row,x,y)


def final_image(data,cells):
    im=backdrop();draw_poem(im,data,cells,len(cells))
    d=ImageDraw.Draw(im);d.rectangle((60,950,1020,1430),fill=PAPER)
    d.text((70,1000),'GUIDED BRUSH / COMPLETE POEM',font=font(23),fill=(115,94,62))
    d.text((70,1050),'27 characters, painted stroke by stroke.',font=font(22),fill=(90,85,74))
    d.text((70,1090),'Traditional characters and supplied line breaks preserved.',font=font(20),fill=(110,105,92))
    im.save(ROOT/'Kaishu-Poem-Final.png')


def render(data,cells):
    fps,step=30,.32
    output=ROOT/'Kaishu-Poem-Guided-Brush.mp4'
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','1080x1440','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
        '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    try:
        for j,(char,x,y,row,col) in enumerate(cells):
            glyph=data[char];strokes=glyph['strokes'];n=len(strokes)
            painters=[BrushPainter(s) for s in strokes];union=np.zeros((SIZE,SIZE),np.float32)
            duration=n*step+.38+(3 if j==len(cells)-1 else 0)
            for f in range(int(np.ceil(duration*fps))):
                elapsed=max(0,(f/fps-.12)/step);k=min(int(elapsed),n-1)
                for i in range(k+1):
                    active=painters[i].advance(min(1,max(0,elapsed-i)))
                    union=np.maximum(union,active)
                im=backdrop();draw_poem(im,data,cells,j,union)
                d=ImageDraw.Draw(im)
                done=elapsed>=n
                if done and col==len(LINES[row])-1:punctuation(d,row,x,y)
                im.paste(ink_image(union,330),(90,1002))
                im.paste(ink_image(active,330),(650,1002))
                if not done:
                    for size,origin in [(132,(x,y)),(330,(90,1002)),(330,(650,1002))]:
                        path=np.asarray(strokes[k]['path'])*size/SIZE+origin
                        d.line([tuple(p) for p in path],fill=(170,116,64),width=1 if size==132 else 2)
                        cursor=painters[k].cursor
                        if cursor:
                            px,py=path[cursor-1];r=2 if size==132 else 4
                            d.ellipse((px-r,py-r,px+r,py+r),fill=(160,63,43))
                d.text((70,1350),f'Character {j+1} / 27   |   Stroke {k+1} / {n}',font=font(21),fill=(110,93,65))
                d.text((70,1392),'Pressure-controlled ink  /  Active path in ochre',font=font(19),fill=(125,116,100))
                proc.stdin.write(im.tobytes())
            np.testing.assert_array_equal(union,glyph['paint'])
            print('video',j+1,char,flush=True)
        proc.stdin.close()
        if proc.wait():raise RuntimeError('ffmpeg failed')
    except BaseException:
        proc.kill();proc.wait();raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',action='store_true');p.add_argument('--reuse',action='store_true');a=p.parse_args()
    if not a.reuse:build()
    data=load();cells=locations();final_image(data,cells)
    if a.video:render(data,cells)


if __name__=='__main__':main()
