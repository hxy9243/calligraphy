const SIZE=300, canvas=document.querySelector('#canvas'),ctx=canvas.getContext('2d');
const el=id=>document.getElementById(id);
const proposed=window.ANNOTATION_SEEDS||await (await fetch('./annotation-seeds.json')).json();
const source=new Image();source.src=window.SOURCE_IMAGE||'./source.jpg';await source.decode();
let style=0,stroke=0,tool='paint',drawing=false,last=null,dragPoint=-1,history=[],working=proposed.styles.map((entry,i)=>load(i)||decodeStyle(entry));
const colors={active:[201,100,58],other:[62,111,153]};

function maskDecode(rle){const a=new Uint8Array(SIZE*SIZE);for(const [start,count] of rle)a.fill(1,start,start+count);return a}
function maskEncode(a){let result=[],begin=-1;for(let i=0;i<=a.length;i++){if(i<a.length&&a[i]&&begin<0)begin=i;if((i===a.length||!a[i])&&begin>=0){result.push([begin,i-begin]);begin=-1}}return result}
function decodeStyle(entry){return entry.strokes.map(s=>({mask:maskDecode(s.maskRLE),median:s.median.map(p=>[...p])}))}
function encodeStyle(){return {version:1,character:'書',size:SIZE,style:proposed.styles[style].name,
  sourceRoi:proposed.styles[style].roi,strokes:working[style].map(s=>({maskRLE:maskEncode(s.mask),median:s.median}))}}
function load(i){try{const saved=JSON.parse(localStorage.getItem('kai-annotation-'+i));return saved?.strokes?.length===10?decodeStyle(saved):null}catch{return null}}
function save(){try{localStorage.setItem('kai-annotation-'+style,JSON.stringify(encodeStyle()));el('status').textContent='Saved locally · '+proposed.styles[style].name+' · stroke '+(stroke+1)}catch{el('status').textContent='Browser storage unavailable; download your annotation JSON.'}}
function snapshot(){history.push({style,stroke,mask:working[style][stroke].mask.slice(),median:working[style][stroke].median.map(p=>[...p])});if(history.length>30)history.shift()}
function position(event){const rect=canvas.getBoundingClientRect();return [Math.max(0,Math.min(299,(event.clientX-rect.left)*SIZE/rect.width)),Math.max(0,Math.min(299,(event.clientY-rect.top)*SIZE/rect.height))]}
function paint(point,prev){const mask=working[style][stroke].mask,value=tool==='paint'?1:0,r=Number(el('size').value)/2;
  const steps=prev?Math.max(1,Math.ceil(Math.hypot(point[0]-prev[0],point[1]-prev[1])/(r/2))):1;
  for(let j=0;j<=steps;j++){const x=prev?prev[0]+(point[0]-prev[0])*j/steps:point[0],y=prev?prev[1]+(point[1]-prev[1])*j/steps:point[1];
    for(let yy=Math.max(0,Math.floor(y-r));yy<=Math.min(299,Math.ceil(y+r));yy++)for(let xx=Math.max(0,Math.floor(x-r));xx<=Math.min(299,Math.ceil(x+r));xx++)if((xx-x)**2+(yy-y)**2<=r*r)mask[yy*SIZE+xx]=value}
}
function draw(){const entry=proposed.styles[style], [x0,y0,x1,y1]=entry.roi;
  ctx.clearRect(0,0,600,600);ctx.save();ctx.filter=entry.bright?'invert(1)':'none';ctx.drawImage(source,x0,y0,x1-x0,y1-y0,0,0,600,600);ctx.restore();
  const overlay=ctx.createImageData(SIZE,SIZE),pixels=overlay.data;for(let i=0;i<SIZE*SIZE;i++){
    let selected=working[style][stroke].mask[i];let other=false;
    if(!selected)for(let j=0;j<working[style].length;j++)if(j!==stroke&&working[style][j].mask[i]){other=true;break}
    if(selected||other){let rgb=selected?colors.active:colors.other;pixels.set([...rgb,selected?130:46],i*4)}
  }
  const layer=document.createElement('canvas');layer.width=SIZE;layer.height=SIZE;layer.getContext('2d').putImageData(overlay,0,0);ctx.imageSmoothingEnabled=false;ctx.drawImage(layer,0,0,600,600);
  const points=working[style][stroke].median;ctx.lineWidth=3;ctx.strokeStyle='#f5dfac';ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x*2,y*2):ctx.moveTo(x*2,y*2));ctx.stroke();
  ctx.font='bold 14px system-ui';points.forEach(([x,y],i)=>{ctx.fillStyle='#fff5d6';ctx.beginPath();ctx.arc(x*2,y*2,8,0,7);ctx.fill();ctx.strokeStyle='#774432';ctx.lineWidth=1.5;ctx.stroke();ctx.fillStyle='#603b2c';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(i+1),x*2,y*2)});
  el('status').textContent=`${entry.name} · stroke ${stroke+1}/10 · ${working[style][stroke].mask.reduce((n,v)=>n+v,0)} mask pixels. Changes save locally.`
}
function switchStroke(i){stroke=i;el('strokeList').querySelectorAll('button').forEach((b,j)=>b.classList.toggle('active',j===i));draw()}
function nearestPoint(point){let best=-1,dist=10;working[style][stroke].median.forEach((p,i)=>{let d=Math.hypot(p[0]-point[0],p[1]-point[1]);if(d<dist){best=i;dist=d}});return best}
function segmentDistance(p,a,b){const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)}
canvas.addEventListener('pointerdown',e=>{e.preventDefault();canvas.setPointerCapture(e.pointerId);let p=position(e);if(tool==='path'){dragPoint=nearestPoint(p);if(dragPoint<0)return}snapshot();drawing=true;last=p;if(tool==='path')working[style][stroke].median[dragPoint]=p;else paint(p,null);draw()});
canvas.addEventListener('pointermove',e=>{if(!drawing)return;let p=position(e);if(tool==='path')working[style][stroke].median[dragPoint]=p;else paint(p,last);last=p;draw()});
function end(){if(drawing){drawing=false;dragPoint=-1;save();draw()}}canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
canvas.addEventListener('dblclick',e=>{if(tool!=='path')return;let p=position(e),points=working[style][stroke].median;let index=-1,dist=12;for(let i=0;i<points.length-1;i++){const d=segmentDistance(p,points[i],points[i+1]);if(d<dist){dist=d;index=i}}if(index>=0){snapshot();points.splice(index+1,0,p);save();draw()}});
proposed.styles.forEach((s,i)=>el('style').add(new Option(s.name,i)));
for(let i=0;i<10;i++){let b=document.createElement('button');b.textContent=String(i+1).padStart(2,'0');b.title='Stroke '+(i+1);b.onclick=()=>switchStroke(i);el('strokeList').append(b)}
el('style').onchange=e=>{style=Number(e.target.value);history=[];switchStroke(0)};
el('tools').onclick=e=>{let b=e.target.closest('button[data-tool]');if(!b)return;tool=b.dataset.tool;el('tools').querySelectorAll('button').forEach(v=>v.classList.toggle('active',v===b))};
el('size').oninput=e=>el('sizeLabel').textContent=e.target.value;
el('undo').onclick=()=>{let old=history.pop();if(!old)return;style=old.style;el('style').value=style;working[style][old.stroke]={mask:old.mask,median:old.median};switchStroke(old.stroke);save()};
el('reset').onclick=()=>{if(!confirm('Reset every stroke in this style to the automatic proposal?'))return;working[style]=decodeStyle(proposed.styles[style]);history=[];save();draw()};
el('export').onclick=()=>{let blob=new Blob([JSON.stringify(encodeStyle())+'\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`shu-${proposed.styles[style].name.toLowerCase().replaceAll(' ','-')}-annotations.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
el('import').onclick=()=>el('file').click();el('file').onchange=async e=>{let file=e.target.files[0];if(!file)return;try{let data=JSON.parse(await file.text());if(data.version!==1||data.size!==SIZE||data.strokes?.length!==10)throw Error('Expected a version 1, 300px, ten-stroke annotation');let index=proposed.styles.findIndex(s=>s.name===data.style);if(index<0)throw Error('Unknown calligrapher');style=index;el('style').value=index;working[index]=decodeStyle(data);history=[];switchStroke(0);save()}catch(err){alert(err.message)}e.target.value=''};
switchStroke(0);
