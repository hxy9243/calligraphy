import json
from PIL import Image, ImageDraw
import numpy as np
from scipy import ndimage as ndi

source=np.asarray(Image.open('experiments/kai-four/source.jpg').convert('L'))
data=json.load(open('experiments/kai-four/shu.json'))
ref=np.asarray(Image.open('experiments/kai-four/template.png').convert('L'))<100
ys,xs=np.where(ref)
refbox=(xs.min(),ys.min(),xs.max(),ys.max())
rois=[(5,3,292,296,True,135),(316,4,584,297,True,140),(52,306,282,591,True,130),(312,305,590,596,False,125)]
canvas=Image.new('RGB',(600,600),'#f5f0e5')
for idx,(x0,y0,x1,y1,white,threshold) in enumerate(rois):
 a=source[y0:y1,x0:x1]
 binary=(a>threshold) if white else (a<threshold)
 labs,n=ndi.label(binary)
 sizes=np.bincount(labs.ravel())
 binary &= sizes[labs]>35
 ys,xs=np.where(binary)
 minx,miny,maxx,maxy=xs.min(),ys.min(),xs.max(),ys.max()
 # normalize to 240 square at tile origin
 out=Image.new('RGB',(300,300),'#f5f0e5')
 pix=np.array(out)
 # render input in grayscale black
 pix[:a.shape[0],:a.shape[1]][binary]=[45,41,38]
 out=Image.fromarray(pix)
 draw=ImageDraw.Draw(out)
 sx=(maxx-minx)/(refbox[2]-refbox[0]); sy=(maxy-miny)/(refbox[3]-refbox[1])
 for stroke in data['medians']:
  pts=[(minx+(p[0]*300/1024-refbox[0])*sx,miny+((900-p[1])*300/1024-refbox[1])*sy) for p in stroke]
  draw.line(pts,fill=(190,70,40),width=2)
  draw.ellipse((pts[0][0]-3,pts[0][1]-3,pts[0][0]+3,pts[0][1]+3),fill=(40,130,60))
 canvas.paste(out,((idx%2)*300,(idx//2)*300))
 print(idx, (minx,miny,maxx,maxy), 'scale',round(sx,2),round(sy,2))
canvas.save('experiments/kai-four/overlay.png')
