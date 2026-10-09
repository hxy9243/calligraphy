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
