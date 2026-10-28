# Stroke fitting regression inputs

`que-hanzi-writer-2.0.1.json` is the unmodified 闕 glyph from
https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/%E9%97%95.json
(retrieved 2026-10-09). Hanzi Writer Data is derived from Make Me a Hanzi;
its character data is available under the Arphic Public License. See the
repository's `ARPHICPL.TXT` and existing guide-data provenance.

The tenth stroke produces a 993-pixel main component plus one detached
antialiased tip pixel under the production 160→480 rasterization pipeline.
Keeping the actual source record makes this regression independent of network
access and avoids changing the bundled production guide bank.

`masa-wind-legacy.json` preserves inferred 風 geometry fitted at baseline commit
`4d7980f5c8b148c5467f1b3cdedafedb6c9888fd`. Its second stroke has an incorrect
interior schedule gap: the top and terminal hook precede the body, which was
assigned to later strokes. The fixture contains contacts and the unchanged
Hanzi Writer Data 2.0.1 guide, not a font file or machine-local registry paths.
Guide licensing is the Arphic Public License (`ARPHICPL.TXT`).

The source is MasaFont Brush Xing (`MasaFont-Regular.ttf`), SHA-256
`f5a449d3a9ce2170e404050cc2b44bfa16ae48ef8fb06aa5968383ed74e5ed4d`, from
https://github.com/max32002/masafont. Copyright and SIL OFL 1.1 notices are
retained in `data/licenses/MasaFont-Regular.ttf.metadata.txt`. The contacts are
inferred rendering regression inputs, not a claim of historical brush motion.
