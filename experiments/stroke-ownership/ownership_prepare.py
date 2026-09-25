"""Bounded raster-stroke layers with preserved overlap.
Templates supply topology/order only; final ink comes from generated artwork.
Registration and ownership are inferred, not verified historical ductus.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage.registration import optical_flow_tvl1
import cv2
from stroke_layers import compose_layers
R=Path(__file__).parent
OUT=R/'ownership-work'; OUT.mkdir(exist_ok=True)
DATA=json.loads((R/'ownership-characters.json').read_text())
TEXT='空山新雨後天氣晚來秋明月松間照清泉石上流竹喧歸浣女蓮動下漁舟隨意春芳歇王孫自可留'
S=160

def groups(v):
    a=ndi.binary_closing(v,iterations=9)
    lab,n=ndi.label(a)
    return [(np.where(lab==i)[0][0],np.where(lab==i)[0][-1]+1) for i in range(1,n+1) if (lab==i).sum()>30]

def extract(path,rows):
    im=np.array(Image.open(path).convert('L'))
    mask=im<150
    rg=groups(mask.sum(1)>8)
    # Preserve edge rows if closing has trimmed the last few pixels.
    if mask[-10:].any() and rg: rg[-1]=(rg[-1][0],len(im))
    if len(rg)!=rows: raise ValueError((str(path),rg,rows))
    result=[]
    for y0,y1 in rg:
        projection=mask[y0:y1].sum(0)
        cuts=[0]
        for k in range(1,5):
            expected=round(k*im.shape[1]/5)
            lo=max(cuts[-1]+10,expected-35);hi=min(im.shape[1]-1,expected+36)
            window=projection[lo:hi]
            choices=np.where(window==window.min())[0]+lo
            cuts.append(int(choices[np.argmin(abs(choices-expected))]))
        cuts.append(im.shape[1])
        for col in range(5):
            x0,x1=cuts[col:col+2]
            crop=im[y0:y1,x0:x1]
            yy,xx=np.where(crop<150)
            crop=crop[max(0,yy.min()-2):yy.max()+3,max(0,xx.min()-2):xx.max()+3]
            scale=(S-20)/max(crop.shape)
            resized=cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
            canvas=np.full((S,S),255,np.uint8)
            oy=(S-resized.shape[0])//2;ox=(S-resized.shape[1])//2
            canvas[oy:oy+resized.shape[0],ox:ox+resized.shape[1]]=resized
            result.append(canvas)
    return result

def template(char):
    d=DATA[char];n=len(d['strokes'])
    strip=np.array(Image.open(OUT/'templates'/f'{char}.png').convert('L'))
    stack=strip.reshape(n,S,S)
    union=stack.max(0)>128
    yy,xx=np.where(union);x0=xx.min();x1=xx.max()+1;y0=yy.min();y1=yy.max()+1
    scale=(S-20)/max(x1-x0,y1-y0)
    width=round((x1-x0)*scale);height=round((y1-y0)*scale)
    ox=(S-width)//2;oy=(S-height)//2
    layers=np.zeros((n,S,S),np.float32)
    progress=np.zeros_like(layers)
    yy,xx=np.mgrid[:S,:S]
    for i in range(n):
        layers[i,oy:oy+height,ox:ox+width]=cv2.resize(stack[i,y0:y1,x0:x1],(width,height))/255
        points=np.array(d['medians'][i],float)
        points[:,1]=900-points[:,1]
        points=points*.15625
        points=(points-[x0,y0])*scale+[ox,oy]
        ls=np.linalg.norm(np.diff(points,axis=0),axis=1)
        dist=np.full((S,S),1e9);offset=0
        for a,b,length in zip(points[:-1],points[1:],ls):
            v=b-a
            t=np.clip(((xx-a[0])*v[0]+(yy-a[1])*v[1])/max(length**2,1e-6),0,1)
            dd=(xx-a[0]-t*v[0])**2+(yy-a[1]-t*v[1])**2
            update=dd<dist
            progress[i][update]=(offset+t[update]*length)/max(ls.sum(),1)
            dist=np.minimum(dist,dd);offset+=length
    return layers,progress

def process(gray,char):
    layers,phase=template(char)
    target=(255-gray)/255.
    union=layers.max(0)
    # Smooth registration adapts the template layout to this artist's glyph.
    reference=ndi.gaussian_filter(target,1.5)
    moving=ndi.gaussian_filter(union,1.5)
    flow=optical_flow_tvl1(reference,moving,attachment=12,tightness=.3,num_warp=8,num_iter=12)
    yy,xx=np.mgrid[:S,:S]
    coords=np.array([yy+flow[0],xx+flow[1]])
    warped=np.stack([ndi.map_coordinates(a,coords,order=1,mode='constant') for a in layers])
    prog=np.stack([ndi.map_coordinates(a,coords,order=1,mode='nearest') for a in phase])
    support=warped>.20
    # The same narrow support collar as the conservative baseline. Each stroke
    # now keeps its intersection area instead of subtracting competitors.
    broad=np.stack([ndi.binary_dilation(a,iterations=1) for a in support])
    ink=target>.20
    memberships,exposure,owner=compose_layers(broad,prog,ink)
    accepted=owner>=0
    original=target.astype(np.float32)
    retained=original*accepted
    dropped=float(original[~accepted].sum()/max(original.sum(),1))
    empty=[i+1 for i,layer in enumerate(memberships) if not layer.any()]
    return dict(original=original,retained=retained,owner=owner,memberships=memberships,exposure=exposure,n=len(layers),dropped=dropped,empty=empty)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,help='Optional raw sheet JSON; paths relative to that JSON')
    args=parser.parse_args()
    if args.assets:
        config=json.loads(args.assets.read_text())
        asset_root=args.assets.resolve().parent
        patches=extract(asset_root/config['last_row'],3) if config.get('last_row') else None
        bundled=None
    else:
        bundled=np.load(R/'glyphs.npz')
        patches=None
    report=[]
    for si,style in enumerate(['Yan','Liu','Zhao']):
        glyphs=bundled[style] if bundled is not None else extract(asset_root/config[style],8)
        if patches: glyphs[-5:]=patches[si*5:si*5+5]
        samples=[]
        for j,(char,gray) in enumerate(zip(TEXT,glyphs)):
            r=process(gray,char)
            samples.append(r)
            np.savez_compressed(OUT/f'{style}-{j:02}.npz',**{k:v for k,v in r.items() if k!='empty'})
            report.append(dict(style=style,char=char,index=j,omitted_ink=r['dropped'],empty_strokes=r['empty']))
            print(style,j,char,'omitted',round(r['dropped']*100,1),'empty',r['empty'],flush=True)
        # Enlarged audit: original / conservative mask for every character.
        canvas=Image.new('RGB',(S*10,S*8),(247,245,238))
        for j,r in enumerate(samples):
            row,col=divmod(j,5)
            for k,name in enumerate(['original','retained']):
                a=np.uint8(255*(1-r[name]))
                canvas.paste(Image.fromarray(a).convert('RGB'),((col*2+k)*S,row*S))
        canvas.save(OUT/f'{style}-audit.png')
    (OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
