"""Cache derived crossing repairs without modifying registered source font banks."""
from hashlib import sha256
import json
import os
from pathlib import Path

from .artifact_cache import ArtifactCache
from .engine_metadata import engine_metadata
from .stroke_crossings import smooth_kai_contacts


def prepare_contacts(glyphs, *, source, inferred_corners=False, cache_path=None):
    metadata = engine_metadata('font-contact')
    cache = ArtifactCache(cache_path or os.environ.get('CALLIGRAPHY_CONTACT_CACHE',
        str(Path.home() / '.local/share/calligraphy/contact-geometry.db')))
    prepared, reports = {}, {}
    for character, strokes in glyphs.items():
        identity = {'source': source, 'character': character, 'strokes': strokes,
                    'inferred_corners': inferred_corners,
                    'engine_source_sha256': metadata['engine_source_sha256']}
        digest = sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                   allow_nan=False).encode()).hexdigest()
        key = f'smoothed-contact/1:{digest}'
        with cache.lock(key):
            try:
                document = cache.get(key)
            except KeyError:
                smoothed, report = smooth_kai_contacts(strokes, inferred_corners=inferred_corners)
                document = {'schemaVersion': 'smoothed-contact/1', 'identity': digest,
                            'strokes': smoothed, 'report': report,
                            'provenance': {'source': source, 'engine': metadata}}
                cache.put(key, document)
            if document.get('identity') != digest:
                raise ValueError(f'Contact cache identity mismatch for {character}')
        prepared[character] = document['strokes']
        reports[character] = document['report']
    return prepared, reports
