"""Thin JSON bridge for the Node CLI's default Kai renderer."""
import argparse
import json
from pathlib import Path
import sys

from .kai_scene import KaiScene, prepare_kai
from .renderer import export_still, export_video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--style', choices=['kai'], default='kai')
    parser.parse_args()
    try:
        request = json.load(sys.stdin)
        plan = request['plan']
        # Fit only characters scheduled for this scene, never the whole guide bank.
        needed = {entry['character'] for entry in plan['schedule']}
        glyphs = {char: request['glyphs'][char] for char in needed}
        scene = KaiScene(plan, prepare_kai(glyphs))
        output = Path(request['output'])
        if output.suffix.lower() == '.mp4':
            export_video(scene, output, fps=request.get('fps', 24), speed=request.get('speed', 1),
                         ffmpeg=request.get('ffmpeg', 'ffmpeg'), workers=request.get('workers', 8))
        else:
            export_still(scene, output, request.get('time'))
        print(json.dumps({'engine': 'kai-fitted', 'output': str(output)}))
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
