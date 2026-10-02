# Experimental contact fairing

`calligraphy.stroke_fairing.fair_program(program, guides, mode='rails', strength=1)`
returns an independent IR 0.2 copy. It preserves ordered IDs, timing and relations.
It does not consume reference masks or infer pressure, bristles, or real motion.

For station values X and second-difference matrix D, fairing minimizes
`||X - X_original||² + strength * ||D X||²`, subject to exact landmark constraints.
The first and last two contact stations are fixed. Guide bends >=45 degrees and
neighboring stations are fixed; original authored corners are retained. Turn
stations are interpolation corners. Output coordinates are clipped to the unit
square, which may alter smoothness near its boundary.

Modes:

- `rails`: solve the two boundary coordinate sequences together.
- `motion`: solve center coordinates, nonnegative contact width, and unwrapped
  contact angle separately, then reconstruct boundary pairs. Zero-width station
  angles are interpolated from neighboring nonzero contacts.

Strength must be finite and nonnegative. A guide is required for each stroke.
Strength zero leaves station coordinates unchanged, though inferred interpolation
corners and provenance may change. There is no score-driven fallback or automatic
selection. The lab records all fixed candidates, including shape or motion failures.

Station-index regularity is not invariant to contact sampling density. Rendered
geometry must be checked at multiple sizes, along with individual partial frames,
outline retention, intended corners, and hooks. A smoother metric is not proof of
better calligraphy. Neither mode is enabled in production CLI rendering.

Reproducible study: sibling `calligraphy-lab/experiments/kai-stroke-ir/tuning.py`
and `tuning.html`. Settings, source/input hashes, metrics and repository states
are recorded per experiment; generated media stays in ignored work directories.
