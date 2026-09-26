"""Full unpunctuated Su Shi poem, rendered with the contact-strip brush model."""
from pathlib import Path
import argparse,io,json,subprocess,sys
import cv2,numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter
from PIL import Image,ImageDraw
import cairosvg
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'liu-brush-grammar'))
sys.path.insert(0,str(ROOT.parent/'lishu-transfer'))
sys.path.insert(0,str(ROOT.parent/'stroke-ownership'))
from brush_grammar import ContactBrush,complete
from paint_brush import font
LINES=['人有悲歡離合','月有陰晴圓缺','此事古難全','但願人長久','千里共嬋娟']
TEXT=''.join(LINES);SIZE=480;W,H=1080,1440

def resample(points,n=100):
 p=np.asarray(points,float);t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
 keep=np.r_[True,np.diff(t)>1e-8];t,p=t[keep],p[keep]
 return np.column_stack([np.interp(np.linspace(0,t[-1],n),t,p[:,j]) for j in range(2)])

def simplify_pairs(p,tol=.7):
 flat=p.reshape(len(p),4)
 def split(a,b):
  if b-a<2:return [a,b]
  v=flat[b]-flat[a];u=np.clip((flat[a+1:b]-flat[a])@v/max(v@v,1e-8),0,1)
  d=np.linalg.norm(flat[a+1:b]-flat[a]-u[:,None]*v,axis=1);k=a+1+d.argmax()
  if d.max()<=tol:return [a,b]
  return split(a,k)[:-1]+split(k,b)
 return p[split(0,len(p)-1)]

def contacts_from_layer(layer,guide,name):
 mask=np.uint8(gaussian_filter(layer,.65)>.45)
 contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
 if not contours:raise ValueError('Empty stroke '+name)
 contour=max(contours,key=cv2.contourArea)[:,0].astype(float)
 g=np.asarray(guide);ia=np.argmin(np.linalg.norm(contour-g[0],axis=1));ib=np.argmin(np.linalg.norm(contour-g[-1],axis=1))
 if ia==ib:ib=np.argmax(np.linalg.norm(contour-contour[ia],axis=1))
 contour=np.roll(contour,-ia,axis=0);ib=(ib-ia)%len(contour)
 a=resample(contour[:ib+1]);b=resample(np.vstack([contour[0],contour[:ib-1:-1]]))
 # Monotonic correspondence between two contour rails. Short cross-sections
 # avoid diagonal bridges across inside corners; guide progress stabilizes hooks.
 pa=np.argmin(((a[:,None]-g[None])**2).sum(2),axis=1)/max(len(g)-1,1)
 pb=np.argmin(((b[:,None]-g[None])**2).sum(2),axis=1)/max(len(g)-1,1)
 cost=((a[:,None]-b[None])**2).sum(2)+2500*(pa[:,None]-pb[None])**2
 n,m=cost.shape;dp=np.full((n,m),np.inf);prev=np.zeros((n,m),np.uint8);dp[0,0]=0
 for i in range(n):
  for j in range(m):
   if i==j==0:continue
   choices=[dp[i-1,j-1] if i and j else np.inf,dp[i-1,j] if i else np.inf,dp[i,j-1] if j else np.inf]
   k=int(np.argmin(choices));dp[i,j]=cost[i,j]+choices[k];prev[i,j]=k
 i,j=n-1,m-1;p=[]
 while True:
  p.append([a[i],b[j]])
  if i==j==0:break
  k=prev[i,j]
  if k in (0,1):i-=1
  if k in (0,2):j-=1
 pairs=simplify_pairs(np.asarray(p[::-1]));centers=pairs.mean(1)
 turns=np.zeros(len(pairs));v=np.diff(centers,axis=0);v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-5)
 turns[1:-1]=np.arccos(np.clip((v[:-1]*v[1:]).sum(1),-1,1))
 corners=np.where(turns>1.)[0].tolist()
 return dict(name=name,contacts=pairs.tolist(),corners=corners,tension=.5,
  features=[dict(station=1,kind='entry-press')]+[dict(station=k,kind='square-fold') for k in corners]+[dict(station=len(pairs)-2,kind='lift')])

def build():
 import ownership_prepare as ownership
 from smooth_strokes import registered_fields,smooth_decomposition
 work=ROOT/'work';work.mkdir(exist_ok=True);(work/'templates').mkdir(exist_ok=True)
 data=json.loads((ROOT.parent/'kaishu-poem/characters.json').read_text());ownership.DATA=data;ownership.OUT=work
 for char,d in data.items():
  layers=[]
  for outline in d['strokes']:
   svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><g transform="scale(.15625) translate(0 900) scale(1 -1)"><path d="{outline}"/></g></svg>'
   layers.append(np.asarray(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA'))[:,:,3])
  Image.fromarray(np.vstack(layers)).save(work/'templates'/f'{char}.png')
 targets=np.load(ROOT/'targets.npz');guides=json.loads((ROOT/'guides.json').read_text());manual=json.loads((ROOT.parent/'liu-brush-grammar/fitted-controls.json').read_text())
 all_strokes={};metrics=[]
 for char in dict.fromkeys(TEXT):
  target=targets[char]
  if char in manual:strokes=manual[char];method='manual contacts'
  else:
   gray=np.uint8(np.clip(255*(1-cv2.resize(target,(160,160))),0,255));warped,phase=registered_fields(gray,char)
   layers,_,_=smooth_decomposition(warped,phase,target)
   strokes=[contacts_from_layer(layer,guide,f'{char} stroke {k+1}') for k,(layer,guide) in enumerate(zip(layers,guides[char]))];method='automatic contour contacts'
  union=np.zeros_like(target);contributions=[]
  for s in strokes:
   nxt=np.maximum(union,complete(s));contributions.append(float((nxt-union).sum()));union=nxt
  a,b=union>.5,target>.5;iou=float((a&b).sum()/max((a|b).sum(),1));all_strokes[char]=strokes
  metrics.append(dict(char=char,method=method,strokes=len(strokes),silhouette_iou=iou,no_new_ink_strokes=[k+1 for k,v in enumerate(contributions) if v<.01]))
  print(char,len(strokes),round(iou,3),flush=True)
 (ROOT/'contacts.json').write_text(json.dumps(all_strokes,ensure_ascii=False,separators=(',',':'))+'\n')
 (ROOT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')

def background():
 # Deterministic, restrained paper grain generated procedurally.
 rng=np.random.default_rng(20260926);grain=gaussian_filter(rng.normal(0,.8,(H,W)),.4)
 rgb=np.clip(np.array([249,246,238])[None,None,:]+grain[...,None],0,255).astype(np.uint8)
 return Image.fromarray(rgb)
def patch(ink):
 a=Image.fromarray(np.uint8(np.clip(ink,0,1)*255)).resize((176,176),Image.Resampling.LANCZOS)
 p=Image.new('RGBA',(176,176),(28,27,24,0));p.putalpha(a);return p
def locations():return [(c,832-col*190,140+row*194) for col,line in enumerate(LINES) for row,c in enumerate(line)]
def paste(im,ink,x,y):
 p=patch(ink);im.paste(p,(x,y),p)
def load():
 strokes=json.loads((ROOT/'contacts.json').read_text());return {c:dict(strokes=s,paint=np.maximum.reduce([complete(v) for v in s])) for c,s in strokes.items()}
def still(data):
 im=background()
 for c,x,y in locations():paste(im,data[c]['paint'],x,y)
 im.save(ROOT/'Liu-Full-Poem-Light.png')
 # Internal audit: all unique glyphs, same scale, target above reconstruction.
 targets=np.load(ROOT/'targets.npz');audit=Image.new('RGB',(1200,1200),(249,246,238));d=ImageDraw.Draw(audit)
 for i,c in enumerate(data):
  x=i%6*200;y=i//6*280
  for dy,a in [(0,targets[c]),(130,data[c]['paint'])]:
   p=Image.fromarray(np.uint8(249*(1-a)+27*a)).convert('RGB').resize((120,120));audit.paste(p,(x+35,y+dy))
 audit.save(ROOT/'audit.png')
def render(data):
 fps,step=24,.28;out=ROOT/'Liu-Full-Poem-Light.mp4'
 proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
 page=background();cells=locations()
 try:
  for j,(char,x,y) in enumerate(cells):
   strokes=data[char]['strokes'];painters=[ContactBrush(s) for s in strokes];union=np.zeros((SIZE,SIZE),np.float32);finished=set()
   duration=.3+len(strokes)*step+.22+(4 if j==len(cells)-1 else 0)
   for f in range(int(np.ceil(duration*fps))):
    elapsed=max(0,(f/fps-.3)/step)
    for k,p in enumerate(painters):
     if k in finished or elapsed<k:continue
     progress=min(1,elapsed-k);union=np.maximum(union,p.advance(progress))
     if progress>=1:finished.add(k)
    im=page.copy();paste(im,union,x,y);proc.stdin.write(im.tobytes())
   np.testing.assert_array_equal(union,data[char]['paint']);paste(page,union,x,y)
   print('video',j+1,'/27',char,flush=True)
  proc.stdin.close()
  if proc.wait():raise RuntimeError('ffmpeg failed')
 except BaseException:
  proc.kill();proc.wait();raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reuse',action='store_true');p.add_argument('--video',action='store_true');a=p.parse_args()
 if not a.reuse:build()
 data=load();still(data)
 if a.video:render(data)
