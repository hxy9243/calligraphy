# Four regular-script hands: can a known stroke template animate real ink?

## Source and setup

The [600 × 600 public-domain comparison image](https://commons.wikimedia.org/wiki/File:%E6%A5%B7%E4%B9%A6%E5%9B%9B%E5%A4%A7%E5%AE%B6.jpg) contains **書** by Ouyang Xun (upper left), Yan Zhenqing (upper right), Liu Gongquan (lower left), and Zhao Mengfu (lower right). `source.jpg` is that image. The ten ordered outlines and median paths in `shu.json` come from [Hanzi Writer Data](https://github.com/chanind/hanzi-writer-data), with the Arphic license at the repo root. The calligraphy source and the stroke template have different provenance.

Run from the repo root:

```sh
python3 -m pip install -r experiments/kai-four/requirements.txt
python3 experiments/kai-four/render.py
```

FFmpeg is required. The renderer outputs `four-kai-shu.mp4` (12 seconds, 1200 × 1320); the checked-in demo video is compressed to 900 × 990. `diagnostics.json` records image-space alignment measurements. `diagnose.py` draws the initial globally aligned medians over the scans for inspection. `template.png` is a 300 × 300 rendering of the ordered vector stroke data.

## Method

1. Crop each character and threshold its ink; keep the source's local ink tones.
2. Scale the ten template medians to each scan's ink bounding box. No learned registration and no individually edited paths are used.
3. For each ink pixel, find the nearest median segment and its distance along that stroke. Assign an exposure time from the known stroke index and path progress. Apply a narrow spatial minimum filter at junctions to limit gaps between visually connected strokes.
4. Reveal the *source image's* ink pixels at their inferred times. All four characters follow the same ordered template but retain distinct final shapes.

This is a **template-guided image reveal**, not a simulation of a brush's physical contact, and not a recovery of recorded historical motion.

## Observations

The table measures how far each source-ink pixel is from the *nearest scaled template median*. It is a rough registration diagnostic, **not** an accuracy score for stroke identity or historical writing order. Thicker strokes naturally increase these distances. “Ambiguous” means the nearest and second-nearest median distances differ by less than three pixels.

| Writer | Median distance (px) | 90th percentile (px) | Ink over 20 px from any median | Ambiguous ink |
| --- | ---: | ---: | ---: | ---: |
| Ouyang Xun | 6.5 | 13.3 | 0.7% | 16.4% |
| Yan Zhenqing | 6.2 | 16.8 | 5.4% | 11.1% |
| Liu Gongquan | 6.9 | 13.0 | 0.7% | 21.2% |
| Zhao Mengfu | 7.9 | 18.5 | 8.1% | 13.3% |

The final frames preserve the four recognizable styles, but intermediate frames expose weaknesses: some ink appears as disconnected islands, crossings can temporarily leave gaps, and a thick stroke may reveal an adjacent mark too early. These effects are clearest in the broad Yan and Zhao examples, and the tightly crossing Liu example. The source is low resolution and includes photocopy texture, so the threshold also retains a few small artifacts. The shared ten-stroke template is a plausible ordering prior; without a recording, we cannot establish the four writers' exact stroke segmentation, speed, or pressure.

## Next experiment

Keep source-ink rendering, but replace global bounding-box alignment and nearest-centerline ownership with **deformable registration plus per-stroke masks**, then allow an editor to fix crossings and path direction. A published registration-and-segmentation method follows this three-stage structure: [Li et al., 2023](https://arxiv.org/abs/2307.04341). Compare automatic and corrected videos at the same mid-stroke timestamps. Measure correction time per character and ask a calligraphy practitioner whether the inferred motion is plausible.
