"""Render the Liu-inspired gesture experiment and its unchanged baseline."""
from pathlib import Path
import argparse,json,subprocess,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from brush_grammar import ContactBrush,complete,fit_strokes,sample
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'lishu-transfer'))
from paint_brush import BrushPainter
PAPER=(247,243,234)
def font(size):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)
def patch(ink,size=420):
 a=np.clip(ink,0,1)[...,None];return Image.fromarray(np.uint8(np.array(PAPER)*(1-a)+np.array([27,26,23])*a)).resize((size,size),Image.Resampling.LANCZOS)
def union(strokes):return np.maximum.reduce([complete(s) for s in strokes])
def iou(a,b):
 a,b=a>.5,b>.5;return float((a&b).sum()/max((a|b).sum(),1))
def load():
 controls=json.loads((ROOT/'fitted-controls.json').read_text());rows=[]
 for c,strokes in controls.items():
  z=np.load(ROOT/'fixtures'/f'{c}.npz');rows.append(dict(char=c,strokes=strokes,target=z['target'],baseline=z['baseline'],new=union(strokes),old_strokes=json.loads((ROOT/'fixtures'/f'{c}-baseline.json').read_text())))
 return rows

def build():
 controls=json.loads((ROOT/'controls.json').read_text());fitted={};metrics=[]
 for c,strokes in controls.items():
  z=np.load(ROOT/'fixtures'/f'{c}.npz');print('fitting',c,flush=True)
  new,reports=fit_strokes(strokes,z['target']);fitted[c]=new
  row=dict(char=c,baseline_iou=iou(z['baseline'],z['target']),authored_iou=iou(union(strokes),z['target']),fitted_iou=iou(union(new),z['target']),fit=reports)
  metrics.append(row);print({k:v for k,v in row.items() if k!='fit'},flush=True)
 (ROOT/'fitted-controls.json').write_text(json.dumps(fitted,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')

def still(rows):
 im=Image.new('RGB',(1440,1600),PAPER);d=ImageDraw.Draw(im)
 d.text((35,24),'LIU-INSPIRED / ENTRY, PRESS, FOLD, LIFT',font=font(30),fill='#302c25')
 d.text((35,72),'A controlled geometry study using manually annotated stroke gestures',font=font(21),fill='#77644d')
 for x,label in zip([30,510,990],['REFERENCE ARTWORK','PREVIOUS ELLIPTICAL BRUSH','NEW ASYMMETRIC CONTACT']):d.text((x,125),label,font=font(21),fill='#493e30')
 for i,row in enumerate(rows):
  y=175+i*465
  for x,key in zip([30,510,990],['target','baseline','new']):im.paste(patch(row[key]),(x,y))
  d.text((510,y+422),f"Silhouette overlap: {iou(row['baseline'],row['target']):.1%}",font=font(19),fill='#77644d')
  d.text((990,y+422),f"Silhouette overlap: {iou(row['new'],row['target']):.1%}",font=font(19),fill='#77644d')
 d.text((35,1570),'Same reference and scale. Hand-authored gestures + bounded fitting; not automatic style recovery.',font=font(19),fill='#77644d')
 im.save(ROOT/'Liu-Brush-Comparison.png')
 # Enlarged diagnostic crops from actual whole-character output, not idealized examples.
 im=Image.new('RGB',(1260,1320),PAPER);d=ImageDraw.Draw(im)
 d.text((25,20),'STROKE FEATURES / IDENTICAL CROPS',font=font(27),fill='#302c25')
 for x,label in zip([20,440,860],['REFERENCE','PREVIOUS','NEW CONTACT BRUSH']):d.text((x,72),label,font=font(20),fill='#77644d')
 for k,(idx,box,label) in enumerate([(1,(25,186,139,272),'Horizontal entry'),(0,(184,61,270,158),'Vertical entry'),(0,(293,22,395,134),'Squared shoulder')]):
  row=rows[idx];x0,y0,x1,y1=box;y=135+k*380
  for x,key in zip([20,440,860],['target','baseline','new']):im.paste(patch(row[key][y0:y1,x0:x1],330),(x,y))
  d.text((20,y+337),label,font=font(20),fill='#493e30')
 im.save(ROOT/'Liu-Brush-Details.png')

def video(rows):
 w,h,fps=1440,760,24;step=1.35
 cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/'Liu-Brush-Experiment.mp4')]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for row in rows:
   painters=[ContactBrush(s) for s in row['strokes']];old=[BrushPainter(s) for s in row['old_strokes']]
   for frame in range(int((len(painters)*step+2.5)*fps)):
    elapsed=max(0,(frame/fps-.5)/step)
    new=np.zeros((480,480),np.float32);prior=np.zeros_like(new)
    for k,p in enumerate(painters):new=np.maximum(new,p.advance(np.clip(elapsed-k,0,1)))
    for k,p in enumerate(old):prior=np.maximum(prior,p.advance(np.clip(elapsed-k,0,1)))
    im=Image.new('RGB',(w,h),PAPER);d=ImageDraw.Draw(im)
    d.text((30,24),'LIU-INSPIRED / SHAPED BRUSH CONTACT',font=font(29),fill='#302c25')
    for x,label,ink in [(30,'REFERENCE ARTWORK',row['target']),(510,'PREVIOUS BRUSH',prior),(990,'NEW CONTACT BRUSH',new)]:
     d.text((x,91),label,font=font(21),fill='#77644d');im.paste(patch(ink),(x,140))
    k=min(int(elapsed),len(painters)-1)
    d.text((30,597),f"Stroke {k+1}/{len(painters)}: {row['strokes'][k]['name']}",font=font(25),fill='#493e30')
    d.text((30,645),'Independent edges / oblique entry / explicit fold / controlled spread and lift',font=font(23),fill='#77644d')
    d.text((30,700),'Experimental guided geometry. Ink accumulates; no source clipping or final-image replacement.',font=font(20),fill='#77644d')
    proc.stdin.write(im.tobytes())
   np.testing.assert_array_equal(new,row['new'])
   print('rendered',row['char'],flush=True)
  proc.stdin.close()
  if proc.wait():raise RuntimeError('ffmpeg failed')
 except BaseException:
  proc.kill();proc.wait();raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reuse',action='store_true');p.add_argument('--video',action='store_true');a=p.parse_args()
 if not a.reuse:build()
 rows=load();still(rows)
 if a.video:video(rows)
