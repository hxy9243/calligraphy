# One-example style transfer baseline: 書 → 永

This experiment uses the Yan Zhenqing **書** scan from `experiments/kai-four/source.jpg` to create a new **永** image and animation. The five target stroke outlines and ordered median paths come from `data/yong.json` (Hanzi Writer Data under the repo's Arphic license). It measures the reference's ink fraction relative to the generic 書 template, adjusts all target outlines to that optical weight, adds restrained edge and ink variation, then reveals each complete target stroke along its known median. The reference image was taken from the public-domain Wikimedia comparison documented in `experiments/kai-four/README.md`.

From the repo root, run:

```sh
npm install
python3 -m pip install -r experiments/kai-four/requirements.txt
node experiments/style-transfer/rasterize.mjs
python3 experiments/style-transfer/synthesize.py
```

Outputs: `yan-inspired-yong.png`, `yan-inspired-yong.mp4`, and `diagnostics.json`. The video places the reference 書 beside the newly generated 永. The render uses the known target stroke topology, so there is no intersection-ownership ambiguity for the new character. Its shape is still largely the generic Hanzi Writer geometry. The measured style transfer is limited to overall weight, color and texture: **this is not a reconstruction of Yan Zhenqing's hypothetical 永**. One scanned glyph does not constrain a full writer-specific stroke vocabulary or compositional habits.

Next, use corrected per-stroke annotations from `experiments/kai-four/annotate-standalone.html` to estimate orientation-specific stroke proportions, start/end pressure, and terminal shapes; test on a second target character and obtain a writer/style plausibility assessment. Retain the generic target outlines as a structural prior and expose the stylization strength so changes can be compared visually.

## Poem at 1.5× speed

`yan-poem-1.5x.mp4` writes 明月松间照，清泉石上流 in vertical columns, right column first and top to bottom within each column. It uses the same measured contour expansion (4.12 pixels at a 512-pixel glyph size) with the ten known Hanzi Writer characters. This SVG variant uses smooth ink gradients and paper grain. It is a Yan-inspired optical-weight approximation, not a learned Yan typeface or a diffusion model.

```sh
STYLE=yan SPEED=1.5 OUTPUT=experiments/style-transfer/yan-poem-1.5x.mp4 node scripts/render-poem.mjs
```

The baseline schedule is 26 seconds; 1.5× playback produces 17.33 seconds at 24 fps. `yan-poem-final.png` is the final still.
