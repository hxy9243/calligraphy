# Copying a calligraphy style: research and next experiment

The current animation is an ordered reveal of **Arphic font-derived outlines**. It does not copy a historical calligrapher's hand, ink, or movement. A style-copy feature needs to generate a target glyph first and then attach stroke order and paths to that glyph. A plausible static glyph alone is not animatable.

## Three levels of style copying

| Input | Target | Practical approach |
| --- | --- | --- |
| A reference image contains **the same characters** | Faithfully animate those exact marks | Segment characters and ink, align the known stroke templates, correct stroke ownership at crossings, then reveal the original pixels along the corrected paths. |
| Several samples by one calligrapher, but **new characters** | Generate matching glyphs | Condition a font/calligraphy generator on reference images and a structural template. Review each output for missing, extra, or malformed strokes. Then decompose and animate the generated glyph. |
| A moving brush that actually writes in that style | Infer pressure, speed, direction, brush angle and ink | Collect online pen/brush trajectories or annotate motion. Static images underdetermine the actual motion; optimize for a *plausible* performance rather than claiming an exact reconstruction. |

## Recommended experiment

1. Start with a clean scan of **永** or the ten poem characters in one specific 楷书 hand. Crop and rectify each character; separate foreground ink from paper.
2. Align each known median path and stroke mask to the scan using coarse affine registration and per-stroke path edits. Build a tiny editor for crossings and endpoints before introducing ML.
3. Keep the scan's ink as the final frame. Animate by revealing assigned ink masks along the corrected paths. Compare the final image pixel-for-pixel with the input; seek through the animation to inspect abrupt pops and overlapping strokes.
4. Test on 10–20 characters from one source. Measure manual corrections per character, final-image similarity, and whether a human calligraphy practitioner finds the path and timing believable.
5. Only after that, try generating **unseen glyphs** in the source style. Use the known stroke geometry to check the generated structure, rather than assuming a beautiful raster image has usable stroke order.

## Relevant primary sources

- [CCSE: Instance Segmentation for Chinese Character Stroke Extraction](https://arxiv.org/abs/2210.13826) offers Kai and handwritten stroke-mask datasets and code. It reports overlap as a particular challenge.
- [Simulating the Writing Process from Chinese Calligraphy Image](https://www.jcad.cn/en/article/id/a148ab9a-9e96-43a5-bc11-563c871bb72b) combines stroke extraction, trajectories, and brush footprints with interactive input.
- [ZiGAN](https://arxiv.org/abs/2108.03596) learns glyph style from few references but reports failures on complex characters. It yields glyph images, not stroke trajectories.
- [Calliffusion](https://arxiv.org/abs/2305.19124) conditions generation on character, script, and style, including transfer to unseen characters. Its reported failures include missing and extra strokes.
- [Few-shot Calligraphy Style Learning](https://arxiv.org/abs/2404.17199) conditions on font images and stroke information, supporting the structural-template approach.

Generated style-copy outputs should carry provenance identifying the reference and whether the motion is inferred or recorded. For modern source works, obtain appropriate permission before distributing source scans or a trained style model.
