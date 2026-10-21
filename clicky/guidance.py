"""Visual hints are data, never mouse/keyboard commands."""
import math
import re

MARKER = re.compile(r'\[(?:POINT|TYPE):(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?):([^\]\r\n]{1,160})\]')


def hints(answer, capture):
    """Map screenshot pixels to logical coordinates in the reviewed capture."""
    if not capture or not capture.get('bounds') or not capture.get('pixels'):
        return []
    b, p = capture['bounds'], capture['pixels']
    if min(p['width'], p['height'], b['width'], b['height']) <= 0:
        return []
    result = []
    for m in MARKER.finditer(answer):
        x, y = float(m[1]), float(m[2])
        if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < p['width'] and 0 <= y < p['height']):
            continue
        result.append({'x': b['x'] + x / p['width'] * b['width'],
                       'y': b['y'] + y / p['height'] * b['height'], 'label': m[3].strip()})
    return result[:8]


def spoken_text(answer):
    return MARKER.sub(lambda m: m[3], answer).strip()
