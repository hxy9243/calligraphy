"""Styled contact replay shared by web previews, stills and videos."""
import base64
import io
import numpy as np
from PIL import Image
from .contact_renderer import ContactScene
from .font_layers import FontLayerScene
from .paper import render_writing_paper
from .spec import Appearance, Transforms


def paste_patch(page, entry, patch):
    """Place a normalized glyph patch identically for editor and contact frames."""
    x = round(entry['x'] + entry['size'] / 2 - patch.width / 2)
    y = round(entry['y'] + entry['size'] / 2 - patch.height / 2)
    page.paste(patch, (x, y), patch)


class StyledContactScene(ContactScene):
    parallel_frames = False
    engine_type = 'smoothed-contact'

    def __init__(self, plan, glyphs, appearance=None, transforms=None):
        super().__init__(plan, glyphs)
        self.appearance = appearance or Appearance()
        self.transforms = transforms or Transforms()
        self.width, self.height = plan['width'], plan['height']
        self.duration = plan['duration']
        schedule = self.plan.get('schedule', []) if isinstance(self.plan, dict) else getattr(self.plan, 'schedule', [])
        self.writing_end = max((float(e['end']) for e in schedule), default=0.0)

    _create_patch = FontLayerScene._create_patch

    def frame(self, time):
        time = float(time)
        if not np.isfinite(time):
            raise ValueError('time must be finite')
        time = min(self.duration, max(0, time))
        time_key = round(time, 4)
        if getattr(self, '_cached_frame_time', None) == time_key and getattr(self, '_cached_frame_image', None) is not None:
            return self._cached_frame_image.copy()
        if time < self._last_time:
            self._active = None
        self._last_time = time
        stamp_time = min(self.writing_end + 0.35, self.duration)
        include_stamp = (time >= stamp_time)
        page = render_writing_paper(self.width, self.height, self.appearance, self.plan, include_stamp=include_stamp)
        for index, entry in enumerate(self.plan['schedule']):
            if time <= entry['start']:
                break
            if time >= entry['end']:
                key = (entry['character'], entry['size'])
                if key not in self._patches:
                    self._patches[key] = self._create_patch(self.glyph_mask(entry['character']), entry['size'])
                patch = self._patches[key]
                if self._active and self._active['index'] == index:
                    self._active = None
            else:
                patch = self._create_patch(self._partial(index, entry, time), entry['size'])
            paste_patch(page, entry, patch)
        self._cached_frame_time = time_key
        self._cached_frame_image = page.copy()
        return page

    def frame_svg(self, time):
        # Same deposited pixels as PNG/video; SVG is a raster container here.
        time_key = round(float(time), 4)
        if getattr(self, '_cached_svg_time', None) == time_key and getattr(self, '_cached_svg_content', None) is not None:
            return self._cached_svg_content
        stream = io.BytesIO()
        self.frame(time).save(stream, format='PNG', compress_level=1)
        payload = base64.b64encode(stream.getvalue()).decode()
        characters = getattr(self, '_characters_tag', None)
        if characters is None:
            characters = self._characters_tag = ''.join(f'<g data-character="{item["character"]}"/>' for item in self.plan['schedule'])

        stamp_time = min(self.writing_end + 0.35, self.duration)
        include_stamp = (float(time) >= stamp_time)
        stamp_svg = ""
        if include_stamp:
            from .paper import get_stamp_placement_for_plan, render_qr_seal_stamp_svg, get_default_stamp_url
            stamp_placement = get_stamp_placement_for_plan(self.width, self.height, self.appearance, self.plan)
            if stamp_placement is not None:
                sx, sy, stamp_sz = stamp_placement
                stamp_url = getattr(self.appearance, "stamp_url", None) or get_default_stamp_url()
                stamp_svg = render_qr_seal_stamp_svg(stamp_url, size_px=stamp_sz, sx=sx, sy=sy)

        res = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
               f'viewBox="0 0 {self.width} {self.height}" data-engine="{self.engine_type}">'
               f'<image width="{self.width}" height="{self.height}" href="data:image/png;base64,{payload}" '
               f'image-rendering="pixelated" style="image-rendering: pixelated; image-rendering: crisp-edges;"/>'
               f'{characters}{stamp_svg}</svg>')
        self._cached_svg_time = time_key
        self._cached_svg_content = res
        return res
