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

## Mask warp trial: result

After installing the root Node dependencies (`npm install`) and Python requirements, run `node experiments/kai-four/stroke_masks.mjs` followed by `python3 experiments/kai-four/mask_warp.py`. The JS script rasterizes all ten ordered stroke outlines into separate 300 × 300 masks. The Python script scales each outline to each scan, searches for a small per-stroke translation (at most 10 pixels in each direction), and assigns source ink to the nearest **warped silhouette**. It resamples the template centerlines with a monotone cubic interpolation before computing each pixel's reveal time. The output is `four-kai-mask-warp.mp4`, with colored ownership maps `mask-labels-0.png` through `mask-labels-3.png`. `comparison-mask-warp.mp4` shows the original method on the left and the mask method on the right at the same timestamps.

**Finding:** This first mask warp did *not* improve the animation overall. It keeps every source-ink pixel in the final frame, but intermediate frames still break strokes into separate pieces. In the broad Zhao Mengfu sample, only 51.7% of source-ink pixels fall within any warped outline; the other hands have 84.3%, 68.5%, and 83.6% coverage respectively. Each writer still has several inferred strokes with multiple connected ink components larger than 12 pixels. These figures measure geometric registration and fragmentation, not historical accuracy. Translation alone cannot fit different calligraphers' changes in stroke proportions and local curvature. Projecting ink onto a smooth centerline also does not guarantee a connected *area* while the stroke is drawn.

The next useful step is **local deformation constrained by stroke topology**, with landmarks for each stroke's start, end, and crossings. During reveal, grow a connected brush contact region along the warped stroke and transfer the scan texture into it; use the original scan as the final target. A small manual correction interface for ambiguous crossings will probably be necessary. Keeping the motion smooth is a useful regularizer, but cannot identify which overlaid ink belongs to which physical brush pass from a single finished image.

## Local path deformation and connected brush sweep

Run `python3 experiments/kai-four/local_warp.py` after generating the individual stroke masks above. `four-kai-local-warp.mp4` contains the result. `comparison-three-methods.mp4` places nearest median, translated masks, and local path warp **left to right** at identical times.

For each stroke, `local_warp.py` searches for a smooth normal displacement of its centerline toward scan ink. A dynamic program penalizes both distance from ink and abrupt displacement changes. It estimates the stroke width from the nearest transverse ink run, limits implausibly large widths using the template mask, and sweeps overlapping disks along the path. A narrow region around the scan transfers its texture and bridges small scan gaps. The final 1-second completion blend restores the **exact original scanned pixels**, including ink outside all inferred strokes; that blend is a disclosed visual completion, not an inferred brush movement.

| Hand | Ink touched by full brush sweep |
| --- | ---: |
| Ouyang Xun | 94.7% |
| Yan Zhenqing | 90.9% |
| Liu Gongquan | 96.8% |
| Zhao Mengfu | 85.5% |

These are *coverage* figures for the union of brush footprints, not per-stroke identity or animation accuracy. The connected sweep looks less fragmented than the translated-mask trial at intermediate frames, especially for broad Yan and Zhao strokes. It also exposes a different error: a wide stamp can pick up ink from the wrong stroke at crossings. Zhao's scan still has 14.5% of ink outside the swept footprint, which appears in the completion blend. For a credible writer, the next experiment needs explicit stroke ownership and crossing depth, likely corrected by hand for a few examples, plus registration of stroke **contours** rather than only median and width.
