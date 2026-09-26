"""Style transfer study: unchanged contact painter, new generated reference art."""
from pathlib import Path
import argparse,importlib.util,io,json,sys
import cv2,numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image,ImageDraw
import cairosvg
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('contact_poem',ROOT.parent/'liu-poem-contact/render.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from smooth_strokes import registered_fields,smooth_decomposition
import ownership_prepare as ownership
from paint_brush import font
STYLES={'Yan':'Yan-Kaishu','Lishu':'Lishu'}

def extract(source):
 image=np.asarray(Image.open(source).convert('L'));h,w=image.shape
 def cuts(projection,count):
  out=[0]
  for k in range(1,count):
   expected=round(k*len(projection)/count);radius=round(len(projection)/count*.28)
   candidates=np.arange(expected-radius,expected+radius+1)
   blank=candidates[projection[candidates]==0]
   if not len(blank):raise ValueError(f'No blank cell boundary {k}')
   out.append(int(blank[np.argmin(abs(blank-expected))]))
  return out+[len(projection)]
 ys=cuts((image<140).sum(1),5);targets={}
 for row,line in enumerate(base.LINES):
  band=image[ys[row]:ys[row+1]];xs=cuts((band<140).sum(0),6)
  for col,char in enumerate(line):
   if char in targets:continue
   cell=band[:,xs[col]:xs[col+1]];yy,xx=np.where(cell<140)
   if not len(xx):raise ValueError('Empty '+char)
   crop=cell[max(0,yy.min()-2):yy.max()+3,max(0,xx.min()-2):xx.max()+3]
   scale=420/max(crop.shape);small=cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
   gray=np.full((480,480),255,np.uint8);oy,ox=(480-small.shape[0])//2,(480-small.shape[1])//2
   gray[oy:oy+small.shape[0],ox:ox+small.shape[1]]=small;gray[gray>220]=255
   targets[char]=(255-gray).astype(np.float32)/255
 return targets

def prepare_templates():
 data=json.loads((ROOT.parent/'kaishu-poem/characters.json').read_text());work=ROOT/'work';(work/'templates').mkdir(parents=True,exist_ok=True)
 ownership.DATA=data;ownership.OUT=work
 for char,d in data.items():
  layers=[]
  for outline in d['strokes']:
   svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><g transform="scale(.15625) translate(0 900) scale(1 -1)"><path d="{outline}"/></g></svg>'
   layers.append(np.asarray(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA'))[:,:,3])
  Image.fromarray(np.vstack(layers)).save(work/'templates'/f'{char}.png')
 return data

def ordered_guide(layer,phase):
 yy,xx=np.where(layer>.25);weights=layer[yy,xx];p=phase[yy,xx]
 lo,hi=np.quantile(p,[.005,.995]);points=[]
 for a,b in zip(np.linspace(lo,hi+1e-5,25)[:-1],np.linspace(lo,hi+1e-5,25)[1:]):
  sel=(p>=a)&(p<b)
  if sel.sum():points.append(np.average(np.column_stack([xx[sel],yy[sel]]),axis=0,weights=weights[sel]))
 if len(points)<2:
  from paint_brush import medial_path
  return medial_path(layer>.5,[1,1])
 return np.asarray(points)

def iou(a,b):
 a,b=a>.5,b>.5;return float((a&b).sum()/max((a|b).sum(),1))

def build(style):
 data=prepare_templates();out=ROOT/style;out.mkdir(exist_ok=True)
 targets=extract(ROOT/f'{style}-Source.png');np.savez_compressed(out/'targets.npz',**targets)
 strokes={};report=[];inputs={}
 for char,target in targets.items():
  gray=np.uint8(np.clip(255*(1-cv2.resize(target,(160,160))),0,255));warped,phase=registered_fields(gray,char)
  layers,phases,_=smooth_decomposition(warped,phase,target)
  fitted=[];layer_metrics=[]
  for k,(layer,p) in enumerate(zip(layers,phases)):
   guide=ordered_guide(layer,p)
   stroke=base.contacts_from_layer(layer,guide,f'{style} {char} stroke {k+1}')
   fitted.append(stroke);layer_metrics.append(iou(base.complete(stroke),layer))
  painted=np.zeros_like(target);contributions=[]
  for s in fitted:
   nxt=np.maximum(painted,base.complete(s));contributions.append(float((nxt-painted).sum()));painted=nxt
  strokes[char]=fitted
  a,b=painted>.5,target>.5
  record=dict(char=char,strokes=len(fitted),silhouette_iou=iou(painted,target),ink_coverage=float((a&b).sum()/max(b.sum(),1)),spill=float((a&~b).sum()/max(a.sum(),1)),min_stroke_iou=min(layer_metrics),no_new_ink_strokes=[k+1 for k,v in enumerate(contributions) if v<.01])
  report.append(record);print(style,char,round(record['silhouette_iou'],3),'stroke min',round(record['min_stroke_iou'],2),flush=True)
 (out/'contacts.json').write_text(json.dumps(strokes,ensure_ascii=False,separators=(',',':'))+'\n')
 (out/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

def outputs(style,video=False):
 base.ROOT=ROOT/style
 paper=Image.open(ROOT/'Decorated-Light-Paper.png').convert('RGB').resize((1080,1440),Image.Resampling.LANCZOS)
 base.background=lambda:paper.copy()
 data=base.load();base.still(data)
 (base.ROOT/'Liu-Full-Poem-Light.png').rename(ROOT/f'{STYLES[style]}-Poem.png')
 if video:
  base.render(data);(base.ROOT/'Liu-Full-Poem-Light.mp4').rename(ROOT/f'{STYLES[style]}-Poem.mp4')
 return data

def audit():
 chars=list('人有月圓長難');width=1600;height=140+len(chars)*190
 im=Image.new('RGB',(width,height),(249,246,238));d=ImageDraw.Draw(im)
 d.text((30,20),'STYLE TRANSFER / SAME CONTACT PAINTER',font=font(29),fill='#302c25')
 for x,label in [(30,'YAN SOURCE'),(420,'YAN CONTACT'),(810,'LISHU SOURCE'),(1200,'LISHU CONTACT')]:d.text((x,80),label,font=font(24),fill='#76634e')
 for style,origin in [('Yan',0),('Lishu',800)]:
  base.ROOT=ROOT/style;data=base.load();targets=np.load(base.ROOT/'targets.npz')
  for i,c in enumerate(chars):
   y=130+i*190
   for x,ink in [(origin+100,targets[c]),(origin+500,data[c]['paint'])]:
    rgb=np.uint8(np.array([249,246,238])[None,None,:]*(1-ink[...,None])+27*ink[...,None]);im.paste(Image.fromarray(rgb).resize((175,175),Image.Resampling.LANCZOS),(x,y))
 im.save(ROOT/'Style-Transfer-Audit.png')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--style',choices=STYLES);p.add_argument('--reuse',action='store_true');p.add_argument('--video',action='store_true');p.add_argument('--audit',action='store_true');a=p.parse_args()
 if a.audit:audit()
 else:
  for style in [a.style] if a.style else STYLES:
   if not a.reuse:build(style)
   outputs(style,a.video)
