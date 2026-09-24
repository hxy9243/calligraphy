"""Bundle the annotator and scan into one downloadable, offline HTML file."""
import base64
import json
from pathlib import Path

here=Path(__file__).resolve().parent
html=(here/'annotate.html').read_text()
html=html.replace('href="./README.md"','href="https://github.com/hxy9243/caligraphy/blob/main/experiments/kai-four/README.md"')
script=(here/'annotate.mjs').read_text()
data=json.loads((here/'annotation-seeds.json').read_text())
image='data:image/jpeg;base64,'+base64.b64encode((here/'source.jpg').read_bytes()).decode()
html=html.replace('<script type="module" src="./annotate.mjs"></script>',
    '<script>window.ANNOTATION_SEEDS='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+
    ';window.SOURCE_IMAGE='+json.dumps(image)+';</script><script>(async()=>{'+script+
    '})().catch(error=>{document.getElementById("status").textContent="Could not open annotator: "+error.message;});</script>')
(here/'annotate-standalone.html').write_text(html)
print(f"Wrote {here/'annotate-standalone.html'}")
