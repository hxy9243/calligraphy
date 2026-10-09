"""Pre-render the fixed 永 picker samples from private inputs at startup."""
from hashlib import sha256

from backend.public_fonts import ROOT, allowed_style, font_sample, private_catalog
from backend.style_catalog import STYLE_ALIASES


def prepare_samples():
    target = ROOT / 'data/font_samples'
    target.mkdir(parents=True, exist_ok=True)
    styles = ['kai', 'yan'] + [entry['id'] for entry in private_catalog()
                              if entry['is_downloaded'] == 1 and allowed_style(entry['id'])]
    for style in styles:
        canonical = STYLE_ALIASES.get(style, style)
        path = target / (sha256(canonical.encode()).hexdigest() + '.png')
        path.write_bytes(font_sample(style))
    print(f'Prepared {len(styles)} backend 永 samples.', flush=True)


if __name__ == '__main__':
    prepare_samples()
