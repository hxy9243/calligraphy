"""Styled contact replay shared by web previews, stills and videos."""
import base64
import io
import numpy as np
from PIL import Image
from .contact_renderer import ContactScene
from .font_layers import FontLayerScene
from .spec import Appearance, Transforms


class StyledContactScene(ContactScene):
    parallel_frames = False
    engine_type = 'smoothed-contact'

    def __init__(self, plan, glyphs, appearance=None, transforms=None):
        super().__init__(plan, glyphs)
        self.appearance = appearance or Appearance()
        self.transforms = transforms or Transforms()
        self.width, self.height = plan['width'], plan['height']
        self.duration = plan['duration']

    _create_patch = FontLayerScene._create_patch

    def frame(self, time):
        time = float(time)
        if not np.isfinite(time):
            raise ValueError('time must be finite')
        time = min(self.duration, max(0, time))
        if time < self._last_time:
            self._active = None
        self._last_time = time
        page = Image.new('RGB', (self.width, self.height), self.appearance.paper_color)
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
            x = round(entry['x'] + entry['size'] / 2 - patch.width / 2)
            y = round(entry['y'] + entry['size'] / 2 - patch.height / 2)
            page.paste(patch, (x, y), patch)
        return page

    def frame_svg(self, time):
        # Same deposited pixels as PNG/video; SVG is a raster container here.
        stream = io.BytesIO()
        self.frame(time).save(stream, format='PNG')
        payload = base64.b64encode(stream.getvalue()).decode()
        characters = ''.join(f'<g data-character="{item["character"]}"/>' for item in self.plan['schedule'])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" data-engine="{self.engine_type}">'
                f'<image width="{self.width}" height="{self.height}" href="data:image/png;base64,{payload}"/>'
                f'{characters}</svg>')
