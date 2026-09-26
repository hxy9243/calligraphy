"""Change video playback speed by retiming packets, without re-encoding frames."""
from pathlib import Path
import argparse,json,math,subprocess
ROOT=Path(__file__).resolve().parent

def retime(source,speed=2.):
 if not math.isfinite(speed) or speed<=0:raise ValueError('Speed must be finite and positive')
 destination=source.with_name(f'{source.stem}-{speed:g}x{source.suffix}')
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(source),'-map','0:v:0','-c:v','copy','-an',
  '-bsf:v',f'setts=pts=PTS/{speed:g}:dts=DTS/{speed:g}:duration=DURATION/{speed:g}',
  '-movflags','+faststart',str(destination)],check=True)
 def probe(path):
  return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
   '-show_entries','stream=duration,nb_frames,width,height,avg_frame_rate','-of','json',str(path)]))['streams'][0]
 before,after=probe(source),probe(destination)
 assert before['nb_frames']==after['nb_frames']
 assert abs(float(after['duration'])-float(before['duration'])/speed)<.002
 assert (before['width'],before['height'])==(after['width'],after['height'])
 return dict(source=source.name,output=destination.name,speed=speed,before=before,after=after)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--speed',type=float,default=2.);args=p.parse_args()
 results=[retime(ROOT/name,args.speed) for name in ['Yan-Kaishu-Poem.mp4','Lishu-Poem.mp4']]
 (ROOT/f'retiming-{args.speed:g}x.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results,indent=2))
