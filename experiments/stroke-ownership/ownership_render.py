"""Side-by-side study: 40 characters, 3 artist-inspired images, same timing."""
from pathlib import Path
import json, subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from ownership_prepare import TEXT,DATA
R=Path(__file__).parent; W=R/'ownership-work'
STYLES=['Yan','Liu','Zhao']
samples={s:[dict(np.load(W/f'{s}-{i:02}.npz')) for i in range(40)] for s in STYLES}
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(size):return ImageFont.truetype(fontpath,size)
paper=(247,245,239); dark=(42,43,39);muted=(109,109,100);gold=(157,119,59)
def ink_image(a,size):
    rgb=np.array(paper)[None,None,:]*(1-a[...,None])+np.array((28,29,27))[None,None,:]*a[...,None]
    return Image.fromarray(np.uint8(np.clip(rgb,0,255))).resize((size,size),Image.Resampling.LANCZOS)

base=Image.new('RGB',(1920,1080),paper);d=ImageDraw.Draw(base)
d.text((55,27),'AUTUMN EVENING IN THE MOUNTAINS',font=font(32),fill=dark)
d.text((57,74),'Wang Wei  /  40 characters  /  stroke layers with preserved overlaps  /  3x writing speed',font=font(19),fill=muted)
for si,s in enumerate(STYLES):
    x=55+si*640
    d.text((x,125),s.upper()+'-INSPIRED',font=font(25),fill=gold)
    d.text((x,162),'Separate stroke shapes; shared junctions retained',font=font(17),fill=muted)
    if si<2:d.line((x+603,124,x+603,1020),fill=(216,213,205),width=1)
    d.line((x,505,x+575,505),fill=(216,213,205),width=1)
    d.text((x,522),'POEM PROGRESS  /  READ ROWS LEFT TO RIGHT',font=font(15),fill=muted)
d.text((55,1042),'Artist-inspired study. Ink at intersections appears as the first participating stroke reaches it.',font=font(17),fill=muted)

step=.16  # 0.48 sec/stroke reference cadence divided by 3.
gap=.28
starts=[];cursor=.8
for char in TEXT:
    starts.append(cursor);cursor+=len(DATA[char]['strokes'])*step+gap
finish=cursor;duration=finish+5
out=R/'Stroke-Ownership-Preserved-Overlaps.mp4'
proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
last_index=-1;completed=base.copy()
for f in range(int(np.ceil(duration*30))):
    t=f/30
    j=max(0,min(39,int(np.searchsorted(starts,t,side='right')-1)))
    if j!=last_index:
        if last_index>=0:
            for si,s in enumerate(STYLES):
                row,col=divmod(last_index,5)
                completed.paste(ink_image(samples[s][last_index]['retained'],57),(100+si*640+col*100,557+row*59))
        last_index=j
    im=completed.copy();draw=ImageDraw.Draw(im)
    elapsed=max(0,(t-starts[j])/step)
    n=len(DATA[TEXT[j]]['strokes'])
    for si,s in enumerate(STYLES):
        a=samples[s][j]
        alpha=np.clip((elapsed-a['exposure'])/.09,0,1)
        active=a['retained']*alpha
        im.paste(ink_image(active,292),(195+si*640,199))
        row,col=divmod(j,5)
        px=100+si*640+col*100;py=557+row*59
        im.paste(ink_image(active,57),(px,py))
        draw.rectangle((px-4,py-2,px+61,py+58),outline=gold,width=1)
        label=f'Character {j+1:02}/40   |   Stroke {min(n,int(elapsed)+1):02}/{n:02}'
        if t>=finish:label='Completed  |  5-second hold'
        draw.text((140+si*640,484),label,font=font(17),fill=muted)
    draw.rectangle((55,1025,1860,1028),fill=(223,219,210))
    draw.rectangle((55,1025,55+int(1805*min(t/finish,1)),1028),fill=gold)
    proc.stdin.write(im.tobytes())
    if f in [45,180,900,int(np.ceil(duration*30))-1]: im.save(W/f'video-check-{f}.jpg')
    if f%600==0:print('render',round(t,1),'/',round(duration,1),flush=True)
proc.stdin.close();assert proc.wait()==0
(W/'timing.json').write_text(json.dumps({'duration':duration,'writing_end':finish,'stroke_interval':step,'starts':starts},indent=2))
print(out,flush=True)

# A compact static audit keeps the omitted intersections easy to inspect.
chosen=[2,11,16,22,25,30]
sheet=Image.new('RGB',(1560,1120),paper);dr=ImageDraw.Draw(sheet)
dr.text((35,22),'STROKE OWNERSHIP / JUNCTION AUDIT',font=font(30),fill=dark)
dr.text((35,67),'Each pair: original artwork (left), overlap-preserving stroke layers (right).',font=font(20),fill=muted)
for si,s in enumerate(STYLES):
    y=125+si*325
    dr.text((35,y),s.upper()+'-INSPIRED',font=font(22),fill=gold)
    for k,j in enumerate(chosen):
        a=samples[s][j];x=20+k*256
        sheet.paste(ink_image(a['original'],124),(x,y+45))
        sheet.paste(ink_image(a['retained'],124),(x+125,y+45))
        dr.text((x+15,y+187),f"Omitted ink: {float(a['dropped'])*100:.1f}%",font=font(17),fill=muted)
dr.text((35,1080),'Artist-inspired generated samples. Stroke ownership remains an estimate that needs visual review.',font=font(18),fill=muted)
sheet.save(R/'Stroke-Ownership-Overlap-Audit.png')
