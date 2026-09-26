"""Isolate ellipse-model capacity using the same corrected stroke and guide.

This is an in-sample reconstruction check, not generalization evidence.
"""
import json
import numpy as np
from study import ROOT,load,iou,complete,patch,PAPER,font
from paint_brush import fit_brush,complete as ellipse_complete
from PIL import Image,ImageDraw
rows=load();report=[];im=Image.new('RGB',(1440,1540),PAPER);d=ImageDraw.Draw(im)
for x,label in zip([30,510,990],['CORRECTED STROKE GEOMETRY','ELLIPSE / SAME INPUT + GUIDE','CONTACT / SAME INPUT']):d.text((x,25),label,font=font(20),fill='#493e30')
for idx,row in enumerate(rows):
 original=[complete(s) for s in row['strokes']];old=[]
 for stroke,target in zip(row['strokes'],original):
  guide=np.mean(stroke['contacts'],axis=1);direction=guide[-1]-guide[0]
  old.append(ellipse_complete(fit_brush(target,direction,guide=guide)))
 old=np.maximum.reduce(old);geometry=np.maximum.reduce(original)
 report.append(dict(char=row['char'],ellipse_iou_to_corrected_geometry=iou(old,geometry),ellipse_iou_to_reference=iou(old,row['target']),contact_iou_to_reference=iou(geometry,row['target'])))
 for x,a in zip([30,510,990],[geometry,old,geometry]):im.paste(patch(a),(x,80+idx*480))
 d.text((510,505+idx*480),f"IoU to corrected shape: {iou(old,geometry):.1%}",font=font(19),fill='#77644d')
(ROOT/'ablation-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');im.save(ROOT/'Liu-Brush-Ablation.png');print(json.dumps(report,ensure_ascii=False,indent=2))
